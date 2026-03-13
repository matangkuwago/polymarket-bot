#!/usr/bin/env bash

start_time=$SECONDS

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

source .env

# Bot for SOL 5-minute market
python run_bot.py --market_slug_prefix=sol-updown-5m --binance_ticker=SOLUSDT --paper_trade=$SOL_PAPER_TRADE

# Bot for XRP 5-minute market
python run_bot.py --market_slug_prefix=xrp-updown-5m --binance_ticker=XRPUSDT --paper_trade=$XRP_PAPER_TRADE

# Bot for ETH 5-minute market
python run_bot.py --market_slug_prefix=eth-updown-5m --binance_ticker=ETHUSDT --paper_trade=$ETH_PAPER_TRADE

# Bot for BTC 5-minute market
python run_bot.py --market_slug_prefix=btc-updown-5m --binance_ticker=BTCUSDT --paper_trade=$BTC_PAPER_TRADE

# Run other tasks
python update_trade_records.py
python get_stats.py

elapsed_time=$(($SECONDS - $start_time))
echo "Elapsed time: $elapsed_time"
