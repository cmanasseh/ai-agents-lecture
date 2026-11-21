#!/usr/bin/env bash
# Put the repo back to the start of the Part 2 demo. Safe to run any number of times:
# after the dry run, before the lecture, or mid-lecture if something goes wrong.
#   bash .devcontainer/reset-demo.sh
set -uo pipefail

git fetch origin --prune --quiet
git checkout --quiet -f part2-live
git reset --quiet --hard origin/part2-live   # undo every edit made during the demo
git clean -fdq                               # remove files the demo created (live_tell.py, the new test)
rm -rf evals/reports                         # old eval output
git branch -D part2-demo 2>/dev/null || true                 # the local demo branch
git push --quiet origin --delete part2-demo 2>/dev/null || true   # and its copy on GitHub

echo "Reset done: on part2-live, no local changes, no part2-demo branch."
echo "Start a demo run with: git checkout -b part2-demo"
