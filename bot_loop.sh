#!/usr/bin/env bash

limit_seconds=1500
start_time=$SECONDS
timeout 120 ./run_bot.sh

while true; do
    elapsed_time=$(($SECONDS - $start_time))
    if [ "$elapsed_time" -ge "$limit_seconds" ]; then
        start_time=$SECONDS
        timeout 120 ./run_bot.sh
    else
        remaining_seconds=$(($limit_seconds - $elapsed_time))
        minutes=$(echo "scale=2; $remaining_seconds/60" | bc)
        echo "$minutes minute(s) remaining till the next run."
    fi
    sleep 1
done
