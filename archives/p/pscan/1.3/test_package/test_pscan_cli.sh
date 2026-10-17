#!/bin/sh
# 消费者测试:真机执行交付的 pscan,用上游自带 test.c(故意标注 good/bad)断言检出行为
BIN="$1"
SRCDIR="$2"
test -x "$BIN" || exit 1
test -f "$SRCDIR/test.c" || exit 1

# 1) 扫描上游自带 test.c(-w 打开 Warning 级):必须检出 line 64/75 两处
#    非静态格式串。pscan 在发现 SECURITY 级问题时以非 0 退出,属预期行为,
#    不影响检出断言。
"$BIN" -w "$SRCDIR/test.c" > scan.out 2>&1
grep -q "test.c:64" scan.out || { echo "missing test.c:64 in:"; cat scan.out; exit 1; }
grep -q "test.c:75" scan.out || { echo "missing test.c:75 in:"; cat scan.out; exit 1; }

# 2) 干净文件零告警
printf 'int main(void){return 0;}\n' > clean.c
"$BIN" -w clean.c > clean.out 2>&1
test ! -s clean.out || { echo "unexpected warnings:"; cat clean.out; exit 1; }

echo "pscan consumer test OK"
