#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
/home/ubuntu/claude-bot/venv/bin/python notifier.py "$@"
