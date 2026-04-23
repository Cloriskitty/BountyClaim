import requests
import hmac
import hashlib
import base64
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()

OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE")
OKX_PROJECT_ID = os.getenv("OK_PROJECT_ID")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
OKX_BASE_URL = "https://web3.okx.com"

USDC_DECIMALS = 6

CHAINS = {
    "base": {
        "chain_index": "8453",
        "chain_id": 8453,
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "label": "Base",
        "explorer": "https://basescan.org/tx/",
    },
    "xlayer": {
        "chain_index": "196",
        "chain_id": 196,
        "usdc": "0x74b7F16337b8972027F6196A17a631aC6dE26d22",
        "label": "X Layer",
        "explorer": "https://www.oklink.com/xlayer/tx/",
    },
}

ERC20_ABI = [{
    "name": "transfer",
    "type": "function",
    "inputs": [
        {"name": "_to", "type": "address"},
        {"name": "_value", "type": "uint256"}
    ],
    "outputs": [{"name": "", "type": "bool"}]
}]

def _timestamp():
    now = datetime.now(timezone.utc)
    return now.strftime('%Y-%m-%dT%H:%M:%S.') + f"{now.microsecond // 1000:03d}Z"

def _sign(timestamp, method, path, body=""):
    message = timestamp + method.upper() + path + body
    mac = hmac.new(OKX_SECRET_KEY.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

def _headers(method, path, body=""):
    ts = _timestamp()
    return {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": _sign(ts, method, path, body),
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
        "OK-ACCESS-PROJECT": OKX_PROJECT_ID,
        "Content-Type": "application/json",
    }

def _get_sign_info(from_addr, to_addr, call_data, chain):
    """Step 1: Ask OKX Onchain OS for gas price and nonce."""
    path = "/api/v5/wallet/pre-transaction/sign-info"
    body = json.dumps({
        "chainIndex": chain["chain_index"],
        "fromAddr": from_addr,
        "toAddr": to_addr,
        "txAmount": "0",
        "extJson": {"inputData": call_data},
    })
    resp = requests.post(OKX_BASE_URL + path, headers=_headers("POST", path, body), data=body)
    data = resp.json()
    if data.get("code") != "0" or not data.get("data"):
        raise RuntimeError(f"sign-info failed: {data.get('msg')}")
    return data["data"][0]

def _get_tx_hash(order_id, address, chain):
    """Query OKX for the real on-chain tx hash from an orderId."""
    import time
    path = "/api/v6/dex/post-transaction/orders"
    params = f"?orderId={order_id}&chainIndex={chain['chain_index']}&address={address}"
    for _ in range(5):
        resp = requests.get(OKX_BASE_URL + path + params, headers=_headers("GET", path + params))
        data = resp.json()
        orders = data.get("data", [{}])[0].get("orders", [])
        if orders and orders[0].get("txHash"):
            return orders[0]["txHash"]
        time.sleep(2)
    return None

def _broadcast(signed_tx_hex, from_addr, chain):
    """Step 3: Broadcast via OKX Onchain OS v6 endpoint."""
    path = "/api/v6/dex/pre-transaction/broadcast-transaction"
    body = json.dumps({
        "signedTx": signed_tx_hex,
        "chainIndex": chain["chain_index"],
        "address": from_addr,
    })
    resp = requests.post(OKX_BASE_URL + path, headers=_headers("POST", path, body), data=body)
    data = resp.json()
    if data.get("code") == "0":
        data_field = data.get("data", [])
        order_id = data_field[0].get("orderId", "") if isinstance(data_field, list) and data_field else ""
        return {"code": "0", "data": {"orderId": order_id}}
    # fallback to public RPC
    rpc_urls = {"8453": "https://mainnet.base.org", "196": "https://rpc.xlayer.tech"}
    rpc = rpc_urls.get(chain["chain_index"], "https://mainnet.base.org")
    resp2 = requests.post(rpc, json={
        "jsonrpc": "2.0", "method": "eth_sendRawTransaction",
        "params": [signed_tx_hex], "id": 1,
    })
    data2 = resp2.json()
    if "error" in data2:
        return {"code": "1", "msg": data2["error"].get("message", "Broadcast failed")}
    return {"code": "0", "data": {"orderId": data2.get("result", "")}}

def send_usdc_payment(recipient_address: str, amount_usdc: float, memo: str = "", chain_name: str = "base") -> dict:
    """
    Hybrid flow:
      1. OKX sign-info  → get gas + nonce (Onchain OS)
      2. web3.py        → sign transaction locally with private key
      3. OKX broadcast  → submit via Onchain OS v6
    Supports: base, xlayer
    """
    if not PRIVATE_KEY:
        return {"success": False, "error": "PRIVATE_KEY not set in .env"}

    chain = CHAINS.get(chain_name, CHAINS["base"])

    w3 = Web3()
    account = Account.from_key(PRIVATE_KEY)
    from_addr = account.address

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(chain["usdc"]),
        abi=ERC20_ABI
    )
    amount_raw = int(amount_usdc * 10 ** USDC_DECIMALS)
    call_data = contract.encode_abi(
        "transfer",
        args=[Web3.to_checksum_address(recipient_address), amount_raw]
    )

    try:
        sign_info = _get_sign_info(from_addr, chain["usdc"], call_data, chain)
    except RuntimeError as e:
        return {"success": False, "error": str(e)}

    nonce = int(sign_info.get("nonce", 0))
    eip1559 = sign_info.get("gasPrice", {}).get("eip1559Protocol", {})
    max_fee = int(eip1559.get("baseFee", 0)) + int(eip1559.get("proposePriorityFee", 0))
    max_priority_fee = int(eip1559.get("proposePriorityFee", 1500000))
    gas_limit = int(sign_info.get("gasLimit", 100000))

    tx = {
        "chainId": chain["chain_id"],
        "nonce": nonce,
        "to": Web3.to_checksum_address(chain["usdc"]),
        "value": 0,
        "gas": gas_limit,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": max_priority_fee,
        "data": call_data,
        "type": 2,
    }
    signed = account.sign_transaction(tx)
    signed_hex = "0x" + signed.raw_transaction.hex()

    result = _broadcast(signed_hex, from_addr, chain)
    if result.get("code") == "0":
        order_id = result.get("data", {}).get("orderId", "")
        tx_hash = _get_tx_hash(order_id, from_addr, chain) or signed.hash.hex()
        return {
            "success": True,
            "tx_hash": tx_hash,
            "amount": amount_usdc,
            "recipient": recipient_address,
            "chain": chain["label"],
            "explorer": chain["explorer"] + tx_hash,
        }
    else:
        return {
            "success": False,
            "error": result.get("msg", "Broadcast failed"),
            "detail": result,
        }
