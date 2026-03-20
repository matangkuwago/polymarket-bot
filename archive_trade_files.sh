#!/usr/bin/env bash

mkdir -p old_trades/trades
mkdir -p old_trades/trades_processed
mv -f trades/*.trade old_trades/trades/ 2>/dev/null
mv -f trades_processed/*.trade old_trades/trades_processed/ 2>/dev/null
