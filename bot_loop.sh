#!/usr/bin/env bash

./run_bot.sh

limit_seconds=1500
start_time=$SECONDS

while true; do
    elapsed_time=$(($SECONDS - $start_time))
    if [ "$elapsed_time" -ge "$limit_seconds" ]; then
        ./run_bot.sh
        start_time=$SECONDS
    else
        remaining_seconds=$(($limit_seconds - $elapsed_time))
        minutes=$(echo "scale=2; $remaining_seconds/60" | bc)
        echo "$minutes minute(s) remaining till the next run."
        python update_trade_records.py
    fi
    sleep 1
done
