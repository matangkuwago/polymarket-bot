#!/usr/bin/env bash

LOCK_FILE=/tmp/polymarket_bot_lock.txt
if [ -f $LOCK_FILE ]; then
   echo "File $LOCK_FILE exists."
   exit 1
else
   echo "File $FILE does not exist."
fi
trap 'rm -rf $LOCK_FILE' EXIT  # remove the lock file on exit

# Prediction proper here
touch $LOCK_FILE
python run_bot.py
