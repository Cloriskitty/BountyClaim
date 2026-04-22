# BountyClaim

> Open-source contribution → verified → USDC in your wallet. Instantly.


## The Problem

Bounty hunters in Nigeria, Pakistan, and LatAm complete GitHub tasks and get stuck
waiting days for PayPal transfers that may be blocked or eaten by fees.
The contribution is done. The execution layer is broken.

## The Solution

BountyClaim automates the last mile of open-source bounty settlement:

1. Paste your merged PR link
2. Agent verifies it's merged via GitHub API
3. OnchainOS x402 sends USDC to your wallet
4. Done in < 30 seconds. No bank needed.

## Onchain OS Integration

Uses **OnchainOS x402 Payments** — the core capability for autonomous agent payments.
Settlement on Base Sepolia (testnet) / Base Mainnet.

## Setup

```bash
git clone https://github.com/yourusername/bountyclaim
cd bountyclaim
pip install -r requirements.txt
cp .env.example .env
# Fill in your OKX API keys in .env
python main.py
```


## Demo

[Link to demo video]

## Built With

- Python + Flask
- OnchainOS x402 Payment API
- GitHub REST API
- Base Sepolia testnet

