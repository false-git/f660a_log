#!/bin/sh
# cronで1時間に1回動かす。
set -e

cd "${0%/*}"
.venv/bin/python f660a_log.py > log/`date +%Y%m%d_%H%M%S`.csv
.venv/bin/python f660a_graph.py log
