#!/bin/bash
# 설정은 있고 프로필.md는 없는 상태
set -eu
mkdir -p "$HOME/.claude" wiki
printf '{"wiki_path": "%s/wiki", "tracker": "local", "notion_ds_id": ""}\n' "$PWD" > "$HOME/.claude/chwijun-copilot.json"
