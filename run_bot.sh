#!/usr/bin/env bash

LOCK_FILE=/tmp/polymarket_bot_lock.txt
if [ -f $LOCK_FILE ]; then
   echo "File $LOCK_FILE exists."
   exit 1
else
   echo "File $LOCK_FILE does not exist."
fi
trap 'rm -rf $LOCK_FILE' EXIT  # remove the lock file on exit
touch $LOCK_FILE


limit_seconds=1500
start_time=$SECONDS
first_run=true

declare -a tickers=("btc" "eth" "xrp" "sol")

while true; do
   elapsed_time=$(($SECONDS - $start_time))
   if [ "$elapsed_time" -ge "$limit_seconds" ] || [ "${first_run}" == "true" ]; then
      start_time=$SECONDS
      first_run=false

      for ticker in "${tickers[@]}"; do
         timeout 120 python run_bot.py --market_slug_prefix=${ticker}-updown-5m
      done
   else
      remaining_seconds=$(($limit_seconds - $elapsed_time))
      minutes=$(echo "scale=2; $remaining_seconds/60" | bc)
      echo "$minutes minute(s) remaining till the next run."
   fi
   sleep 1
done
