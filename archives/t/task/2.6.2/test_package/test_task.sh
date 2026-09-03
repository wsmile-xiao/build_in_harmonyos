#!/bin/bash
# Test script for task 2.6.2 (Taskwarrior)
# Verifies: version, add, list, done workflow

set -e

TASK_BIN="${1:-task}"
TMPDIR=$(mktemp -d)
export TASKDATA="$TMPDIR/data"
export TASKRC="$TMPDIR/taskrc"
mkdir -p "$TASKDATA"

# Test 1: version
echo "=== Test 1: version ==="
$TASK_BIN --version

# Test 2: add task
echo "=== Test 2: add task ==="
$TASK_BIN add "Test task from conan"

# Test 3: list
echo "=== Test 3: list ==="
$TASK_BIN list

# Test 4: done
echo "=== Test 4: done ==="
$TASK_BIN 1 done

# Test 5: list (empty)
echo "=== Test 5: list (empty) ==="
$TASK_BIN list || true  # exit 1 is expected when no matches

rm -rf "$TMPDIR"
echo "=== All tests passed ==="
