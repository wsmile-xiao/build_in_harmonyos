#!/bin/sh
set -eu

BIN="$1"

# 负向断言用显式 if-then-fail 模式：POSIX sh 中 set -e 会忽略以 ! 开头
# pipeline 的失败，裸 ! cmd 在二进制意外返回 0 时不会使脚本退出

# Help/usage output and exit code (mirrors upstream src/test/test1.sh)
"$BIN/dnsperf" -h
"$BIN/resperf" -h

# Suppression argument validation (mirrors upstream src/test/test1.sh)
if "$BIN/dnsperf" -O suppress; then
    echo "FAIL: dnsperf accepted -O suppress" >&2
    exit 1
fi
if "$BIN/resperf" -O suppress; then
    echo "FAIL: resperf accepted -O suppress" >&2
    exit 1
fi

# Regression check for v2.11.0 broken long option (upstream issue #234)
"$BIN/dnsperf" -O suppress=test 2>&1 | grep -q "unknown message type to suppress: test"

# DoH option combination accepted (upstream test1.sh)
"$BIN/dnsperf" -O doh-uri=https://blahblah.com/dns-query -O suppress=timeouts -h

# Invalid argument error paths (mirrors upstream src/test/test3.sh)
if "$BIN/dnsperf" -d does_not_exist; then
    echo "FAIL: dnsperf accepted nonexistent datafile" >&2
    exit 1
fi
if "$BIN/dnsperf" -m invalid; then
    echo "FAIL: dnsperf accepted invalid transport mode" >&2
    exit 1
fi
if "$BIN/dnsperf" -n 43f8huishfs; then
    echo "FAIL: dnsperf accepted malformed -n value" >&2
    exit 1
fi

# Malformed empty input blob must be rejected (mirrors upstream src/test/test7.sh)
: > empty.blob
if "$BIN/dnsperf" -vvv -B -d empty.blob > empty.out 2>&1; then
    echo "FAIL: empty blob was accepted" >&2
    exit 1
fi
grep -F "Error: input file contains no data" empty.out
