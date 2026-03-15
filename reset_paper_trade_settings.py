import json
from core.config import Config


config = {
    "btc-updown-5m": True,
    "eth-updown-5m": True,
    "sol-updown-5m": True,
    "xrp-updown-5m": True,
}

Config.save_paper_trade_settings(config)
settings_json = Config.get_paper_trade_settings()

print("Saved paper trade settings:")
pretty_json_string = json.dumps(settings_json, indent=4)
print(pretty_json_string)
