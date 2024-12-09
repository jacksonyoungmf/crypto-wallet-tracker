import os
import pytest
from dotenv import load_dotenv

def test_environment_variables():
    """
    Test that critical environment variables are set
    """
    # Load environment variables
    load_dotenv()

    # Check Telegram configuration
    assert os.getenv('TELEGRAM_BOT_TOKEN'), "Telegram Bot Token must be set"
    assert os.getenv('TELEGRAM_CHAT_ID'), "Telegram Chat ID must be set"

    # Check RPC URLs
    assert os.getenv('ETHEREUM_RPC_URL'), "Ethereum RPC URL must be set"
    assert os.getenv('BASE_RPC_URL'), "Base RPC URL must be set"

def test_wallet_lists():
    """
    Test that wallet lists are not empty
    """
    ethereum_wallets = os.getenv('ETHEREUM_WALLETS', '').split(',')
    base_wallets = os.getenv('BASE_WALLETS', '').split(',')

    assert len(ethereum_wallets) > 0, "Ethereum wallet list must not be empty"
    assert len(base_wallets) > 0, "Base wallet list must not be empty"

def test_wallet_address_format():
    """
    Basic validation of wallet address formats
    """
    def is_valid_eth_address(address):
        # Basic check for 0x prefix and 40 hex characters
        return (len(address) == 42 and 
                address.startswith('0x') and 
                all(c in '0123456789ABCDEFabcdef' for c in address[2:]))

    ethereum_wallets = os.getenv('ETHEREUM_WALLETS', '').split(',')
    base_wallets = os.getenv('BASE_WALLETS', '').split(',')

    for wallet in ethereum_wallets + base_wallets:
        assert is_valid_eth_address(wallet), f"Invalid wallet address format: {wallet}"
