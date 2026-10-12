#!/usr/bin/env bash
# jomon test_package 断言脚本（测试源文件；CI L0c/L0e 与本仓 PF3 要求）
#
# 用法: bash test.sh <安装前缀>/bin/jomon
#
# 三条断言都执行被测包的真实二进制（R34，非打印空壳）：
#   1) --version  版本号由构建注入（configure 的 JOMON_VERSION -> config.mk）
#   2) --help     上游 main.c 的 print_help_and_exit()，输出 "jomon <ver>" + Usage
#   3) -ddd -f "tcp or icmp"
#      上游 main.c 的 print_bpf_and_exit() 在接口初始化之前 exit(0)，离线可跑
#      （无需 root/网卡）。BPF_DUMP_MODE_INT 输出格式：第一行 = BPF 指令条数，
#      随后每行 "code jt jf k"。
#      过滤器只用上游 tcpdump 语法的已实现子集（README 原文："tcpdump syntax
#      has very limited support for now"）：port/host/ether/igmp/vlan 等 token
#      在词法表 bpf/pcap_lexer.re 里有定义，但解析器 bpf/pcap_parser.c 的
#      nud()/led() 未实现对应分支 -> bpf.size == 0 -> "pcap_compile error"。
#      实测可用：ip / ip6 / tcp / udp / arp / icmp / "tcp or icmp" / "ip and tcp"。
set -u

BIN="${1:?usage: bash test.sh <path-to-jomon>}"
[ -x "$BIN" ] || { echo "FAIL: 不是可执行文件: $BIN" >&2; exit 1; }

TMP="$(mktemp -d 2>/dev/null)" || TMP="./jomon-test-$$"
mkdir -p "$TMP"
rc=0
fail() { echo "FAIL: $*" >&2; rc=1; }

# 1) --version
"$BIN" --version > "$TMP/version.txt" 2>&1
if [ $? -ne 0 ]; then
    fail "--version 退出码非 0"
else
    grep -q "0.6.4" "$TMP/version.txt" \
        || fail "--version 未输出注入的版本号: $(cat "$TMP/version.txt")"
fi
echo "OK: $("$BIN" --version 2>&1 | sed -n '1p')"

# 2) --help
"$BIN" --help > "$TMP/help.txt" 2>&1
[ $? -eq 0 ] || fail "--help 退出码非 0"
grep -q "Usage: jomon" "$TMP/help.txt" || fail "--help 未输出用法"
grep -q -- "--list-interfaces" "$TMP/help.txt" || fail "--help 未输出长选项表"
echo "OK: --help 输出 $(grep -c . "$TMP/help.txt") 行选项说明"

# 3) 离线 BPF 过滤器编译 + 反汇编（-ddd = BPF_DUMP_MODE_INT）
"$BIN" -ddd -f "tcp or icmp" > "$TMP/bpf.txt" 2>&1
if [ $? -ne 0 ]; then
    fail "-ddd -f 退出码非 0: $(cat "$TMP/bpf.txt")"
else
    n="$(sed -n '1p' "$TMP/bpf.txt")"
    case "$n" in
        ''|*[!0-9]*)
            fail "-ddd 首行不是指令条数: '$n'"
            ;;
        *)
            lines="$(sed -n '2,$p' "$TMP/bpf.txt" | grep -c .)"
            if [ "$n" -lt 1 ]; then
                fail "-ddd 指令条数为 0"
            elif [ "$lines" -ne "$n" ]; then
                fail "BPF 行数($lines) 与声明的指令条数($n) 不一致"
            else
                echo "OK: -ddd -f 'tcp or icmp' 编译出 $n 条 BPF 指令"
            fi
            ;;
    esac
fi

rm -rf "$TMP"
if [ "$rc" -eq 0 ]; then
    echo "test.sh: 3/3 checks passed"
fi
exit "$rc"
