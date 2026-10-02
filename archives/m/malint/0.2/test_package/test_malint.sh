#!/bin/sh
# test_malint.sh — malint 0.2 消费者冒烟测试（真实调用被测包）
# 用法: sh test_malint.sh <path-to-installed-malint-binary>
#
# 断言（R34，L1e 反向破坏验证依赖被测产物）：
#  1. 安装后的 malint 二进制存在且 --help 退出 0
#  2. 上游官方样本 frame-short.in（546 字节，base64 内嵌）解码成功
#  3. malint -N3 输出与上游参考 frame-short.log 关键行一致
#     （帧头参数 / 缺字节报告 / 帧计数）
set -u

MALINT="${1:-}"
[ -n "$MALINT" ] || { echo "FAIL: usage: test_malint.sh <malint-binary>"; exit 2; }
[ -f "$MALINT" ] || { echo "FAIL: malint binary not found: $MALINT"; exit 1; }

# 1. --help 可执行
"$MALINT" --help > /dev/null 2>&1 || { echo "FAIL: malint --help rc!=0"; exit 1; }

# 2. 准备工作目录（HMDFS 上 mktemp 可能被拒，回退到当前目录）
D=$(mktemp -d 2>/dev/null) || D=""
[ -n "$D" ] || { D="./tp$$"; mkdir -p "$D"; }

# 上游 malint-0.2/regress/frame-short.in（官方 tarball 样本）
cat > "$D/frame-short.b64" <<'EOF'
//MowAAM6AalnggAAgWr/bkktAYYD5Q4cLvDBRwfEDgwJ6Cg0/kC/85yg0/hgTqovzhPKLf0
//Ehc+GLhOUdvIAByW27bbbf//MowAcLiALeXgAAAoD9gLuiolKhJVwlUkqPOh1owFTjyQ86
ydJJxCM6/v3M7n/5/7bmdIABqy2W2268e+dUwkRkFqOpzyRe//MowBMLmArPthAAAmShRz1q
exU80rczalViejUm9Kv8n+6Jd7FUtWABuvW623bcfsLoSmIULeXuckIvYhNtVi+rZ6ntUtrC
//MowB8KqArTthAAAuq3p/fmfzkXSuztUAG7Nbrbtt389HzfBKfaPc5I//MowC8KehLXtghE
th4P1S0fWlZ0+yiiNDKp4xvYtDUR8wMsTcSotXp2VaV/V9ZAhJvJLOOEgCHLdbrdttxyErc9
blnHMUgi//MowEALmA63jjAAApjWLur0bCKh76r0LtRe1V6Vaf/LO+L6QDavSTjgulOWQO3L
cwkohUoWIIc0htRtTtve303C/tY4jcyr//MowEwKEAbXthAAAuXd9GkVmqkk2oHZD7SAYVDi
yEmtZ8UW5qbjSbhUstzBnVd3J3IXrXbV/9v16n9egAUlG25JLrwSKhq7//MowF4JwA6nXkgA
AolY8PtpeeDciZ5bM9KDUyqfVdqb6s7033ppR6vT1+lGrtp//Bvv7cj+sEbm3Y5Lrw6VQcTh
QbrI0pU5
EOF
base64 -d "$D/frame-short.b64" > "$D/frame-short.in" 2>/dev/null || {
    echo "FAIL: base64 decode failed"; exit 1; }
SZ=$(wc -c < "$D/frame-short.in")
[ "$SZ" = "546" ] || { echo "FAIL: sample size $SZ != 546"; exit 1; }

# 3. 上游 frame-short.test 的 flags（-N3），输出比对参考 log 关键行
"$MALINT" -N3 "$D/frame-short.in" > "$D/out.txt" 2>&1
RC=$?
[ "$RC" = "0" ] || { echo "FAIL: malint -N3 rc=$RC"; exit 1; }

grep -q "MPEG 2 layer 3, 16kbps, 16kHz, mono" "$D/out.txt" || {
    echo "FAIL: missing frame header line"; cat "$D/out.txt"; exit 1; }
grep -q "padding missing from frame (30 of 47 bytes)" "$D/out.txt" || {
    echo "FAIL: missing violation report"; cat "$D/out.txt"; exit 1; }
grep -q "play time: 00:00:00 (8 frames)" "$D/out.txt" || {
    echo "FAIL: missing frame count"; cat "$D/out.txt"; exit 1; }

rm -rf "$D"
echo "PASS: malint consumer validation (help + upstream sample -N3)"
exit 0
