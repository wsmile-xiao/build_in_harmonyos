#!/data/service/hnp/bin/bash
# pcapfix consumer pipeline test — 验证修复产物对下游 pcap 消费者真正可用。
#
# 场景：抓包分析流水线拿到一个全局头损坏的 pcap → pcapfix 修复 →
# 下游读取器按 pcap 记录链逐包消费：
#   - 从包头读 caplen（u32 LE，offset+8），按 16B 头 + caplen 步进走完整个文件
#   - 每包提取 payload 并与原始写入内容逐字节比对（cmp）
#   - 走完 4 包后位置必须正好等于文件大小（记录链完整、无尾部垃圾）
# 夹具与 test_pcapfix.sh 同法内联生成，payload 各包字节数与内容互不相同
# （错位/错 caplen 立即暴露）。
set -e
set -u

if [ $# -lt 1 ]; then
    echo "usage: consumer_pcap_repair_pipeline.sh <package_bin_dir>" >&2
    exit 2
fi
BIN="$1"
P="$BIN/pcapfix"

[ -x "$P" ] || { echo "pcapfix binary not found/executable: $P" >&2; exit 1; }

tmp="${TMPDIR:-$HOME/tmp}/pcapfix_consumer.$$"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

# ---- 生成夹具：24B 全局头 + 4 包（16B 头 + 定长 payload，长度互异）----
hdr_rest='\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x01\x00\x00\x00'
CAPLENS="60 80 60 70"           # 4 包的 caplen
FIXTURE_SIZE=358                 # 24 + (16+60)+(16+80)+(16+60)+(16+70)

gen_packets() { # $1 = output file（追加，不截断——全局头已由调用方写入）；每包 payload 写到 $tmp/payload_<i>.bin
    local f="$1" i=0 c
    for c in $CAPLENS; do
        i=$((i + 1))
        # ts_sec 统一 0x5fe2245f（LE 字节序！）、ts_usec=0：
        # pcapfix 合理性检查要求相邻包 ts_sec 差 ≤ 86400s，否则触发暴力重同步
        printf "\x5f\xe2\x24\x5f\x00\x00\x00\x00" >> "$f"
        printf "\\x$(printf '%02x' "$c")\\x00\\x00\\x00" >> "$f"
        printf "\\x$(printf '%02x' "$c")\\x00\\x00\\x00" >> "$f"  # caplen = len = c
        printf "$i%.0s" $(seq 1 "$c") > "$tmp/payload_$i.bin"
        cat "$tmp/payload_$i.bin" >> "$f"
    done
}

printf "\xd4\xc3\xb2\xa1$hdr_rest" > "$tmp/good.pcap"
gen_packets "$tmp/good.pcap"
[ "$(wc -c < "$tmp/good.pcap")" -eq "$FIXTURE_SIZE" ] || {
    echo "fixture size unexpected" >&2; exit 1; }

# 损坏：仅清零 4 字节 magic（其余逐字节一致）
printf "\x00\x00\x00\x00$hdr_rest" > "$tmp/damaged.pcap"
gen_packets "$tmp/damaged.pcap"
[ "$(wc -c < "$tmp/damaged.pcap")" -eq "$FIXTURE_SIZE" ] || {
    echo "damaged fixture size unexpected" >&2; exit 1; }

# ---- 修复 ----
"$P" -o "$tmp/fixed.pcap" "$tmp/damaged.pcap" > "$tmp/fix.out" 2>&1 || {
    echo "pcapfix exited non-zero:" >&2; cat "$tmp/fix.out" >&2; exit 1; }
grep -q 'SUCCESS: 1 Corruption(s) fixed' "$tmp/fix.out" || {
    echo "missing SUCCESS banner:" >&2; cat "$tmp/fix.out" >&2; exit 1; }

# ---- 下游消费者：走记录链 ----
read4le() { # $1=file $2=offset → 输出 u32 LE 十进制
    local b
    b=$(dd if="$1" bs=1 skip="$2" count=4 2>/dev/null | od -An -tx1 | tr -d ' \n')
    [ "${#b}" -eq 8 ] || { echo "read4le: short read at $2" >&2; return 1; }
    echo $(( 0x${b:6:2} * 16777216 + 0x${b:4:2} * 65536 + 0x${b:2:2} * 256 + 0x${b:0:2} ))
}

off=24
i=0
for c in $CAPLENS; do
    i=$((i + 1))
    cap=$(read4le "$tmp/fixed.pcap" $((off + 8)))
    [ "$cap" -eq "$c" ] || {
        echo "record $i: caplen $cap != expected $c" >&2; exit 1; }
    dd if="$tmp/fixed.pcap" of="$tmp/got_payload.bin" bs=1 \
       skip=$((off + 16)) count="$cap" 2>/dev/null
    cmp -s "$tmp/payload_$i.bin" "$tmp/got_payload.bin" || {
        echo "record $i: payload bytes differ from original" >&2; exit 1; }
    off=$((off + 16 + cap))
done

# 记录链必须恰好走满整个文件（无尾部垃圾/未消费字节）
[ "$off" -eq "$(wc -c < "$tmp/fixed.pcap")" ] || {
    echo "record chain ends at $off but file is $(wc -c < "$tmp/fixed.pcap") bytes" >&2
    exit 1; }

echo "pcapfix consumer pipeline test OK (4/4 records, payloads byte-identical)"
