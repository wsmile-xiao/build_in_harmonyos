#!/bin/sh
# 消费者测试：运行 alfa --citation 断言版本 + 对上游 1d.ascii 拟合断言输出
set -eu

ALFA="${1:-}"
WORKDIR="${2:-}"
if [ -z "$ALFA" ]; then
    echo "FAIL: alfa binary path not provided"
    exit 1
fi
if [ -z "$WORKDIR" ]; then
    WORKDIR="$(dirname "$0")"
fi

# 断言 1：--citation 输出版本
CIT=$("$ALFA" --citation 2>&1) || true
echo "alfa citation: $(echo "$CIT" | grep -m1 version || echo "$CIT" | head -1)"
case "$CIT" in
    *2.2*) echo "PASS: version output" ;;
    *) echo "FAIL: unexpected citation output: $CIT"; exit 1 ;;
esac

# 断言 2：对上游 1d.ascii 拟合（真实测试数据，linelists 已在 workdir）
cd "$WORKDIR"
[ -f 1d.ascii ] || { echo "FAIL: 1d.ascii not found in $WORKDIR"; exit 1; }
OUT=$("$ALFA" -cl "$WORKDIR/1d.ascii" 2>&1)
RC=$?
echo "$OUT" | tail -3
if [ $RC -eq 0 ] && [ -f "${WORKDIR}/1d.ascii_fit.fits" ]; then
    echo "PASS: 1d.ascii fit completed (fits output produced)"
else
    echo "FAIL: alfa fit rc=$RC"
    echo "$OUT" | tail -5
    exit 1
fi

echo "alfa test_package: OK"
exit 0
