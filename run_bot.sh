#!/usr/bin/env bash

start_time=$SECONDS

./process_trade_records.sh

# Bot for SOL 5-minute market
python run_bot.py --market_slug_prefix=sol-updown-5m

# Bot for XRP 5-minute market
python run_bot.py --market_slug_prefix=xrp-updown-5m

# Bot for BTC 5-minute market
python run_bot.py --market_slug_prefix=btc-updown-5m

# Bot for ETH 5-minute market
python run_bot.py --market_slug_prefix=eth-updown-5m

./process_trade_records.sh
./send_stats.sh

elapsed_time=$(($SECONDS - $start_time))
echo "Elapsed time: $elapsed_time"
