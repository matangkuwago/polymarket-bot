#!/usr/bin/env bash

start_time=$SECONDS

LOCK_FILE=/tmp/process_trade_records.txt
if [ -f $LOCK_FILE ]; then
   echo "File $LOCK_FILE exists."
   exit 1
else
   echo "File $LOCK_FILE does not exist."
fi
trap 'rm -rf $LOCK_FILE' EXIT  # remove the lock file on exit

# Prediction proper here
touch $LOCK_FILE

python update_trade_records.py
python evaluate_paper_trade_settings.py

elapsed_time=$(($SECONDS - $start_time))
echo "Elapsed time: $elapsed_time"
