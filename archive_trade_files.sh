#!/usr/bin/env bash

mkdir -p old_trades/trades_processed
python archive_processed_trades.py --old_days=1
