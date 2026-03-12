#!/usr/bin/env bash

LOCK_FILE=/tmp/polymarket_bot_lock.txt
if [ -f $LOCK_FILE ]; then
   echo "File $LOCK_FILE exists."
   exit 1
else
   echo "File $LOCK_FILE does not exist."
fi
trap 'rm -rf $LOCK_FILE' EXIT  # remove the lock file on exit

# Prediction proper here
touch $LOCK_FILE

# Bot for BTC 5-minute market
python python run_bot.py --market_slug_prefix=btc-updown-5m --binance_ticker=BTCUSDT

# Bot for SOL 5-minute market
python python run_bot.py --market_slug_prefix=sol-updown-5m --binance_ticker=SOLUSDT
