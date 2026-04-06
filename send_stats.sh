#!/usr/bin/env bash

start_time=$SECONDS

python get_stats.py

elapsed_time=$(($SECONDS - $start_time))
echo "Elapsed time: $elapsed_time"
