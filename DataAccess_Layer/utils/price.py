import requests
from decimal import Decimal

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=tether,usd-coin&vs_currencies=inr"
)

def get_usd_to_inr_rate() -> Decimal:
    try:
        response = requests.get(COINGECKO_URL, timeout=5)
        response.raise_for_status()

        data = response.json()

        # Prefer USDC, fallback to USDT
        inr_rate = (
            data.get("usd-coin", {}).get("inr")
            or data.get("tether", {}).get("inr")
        )

        if not inr_rate:
            raise ValueError("INR rate not found in CoinGecko response")

        return Decimal(str(inr_rate))

    except Exception as e:
        raise RuntimeError(f"Failed to fetch INR rate: {e}")
