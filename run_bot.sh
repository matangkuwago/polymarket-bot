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
touch $LOCK_FILE

# Bot for SOL 5-minute market
python run_bot.py --market_slug_prefix=sol-updown-5m --binance_ticker=SOLUSDT

# Bot for XRP 5-minute market
python run_bot.py --market_slug_prefix=xrp-updown-5m --binance_ticker=XRPUSDT

# Bot for ETH 5-minute market
python run_bot.py --market_slug_prefix=eth-updown-5m --binance_ticker=ETHUSDT

# Bot for BTC 5-minute market
python run_bot.py --market_slug_prefix=btc-updown-5m --binance_ticker=BTCUSDT

./process_trade_records.sh
./send_stats.sh

elapsed_time=$(($SECONDS - $start_time))
echo "Elapsed time: $elapsed_time"
