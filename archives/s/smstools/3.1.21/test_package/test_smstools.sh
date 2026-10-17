#!/bin/sh
# 消费者测试：以使用者身份运行打包后的 smsd，断言其可观察行为。
# 用法: test_smstools.sh <smsd 可执行文件> <临时工作目录>
# smsd 的守护功能需要实体 GSM modem，此处断言的是不依赖 modem 的确定性行为：
# 帮助输出、GSM 7bit packed 编解码（-E/-D）、配置文件读取路径。
# 不启用 set -e：断言依赖失败命令的退出码（rc=$? 捕获），-e 会中断断言语义
set -u

BIN="$1"
WORK="$2"
CONF="$WORK/smsd.conf"
: > "$CONF"

pass=0
fail=0

ok() {
    pass=$((pass + 1))
    printf 'PASS %s\n' "$1"
}

bad() {
    fail=$((fail + 1))
    printf 'FAIL %s\n' "$1"
    printf '     %s\n' "$2"
}

equals() { # 名称 期望 实际
    if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "expected=[$2] actual=[$3]"; fi
}

if [ ! -x "$BIN" ]; then
    printf 'FAIL binary-not-executable [%s]\n' "$BIN"
    exit 1
fi

# 1) 帮助输出：退出码 0 + 首行摘要 + Usage 段
help_out=$("$BIN" -h 2>&1)
help_rc=$?
equals "help-exit-code" "0" "$help_rc"
case "$help_out" in
    *"smsd spools incoming and outgoing sms."*) ok "help-summary-line" ;;
    *) bad "help-summary-line" "missing summary line in: $(printf '%s' "$help_out" | head -1)" ;;
esac
case "$help_out" in
    *"Usage:"*"smsd [options]"*) ok "help-usage-section" ;;
    *) bad "help-usage-section" "missing usage block" ;;
esac

# 2) GSM 7bit 编码：'Hello' -> C8329BFD06（packed 十六进制，上游 pdu.c 实现）
enc=$("$BIN" -c "$CONF" -EHello 2>&1)
equals "encode-hello" "C8329BFD06" "$enc"

# 3) GSM 7bit 解码：C8329BFD06 -> Hello
dec=$("$BIN" -c "$CONF" -DC8329BFD06 2>&1)
equals "decode-hello" "Hello" "$dec"

# 4) 含空格多字符往返：编码后再解码必须还原原文
enc2=$("$BIN" -c "$CONF" "-EHello world" 2>&1)
dec2=$("$BIN" -c "$CONF" "-D${enc2}" 2>&1)
equals "roundtrip-hello-world" "Hello world" "$dec2"

# 5) 配置文件缺失时错误路径：非 0 退出 + 明确的 config 报错
err=$("$BIN" -c "$WORK/no-such.conf" -EHello 2>&1)
rc=$?
missing_ok=0
[ "$rc" -ne 0 ] && missing_ok=1
equals "missing-config-exit-code" "1" "$missing_ok"
case "$err" in
    *"Cannot open config file"*) ok "missing-config-message" ;;
    *) bad "missing-config-message" "actual=[$err]" ;;
esac

printf 'smstools consumer tests: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
