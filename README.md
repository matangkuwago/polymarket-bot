# polymarket-bot

### About The Project
An experimental Polymarket bot that places limit orders based on predictions obtained from a [price-prediction-server](https://github.com/matangkuwago/price-prediction-server).


The bot works as follows:
1. Get price history from polymarket (or from Binance because sometimes, Polymarket price history is inconsistent).
2. Send the price history to the prediction server and wait for the predictions to be available.
3. Place limit orders on Polymarket based on the obtained predictions.

### Installation
1. Create a python virtual environment, use the python version in the `.python-version` and install the pip packages in the `requirements.txt` file.
2. Setup a Polymarket account.
3. Create a `wallet_config.json` file with content in this format:
```
{
    "btc-updown-5m": {
        "funder_address": "funder_address_here",
        "private_key": "private_key_here",
        "signature_type": 2
    },
    "eth-updown-5m": {
        "funder_address": "funder_address_here",
        "private_key": "private_key_here",
        "signature_type": 2
    },
    "xrp-updown-5m": {
        "funder_address": "funder_address_here",
        "private_key": "private_key_here",
        "signature_type": 2
    },
    "sol-updown-5m": {
        "funder_address": "funder_address_here",
        "private_key": "private_key_here",
        "signature_type": 2
    }
}
```
4. Run the bot:
`./run_bot.sh`
