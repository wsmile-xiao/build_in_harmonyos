#!/bin/sh
# mbuffer 20260511 - standalone consumer probe.
# Runs the installed binary the way a shell user would and asserts on real
# output.  Exits non-zero on the first failed expectation.
#
# NOTE: shebang is /bin/sh on purpose -- /bin/bash does not exist on HarmonyOS
# and /tmp is read-only, so all scratch files stay under $1.
set -e
D=${1:-.}
if [ ! -d "$D" ]; then
	echo "PROBE_FAIL: no such work dir: $D" >&2
	exit 2
fi
MB=$(command -v mbuffer)
if [ -z "$MB" ]; then
	echo "PROBE_FAIL: mbuffer not on PATH" >&2
	exit 2
fi
SUM=$(command -v sha256sum)
if [ -z "$SUM" ]; then
	echo "PROBE_FAIL: sha256sum not on PATH" >&2
	exit 2
fi

IN="$D/probe-in.bin"
OUT="$D/probe-out.bin"
LOG="$D/probe-run.log"

# 1 MiB of deterministic data (dd of /dev/zero would hash to a trivial pattern)
i=0
: > "$IN"
while [ $i -lt 64 ]; do
	head -c 16384 /dev/urandom >> "$IN" 2>/dev/null || head -c 16384 "$MB" >> "$IN"
	i=$((i + 1))
done
test -s "$IN" || { echo "PROBE_FAIL: could not build the payload" >&2; exit 1; }

# 1. the buffer must not alter a single byte
"$MB" -q -s 32k -i "$IN" -o "$OUT"
if [ ! -f "$OUT" ]; then
	echo "PROBE_FAIL: no output produced" >&2
	exit 1
fi
A=$("$SUM" "$IN" | cut -d' ' -f1)
B=$("$SUM" "$OUT" | cut -d' ' -f1)
if [ "$A" != "$B" ]; then
	echo "PROBE_FAIL: digest changed ($A != $B)" >&2
	exit 1
fi
SIZE=$(wc -c "$IN")
echo "PROBE_OK 1: $SIZE bytes round-tripped unchanged"

# 2. mbuffer's own digest backend must agree with the external one
DST=$("$MB" -q --md5 -i "$IN" -o /dev/null 2>&1 | sed -n 's/.*hash: *\([0-9a-f]*\).*/\1/p')
if [ -z "$DST" ]; then
	echo "PROBE_FAIL: --md5 produced no digest line" >&2
	exit 1
fi
# OHOS 设备 shell 里 md5sum 是 alias，`command -v md5sum` 返回的是别名定义串
# "alias md5sum=md5sum" 而不是路径 ：把它当可执行文件调用会报
# "inaccessible or not found" 并让 WANT 变成空串，从而把正确的摘要判成假失败。
# 判据不变（mbuffer 自算摘要必须等于独立计算的 md5），只把“探测工具”
# 换成真实可执行性探测，并直接用命令名调用让 shell 自己解析别名。
if echo x | md5sum >/dev/null 2>&1; then
	WANT=$(md5sum "$IN" | cut -d' ' -f1)
	if [ "$DST" != "$WANT" ]; then
		echo "PROBE_FAIL: mbuffer md5 $DST != md5sum $WANT" >&2
		exit 1
	fi
	echo "PROBE_OK 2: mbuffer --md5 == md5sum ($DST)"
else
	echo "PROBE_OK 2: mbuffer --md5 produced a digest ($DST), no md5sum to cross-check"
fi

# 3. the throughput report must exist and must not be a zero measurement
"$MB" -s 64k -i "$IN" -o /dev/null > "$LOG" 2>&1 || true
if ! grep -q "average of" "$LOG"; then
	echo "PROBE_FAIL: no throughput summary in $LOG" >&2
	exit 1
fi
if grep -q "average of  *0\.0 " "$LOG"; then
	echo "PROBE_FAIL: measured throughput reported as zero" >&2
	cat "$LOG" >&2
	exit 1
fi
echo "PROBE_OK 3: throughput summary present"

# 4. 多输出契约：`-o` 可重复传，每个汇点都必须拿到逐字节相同的流；且 `-f` 必须能
#    覆盖已存在的目标。（真正的"切卷"是上游 test4/test5 的活：它靠 tapetest.so 注入
#    ENOSPC 才触发，而 `-n/-A` 是**输入侧**卷加载器。实测 `-f -o base -H` 只产出
#    `base` 一个文件 ⇒ 在这里断言出现 `base.*` 分卷，是在测 mbuffer 没有实现的行为。）
O1="$D/probe-out1"
O2="$D/probe-out2"
rm -f "$O1" "$O2"
"$MB" -q -s 128k -o "$O1" -o "$O2" -i "$IN" >/dev/null 2>&1
for o in "$O1" "$O2"; do
	if [ ! -s "$o" ]; then
		echo "PROBE_FAIL: multi-output wrote nothing to $o" >&2
		exit 1
	fi
	c=$("$SUM" "$o" | cut -d' ' -f1)
	if [ "$c" != "$A" ]; then
		echo "PROBE_FAIL: $o digest $c != input $A" >&2
		exit 1
	fi
done
"$MB" -q -s 128k -f -o "$O1" -i "$IN" >/dev/null 2>&1
c=$("$SUM" "$O1" | cut -d' ' -f1)
if [ "$c" != "$A" ]; then
	echo "PROBE_FAIL: -f did not overwrite the existing target ($c != $A)" >&2
	exit 1
fi
echo "PROBE_OK 4: both -o sinks byte-exact and -f overwrites an existing target"

echo "PROBE_PASS mbuffer consumer probe: 4/4 checks"
