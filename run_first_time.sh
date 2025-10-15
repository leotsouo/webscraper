#!/usr/bin/env bash
set -euo pipefail

# 第一次跑：抓 6 頁 iPhone 15 當示範（你可換關鍵字）
python cli.py fetch pchome --q "iphone 15" --pages 6
