#!/usr/bin/env bash

mkdir -p old_trades/trades
mkdir -p old_trades/trades_processed
mv trades/*.trade old_trades/trades/
mv trades_processed/*.trade old_trades/trades_processed/
