#!/usr/bin/env bash
# Runs when the model says it is done. Exit 2 sends the failures back and the agent keeps working.

# Already sent back once? Let it stop: keep the loop small.
[[ $(jq -r '.stop_hook_active') == "true" ]] && exit 0

out=$(uv run pytest -q 2>&1)
code=$?
[[ $code -eq 0 || $code -eq 5 ]] && exit 0   # 5 = no tests yet

echo "Tests failed. Fix them before you stop:" >&2
echo "$out" >&2
exit 2
