#!/usr/bin/env bash
# Runs after every Edit/Write. Claude Code sends the tool call as JSON on stdin.
# Exit 2 sends stderr back to the model, which must fix the error before moving on.

file=$(jq -r '.tool_input.file_path')
[[ "$file" == *.py ]] || exit 0

if ! out=$(uv run ruff check "$file" 2>&1); then
  echo "ruff found problems in $file:" >&2
  echo "$out" >&2
  exit 2
fi
