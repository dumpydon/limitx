import hashlib
import json
from typing import Any


def depth_checksum(symbol: str, depth: dict[str, Any]) -> str:
    """Hash symbol plus canonical aggregated L2 depth (not private order fields)."""
    payload = json.dumps(
        {"symbol": symbol, "bids": depth["bids"], "asks": depth["asks"]},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.blake2s(payload.encode(), digest_size=8).hexdigest()
