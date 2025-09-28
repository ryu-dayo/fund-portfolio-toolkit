from config_loader import load_config

try:
    from eastmoney_client import fetch_fund_info_map
except ModuleNotFoundError:
    def fetch_fund_info_map(_codes: list[str]) -> dict[str, dict[str, str]]:
        return {}

CHANNEL_MAP = {
    "ttjj": fetch_fund_info_map,
}

def get_fund_data(fund_codes: list[str]) -> dict[str, dict[str, str]]:
    config = load_config()
    channel_name = config.get("channel", {}).get("name", "ttjj")
    provider = CHANNEL_MAP.get(channel_name)
    if not provider:
        raise ValueError(f"Unsupported fund data channel: {channel_name}")
    try:
        response = provider(fund_codes)
    except Exception:
        # Gracefully swallow provider issues so the project can run without bundled API clients.
        return {}
    return response
