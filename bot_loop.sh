#!/usr/bin/env bash


start_time=$SECONDS
limit_seconds=1500

./run_bot.sh

while true; do
    elapsed_time=$(($SECONDS - $start_time))
    if [ "$elapsed_time" -ge "$limit_seconds" ]; then
        start_time=$SECONDS
        ./run_bot.sh
    else
        remaining_seconds=$(($limit_seconds - $elapsed_time))
        minutes=$(echo "scale=2; $remaining_seconds/60" | bc)
        echo "$minutes minute(s) remaining till the next run."

        # do other tasks while waiting
        python update_trade_records.py
    fi
    sleep 1
done
