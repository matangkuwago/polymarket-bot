#!/usr/bin/env bash

while true; do
    ./run_bot.sh
    for (( seconds=1500; seconds>0; seconds-- )); do
        minutes=$(echo "scale=2; $seconds/60" | bc)
        echo "$minutes minute(s) remaining till the next run."
        sleep 1
    done
done
