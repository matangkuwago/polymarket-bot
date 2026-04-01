#!/usr/bin/env bash

start_time=$SECONDS

LOCK_FILE=/tmp/process_trade_records_lock.txt
if [ -f $LOCK_FILE ]; then
   echo "File $LOCK_FILE exists."
   exit 1
else
   echo "File $LOCK_FILE does not exist."
fi
trap 'rm -rf $LOCK_FILE' EXIT  # remove the lock file on exit
touch $LOCK_FILE

python archive_processed_trades.py --old_days=1
python update_trade_records.py

elapsed_time=$(($SECONDS - $start_time))
echo "Elapsed time: $elapsed_time"
