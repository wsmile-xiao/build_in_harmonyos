#!/bin/sh
# zsv 消费者冒烟测试：version + count（实质调用被测包二进制）
set -e

zsv version

printf 'name,age\nalice,30\nbob,25\n' > smoke.csv
n=$(zsv count smoke.csv)
if [ "$n" != "2" ]; then
    echo "FAIL: zsv count expected 2, got '$n'"
    exit 1
fi
echo "PASS: zsv count = $n"
