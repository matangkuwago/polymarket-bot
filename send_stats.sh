#!/usr/bin/env bash

start_time=$SECONDS

LOCK_FILE=/tmp/send_stats_lock.txt
if [ -f $LOCK_FILE ]; then
   echo "File $LOCK_FILE exists."
   exit 1
else
   echo "File $LOCK_FILE does not exist."
fi
trap 'rm -rf $LOCK_FILE' EXIT  # remove the lock file on exit
touch $LOCK_FILE

python get_stats_per_hour.py
python get_stats.py

elapsed_time=$(($SECONDS - $start_time))
echo "Elapsed time: $elapsed_time"
