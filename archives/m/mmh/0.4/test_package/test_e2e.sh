#!/bin/sh
# mmh 0.4 鸿蒙特有测试 — 完整消费者端到端用例（8 例）
# 链路：mbox 夹具 -> inc 投递 -> scan 浏览 -> pick 检索 ->
#       mhlist 部件列表 -> mhstore 提取 base64 附件并校验内容 ->
#       refile 归档 -> 终态复查。全部使用包内 CLI，独立 context（不碰 $HOME/Mail）。

set -u
fail=0
ok()  { echo "PASS [$1] $2"; }
bad() { echo "FAIL [$1] $2"; fail=1; }

workdir="$PWD/e2e-work"
rm -rf "$workdir"
mkdir -p "$workdir/mail" "$workdir/.mmh"
printf 'Path: %s\nInbox: +inbox\n' "$workdir/mail" > "$workdir/.mmh/profile"
export MMH="$workdir/.mmh"
cd "$workdir"

# 夹具：两条消息（1 简单文本 / 2 multipart/mixed，含 base64 octet-stream 附件）
cat > drop.mbox <<'EOF'
From e2e1@example.com Sun Oct  4 12:00:00 2026
From: e2e1@example.com
To: box@example.com
Subject: E2E simple
Date: Sun, 04 Oct 2026 12:00:00 +0800

simple body text
From e2e2@example.com Sun Oct  4 12:00:01 2026
From: e2e2@example.com
To: box@example.com
Subject: E2E multipart
Date: Sun, 04 Oct 2026 12:00:01 +0800
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="E2EBOUNDARY"

--E2EBOUNDARY
Content-Type: text/plain; charset=us-ascii

multipart body text
--E2EBOUNDARY
Content-Type: application/octet-stream; name="payload.bin"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="payload.bin"

TU1ILUUyRS1QQVlMT0FELU9LCg==
--E2EBOUNDARY--
EOF

folder -create +inbox >/dev/null 2>&1

# 1) inc -file 投递 mbox -> inbox 计 2 条消息
inc -file drop.mbox +inbox >/dev/null 2>&1
f1=$(folder +inbox 2>&1)
echo "$f1" | grep -q 'has 2 message' \
	&& ok 1 "inc -file -> $f1" \
	|| bad 1 "inc -file -> $f1"

# 2) scan 列出两条消息的 Subject
s2=$(scan +inbox 2>&1)
echo "$s2" | grep -q 'E2E simple' && echo "$s2" | grep -q 'E2E multipart' \
	&& ok 2 "scan shows both subjects" \
	|| bad 2 "scan output: $s2"

# 3) pick -subject 命中 multipart 消息（编号应恰为 2）
p3=$(pick +inbox -subject multipart 2>&1)
[ "$p3" = "2" ] \
	&& ok 3 "pick -subject multipart -> $p3" \
	|| bad 3 "pick -subject multipart -> $p3"

# 4) mhlist 呈现 octet-stream 部件
ml4=$(mhlist +inbox 2 2>&1)
echo "$ml4" | grep -q 'application/octet-stream' \
	&& ok 4 "mhlist shows application/octet-stream part" \
	|| bad 4 "mhlist output: $ml4"

# 5) mhstore -auto -part 2 提取附件，按 Content-Disposition 命名并校验内容
rm -f payload.bin
mhstore -auto -part 2 +inbox 2 >/dev/null 2>&1
if [ -f payload.bin ] && grep -q 'MMH-E2E-PAYLOAD-OK' payload.bin; then
	ok 5 "mhstore stored payload.bin (content verified)"
else
	bad 5 "mhstore payload.bin missing or wrong (ls: $(ls -1 2>/dev/null | tr '\n' ' '))"
fi

# 6) refile 将 inbox 第 1 条归档到 +archive
refile -src +inbox 1 +archive >/dev/null 2>&1
grep -q 'Subject: E2E simple' mail/archive/1 2>/dev/null \
	&& ok 6 "refile moved msg 1 into archive" \
	|| bad 6 "refile: archive/1 missing or wrong ($(ls -1 mail/archive 2>&1 | tr '\n' ' '))"

# 7) archive 计 1 条
f7=$(folder +archive 2>&1)
echo "$f7" | grep -q 'has 1 message' \
	&& ok 7 "archive -> $f7" \
	|| bad 7 "archive -> $f7"

# 8) inbox 终态计 1 条，且保留的是 multipart 消息
f8=$(folder +inbox 2>&1)
if echo "$f8" | grep -q 'has 1 message' && grep -q 'multipart/mixed' mail/inbox/2 2>/dev/null; then
	ok 8 "inbox final state: $f8（保留 msg 2 multipart）"
else
	bad 8 "inbox final state: $f8"
fi

echo "== test_e2e.sh: $( [ $fail -eq 0 ] && echo ALL-PASS || echo FAILED ) =="
exit $fail
