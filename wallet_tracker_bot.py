import os
import time
import logging
import signal
import sys
from dotenv import load_dotenv
from web3 import Web3
import telegram
import asyncio
import requests

# Load environment variables
load_dotenv()

# Configure logging with file handler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wallet_tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variable for the bot instance
bot_instance = None
chat_id = None

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    logger.info("Shutdown signal received")
    if bot_instance and chat_id:
        # Create event loop if it doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Send shutdown message
        loop.run_until_complete(
            bot_instance.send_message(
                chat_id=chat_id,
                text="⚠️ Wallets have stopped being tracked"
            )
        )
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class WalletTracker:
    def __init__(self, telegram_token, chat_id, wallets, wallet_names, blockchain='ethereum'):
        """
        Initialize the wallet tracker bot
        
        :param telegram_token: Telegram bot token
        :param chat_id: Telegram chat ID to send notifications
        :param wallets: Dictionary of wallets for different blockchains
        :param wallet_names: Dictionary of wallet names for different blockchains
        :param blockchain: Primary blockchain to track (default: ethereum)
        """
        self.telegram_bot = telegram.Bot(token=telegram_token)
        self.chat_id = chat_id
        
        # Blockchain configurations
        self.blockchain_configs = {
            'ethereum': {
                'rpc_url': os.getenv('ETHEREUM_RPC_URL', 'https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'),
                'chain_name': 'Ethereum',
                'explorer_url': 'https://etherscan.io/tx/'
            },
            'base': {
                'rpc_url': os.getenv('BASE_RPC_URL', 'https://mainnet.base.org'),
                'chain_name': 'Base',
                'explorer_url': 'https://basescan.org/tx/'
            }
        }
        
        # Prepare wallet tracking
        self.wallets = {}
        self.wallet_names = {}
        for chain, addresses in wallets.items():
            if chain.lower() not in self.blockchain_configs:
                logger.warning(f"Unsupported blockchain: {chain}. Skipping.")
                continue
            
            # Convert addresses to checksum format
            self.wallets[chain.lower()] = [
                Web3.to_checksum_address(addr.lower()) for addr in addresses
            ]
            
            # Store corresponding wallet names
            self.wallet_names[chain.lower()] = wallet_names.get(chain, [])

        # Initialize Web3 connections
        self.w3_connections = {}
        for chain, config in self.blockchain_configs.items():
            self.w3_connections[chain] = Web3(Web3.HTTPProvider(config['rpc_url']))
        
        # Last known blocks for each chain
        self.last_blocks = {chain: conn.eth.block_number 
                            for chain, conn in self.w3_connections.items()}

    async def send_telegram_message(self, message):
        """Send a message via Telegram"""
        try:
            await self.telegram_bot.send_message(
                chat_id=self.chat_id, 
                text=message, 
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def is_valid_transaction(self, tx, w3, chain):
        """
        Enhanced transaction validation
        
        :param tx: Transaction dictionary
        :param w3: Web3 connection
        :param chain: Blockchain chain name
        :return: Boolean indicating if transaction is valid
        """
        try:
            # Log full transaction details for debugging
            logger.info(f"Validating transaction: {tx}")
            
            # Validate transaction hash
            if not tx['hash']:
                logger.warning(f"Transaction hash is None")
                return False
            
            # Convert hash to hex and validate length
            try:
                tx_hash_hex = tx['hash'].hex()
                if len(tx_hash_hex) != 66:
                    logger.warning(f"Invalid transaction hash length: {tx_hash_hex}")
                    return False
            except Exception as hash_error:
                logger.warning(f"Error processing transaction hash: {hash_error}")
                return False
            
            # Validate transaction value with more detailed logging
            value_in_ether = w3.from_wei(tx['value'], 'ether')
            logger.info(f"Transaction value: {value_in_ether} ETH")
            
            # Optional: Check transaction receipt status with more error details
            try:
                receipt = w3.eth.get_transaction_receipt(tx['hash'])
                if receipt:
                    logger.info(f"Transaction receipt status: {receipt['status']}")
                    if receipt['status'] != 1:
                        logger.warning(f"Transaction failed: {tx_hash_hex}")
                        return False
            except Exception as receipt_error:
                logger.warning(f"Could not fetch transaction receipt: {receipt_error}")
            
            return True
        except Exception as e:
            logger.error(f"Comprehensive transaction validation error: {e}")
            return False

    def check_wallet_transactions(self):
        """
        Check for new transactions for tracked wallets across different chains
        """
        for chain, w3 in self.w3_connections.items():
            # Skip if no wallets for this chain
            if chain not in self.wallets or not self.wallets[chain]:
                continue
            
            current_block = w3.eth.block_number
            
            transactions_processed = 0
            transactions_filtered = 0
            
            for block_num in range(self.last_blocks[chain] + 1, current_block + 1):
                block = w3.eth.get_block(block_num, full_transactions=True)
                
                for tx in block.transactions:
                    # Check if sender or receiver is in tracked wallets for this chain
                    if (tx['from'] in self.wallets[chain] or 
                        (tx['to'] is not None and tx['to'] in self.wallets[chain])):
                        
                        # Validate transaction
                        if not self.is_valid_transaction(tx, w3, chain):
                            transactions_filtered += 1
                            continue
                        
                        # Find wallet names for sender and receiver
                        from_index = self.wallets[chain].index(tx['from']) if tx['from'] in self.wallets[chain] else -1
                        to_index = self.wallets[chain].index(tx['to']) if tx['to'] is not None and tx['to'] in self.wallets[chain] else -1
                        
                        from_name = self.wallet_names[chain][from_index] if from_index != -1 else tx['from']
                        to_name = self.wallet_names[chain][to_index] if to_index != -1 else (tx['to'] or 'Contract Creation')
                        
                        # Format transaction details
                        tx_details = f"""
🚨 <b>{self.blockchain_configs[chain]['chain_name']} Wallet Transaction Detected</b> 🚨
📊 Block: {block_num}
💸 From: <code>{from_name}</code> (<code>{tx['from']}</code>)
💰 To: <code>{to_name}</code> {f"(<code>{tx['to']}</code>)" if tx['to'] else ''}
💵 Value: {w3.from_wei(tx['value'], 'ether')} {chain.upper()}
🔗 Tx Hash: <code>{tx['hash'].hex()}</code>
🌐 Explorer: {self.blockchain_configs[chain]['explorer_url']}{tx['hash'].hex()}
"""
                        # Send Telegram notification
                        asyncio.create_task(self.send_telegram_message(tx_details))
                        transactions_processed += 1
            
            # Log transaction processing summary
            logger.info(f"Processed {chain} transactions - Total: {transactions_processed}, Filtered: {transactions_filtered}")
            
            # Update last processed block for this chain
            self.last_blocks[chain] = current_block

    async def start_tracking(self, interval=15):
        """
        Start continuous wallet tracking
        
        :param interval: Polling interval in seconds
        """
        logger.info(f"Started tracking wallets: {self.wallets}")
        
        while True:
            try:
                self.check_wallet_transactions()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in tracking: {e}")
                await asyncio.sleep(interval)

async def main():
    """
    Main function to initialize and run the wallet tracker
    """
    global bot_instance, chat_id
    
    # Telegram configuration
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    # Validate critical environment variables
    if not telegram_token or not chat_id:
        logger.critical("Missing Telegram configuration. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        sys.exit(1)
    
    # Initialize bot instance
    bot_instance = telegram.Bot(token=telegram_token)
    
    # Safely split and filter wallet addresses and names
    def safe_split(env_var):
        addresses = [addr.strip() for addr in os.getenv(env_var, '').split(',') if addr.strip()]
        logger.info(f"Loaded {len(addresses)} addresses from {env_var}")
        return addresses
    
    # Initialize tracker
    tracker = WalletTracker(telegram_token, chat_id, {
        'ethereum': safe_split('ETHEREUM_WALLETS'),
        'base': safe_split('BASE_WALLETS'),
    }, {
        'ethereum': safe_split('ETHEREUM_WALLET_NAMES'),
        'base': safe_split('BASE_WALLET_NAMES'),
    })
    
    # Send startup message
    try:
        await tracker.telegram_bot.send_message(
            chat_id=chat_id, 
            text="🚀 Wallets are now being tracked"
        )
    except Exception as e:
        logger.error(f"Failed to send startup message: {e}")
    
    # Start tracking
    try:
        await tracker.start_tracking()
    except Exception as e:
        logger.error(f"Tracking stopped unexpectedly: {e}")
        try:
            await tracker.telegram_bot.send_message(
                chat_id=chat_id, 
                text="⚠️ Wallets have stopped being tracked"
            )
        except Exception as send_error:
            logger.error(f"Failed to send shutdown message: {send_error}")

if __name__ == '__main__':
    asyncio.run(main())
