#!/usr/bin/env bash

start_time=$SECONDS

python archive_processed_trades.py --old_days=1
python update_trade_records.py

elapsed_time=$(($SECONDS - $start_time))
echo "Elapsed time: $elapsed_time"
