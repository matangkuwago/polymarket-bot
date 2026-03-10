#!/usr/bin/env bash

while true; do
    ./run_bot.sh
    for (( i=1300; i>0; i-- )); do
        seconds="seconds"
        if [[ "$i" -eq 1 ]]; then
            seconds="second"
        fi
        echo "$i $seconds remaining till the next run."
        sleep 1
    done
done
