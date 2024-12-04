# Crypto Wallet Transaction Telegram Bot

## Overview
This Telegram bot tracks and notifies you about transactions for specific cryptocurrency wallets on the Ethereum blockchain.

## Prerequisites
- Python 3.8+
- Telegram Bot Token
- Infura Account (or another Ethereum RPC provider)

## Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/crypto-wallet-tracker.git
cd crypto-wallet-tracker
```

2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create Telegram Bot
- Open Telegram and search for @BotFather
- Create a new bot and get the bot token
- Start a chat with your bot and get your Chat ID (use @userinfobot)

5. Configure Environment
- Copy `.env.example` to `.env`
- Fill in your Telegram Bot Token
- Add your Telegram Chat ID
- Add wallet addresses to track
- Add Ethereum RPC URL (e.g., from Infura)

6. Run the Bot
```bash
python wallet_tracker_bot.py
```

## Configuration
- Modify `TRACKED_WALLETS` in `.env` to add/remove wallet addresses
- Adjust tracking interval in `start_tracking()` method

## Features
- Real-time Ethereum wallet transaction tracking
- Telegram notifications
- Supports multiple wallet addresses
- Configurable polling interval

## Security Notes
- Never share your `.env` file
- Use environment variables for sensitive information
- Be mindful of RPC provider rate limits

## Future Improvements
- Multi-blockchain support
- Transaction amount filtering
- Advanced notification customization
