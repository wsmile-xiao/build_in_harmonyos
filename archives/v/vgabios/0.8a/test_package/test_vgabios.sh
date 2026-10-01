#!/data/service/hnp/bin/bash
# test_vgabios.sh — vgabios 消费者功能测试（conan test_package 入口）
#
# 用法:   bash test_vgabios.sh <package_folder>
# 退出码: 0 = 全部用例通过；1 = 存在失败用例；2 = 参数错误
#
# 实质消费被测包（R34）：直接读取包内 share/vgabios/ 的 8086 Option ROM 镜像
# 逐字节校验其结构，并实际运行包内 bin/biossums 对 ROM 做校验和修复。
#
# 用例清单（9 项，其中 1 项为鸿蒙平台专有）：
#   TC-01-rom-inventory    5 个 ROM 镜像齐备且尺寸与 0.8a 基线一致
#   TC-02-rom-signature    每个 ROM 具备 x86 Option ROM 签名 0x55AA
#   TC-03-rom-checksum     每个 ROM 的校验和 ≡ 0 (mod 256)（biossums 写入）
#   TC-04-rom-sizefield    每个 ROM 的 data[2] 长度字段与文件大小一致
#   TC-05-pci-structure    每个 ROM 的 PCIR 结构（指针/magic/Vendor/Device/ImageLen）
#   TC-06-rom-ident        IBM 标识 (0x1e) 与 LGPL VGABios 版本串
#   TC-07-variant-tags     cirrus/banshee 变体标记 + debug 变体 DEBUG 串区分
#   TC-08-biossums-fix     实际运行 biossums 修复被破坏的 ROM 校验和
#   TC-09-ohos-host-abi    【鸿蒙特有】bin/biossums 为 OHOS 目标 AArch64 ELF 且可在本机执行

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ $# -lt 1 ]; then
    echo "usage: $0 <package_folder>" >&2
    exit 2
fi
PKG_DIR="$1"
ROM_DIR="$PKG_DIR/share/vgabios"
BIN_DIR="$PKG_DIR/bin"
BIOSSUMS="$BIN_DIR/biossums"

if [ ! -d "$ROM_DIR" ]; then
    echo "FAIL: ROM 目录不存在: $ROM_DIR" >&2
    exit 1
fi

WORK="$(mktemp -d)"
LOGS="$WORK/logs"
mkdir -p "$LOGS" "$WORK/run"

TOTAL=0
PASS=0
FAIL=0
SKIP=0
CUR=""
RESULTS=()

case_begin() {
    CUR="$1"
    TOTAL=$((TOTAL + 1))
    mkdir -p "$WORK/run/$CUR"
    echo "── [$CUR] $2"
}
case_pass() {
    PASS=$((PASS + 1))
    RESULTS+=("PASS  $CUR")
    echo "   → PASS${1:+ ($1)}"
}
case_fail() {
    FAIL=$((FAIL + 1))
    RESULTS+=("FAIL  $CUR — $1")
    echo "   → FAIL: $1"
}
case_skip() {
    SKIP=$((SKIP + 1))
    RESULTS+=("SKIP  $CUR — $1")
    echo "   → SKIP: $1"
}

vfy() {
    python3 "$SCRIPT_DIR/verify_rom.py" "$@"
}

ROM_VGABIOS="$ROM_DIR/VGABIOS-lgpl-latest.bin"
ROM_VGABIOS_DBG="$ROM_DIR/VGABIOS-lgpl-latest.debug.bin"
ROM_CIRRUS="$ROM_DIR/VGABIOS-lgpl-latest.cirrus.bin"
ROM_CIRRUS_DBG="$ROM_DIR/VGABIOS-lgpl-latest.cirrus.debug.bin"
ROM_BANSHEE="$ROM_DIR/VGABIOS-lgpl-latest.banshee.bin"

# name:expected_size:pcir_vendor:pcir_device
ROMS=(
  "VGABIOS-lgpl-latest.bin:38400:1234:1111"
  "VGABIOS-lgpl-latest.debug.bin:39424:1234:1111"
  "VGABIOS-lgpl-latest.cirrus.bin:33280:1013:00b8"
  "VGABIOS-lgpl-latest.cirrus.debug.bin:33280:1013:00b8"
  "VGABIOS-lgpl-latest.banshee.bin:32768:121a:0003"
)

echo "=============================================================="
echo " vgabios test_package — pkg=$PKG_DIR"
echo " work=$WORK"
echo "=============================================================="

# ── TC-01 ROM 清单与基线尺寸 ───────────────────────────────────
case_begin TC-01-rom-inventory "5 个 ROM 镜像齐备且尺寸与 0.8a 基线一致"
tc01_bad=""
for entry in "${ROMS[@]}"; do
    IFS=':' read -r name want _v _d <<<"$entry"
    if [ ! -f "$ROM_DIR/$name" ]; then
        tc01_bad="$tc01_bad 缺失:$name"
        continue
    fi
    got=$(stat -c%s "$ROM_DIR/$name")
    if [ "$got" != "$want" ]; then
        tc01_bad="$tc01_bad 尺寸不符:$name(got=$got,want=$want)"
    fi
done
count=$(ls -1 "$ROM_DIR"/VGABIOS-lgpl-latest*.bin 2>/dev/null | wc -l)
ls -l "$ROM_DIR" >"$LOGS/TC-01-inventory.txt" 2>&1
if [ -n "$tc01_bad" ]; then
    case_fail "$tc01_bad"
elif [ "$count" != "5" ]; then
    case_fail "ROM 数量为 $count，期望 5"
else
    case_pass "5/5 ROM 尺寸匹配基线"
fi

# ── TC-02 x86 Option ROM 签名 ─────────────────────────────────
case_begin TC-02-rom-signature "每个 ROM 偏移 0 处为 0x55AA"
tc02_bad=""
for entry in "${ROMS[@]}"; do
    IFS=':' read -r name _v _d _e <<<"$entry"
    if ! vfy signature "$ROM_DIR/$name" >>"$LOGS/TC-02-signature.log" 2>&1; then
        tc02_bad="$tc02_bad $name"
    fi
done
if [ -n "$tc02_bad" ]; then
    case_fail "缺少 0x55AA 签名:$tc02_bad"
else
    case_pass "5/5 具备 Option ROM 签名"
fi

# ── TC-03 ROM 校验和 ──────────────────────────────────────────
case_begin TC-03-rom-checksum "每个 ROM 前 data[2]*512 字节求和 ≡ 0 (mod 256)"
tc03_bad=""
for entry in "${ROMS[@]}"; do
    IFS=':' read -r name _v _d _e <<<"$entry"
    if ! vfy checksum "$ROM_DIR/$name" >>"$LOGS/TC-03-checksum.log" 2>&1; then
        tc03_bad="$tc03_bad $name"
    fi
done
if [ -n "$tc03_bad" ]; then
    case_fail "校验和非 0:$tc03_bad"
else
    case_pass "5/5 校验和有效"
fi

# ── TC-04 ROM 长度字段 ────────────────────────────────────────
case_begin TC-04-rom-sizefield "每个 ROM 的 data[2]*512 == 文件大小"
tc04_bad=""
for entry in "${ROMS[@]}"; do
    IFS=':' read -r name _v _d _e <<<"$entry"
    if ! vfy sizefield "$ROM_DIR/$name" >>"$LOGS/TC-04-sizefield.log" 2>&1; then
        tc04_bad="$tc04_bad $name"
    fi
done
if [ -n "$tc04_bad" ]; then
    case_fail "长度字段不一致:$tc04_bad"
else
    case_pass "5/5 长度字段自洽"
fi

# ── TC-05 PCI 数据结构 (PCIR) ─────────────────────────────────
case_begin TC-05-pci-structure "PCIR 指针/magic/Vendor/Device/ImageLen 全部匹配"
tc05_bad=""
for entry in "${ROMS[@]}"; do
    IFS=':' read -r name _s vendor device <<<"$entry"
    if ! vfy pcir "$ROM_DIR/$name" "$vendor" "$device" >>"$LOGS/TC-05-pcir.log" 2>&1; then
        tc05_bad="$tc05_bad $name"
    fi
done
if [ -n "$tc05_bad" ]; then
    case_fail "PCIR 校验失败:$tc05_bad"
else
    case_pass "5/5 PCIR 结构正确"
fi

# ── TC-06 IBM 标识与版本串 ────────────────────────────────────
case_begin TC-06-rom-ident "0x1e 处 IBM 标识 + 包内 LGPL VGABios 版本串"
tc06_bad=""
for entry in "${ROMS[@]}"; do
    IFS=':' read -r name _v _d _e <<<"$entry"
    if ! vfy bytes-at "$ROM_DIR/$name" 1e 49424d >>"$LOGS/TC-06-ident.log" 2>&1; then
        tc06_bad="$tc06_bad IBM:$name"
    fi
    if ! vfy contains "$ROM_DIR/$name" "Bochs VGABios" >>"$LOGS/TC-06-ident.log" 2>&1; then
        tc06_bad="$tc06_bad banner:$name"
    fi
done
if [ -n "$tc06_bad" ]; then
    case_fail "$tc06_bad"
else
    case_pass "IBM 标识 + VGABios 版本串齐备"
fi

# ── TC-07 变体标记（cirrus/banshee/debug）──────────────────────
case_begin TC-07-variant-tags "cirrus/banshee 变体串与 debug 变体 DEBUG 串区分"
tc07_bad=""
for rom in "$ROM_CIRRUS" "$ROM_CIRRUS_DBG"; do
    vfy contains "$rom" "cirrus-compatible VGA is detected" >>"$LOGS/TC-07-variant.log" 2>&1 \
        || tc07_bad="$tc07_bad cirrus:$(basename "$rom")"
done
vfy contains "$ROM_BANSHEE" "VGABIOS Banshee extension" >>"$LOGS/TC-07-variant.log" 2>&1 \
    || tc07_bad="$tc07_bad banshee-ext"
vfy contains "$ROM_BANSHEE" "3dfx Voodoo" >>"$LOGS/TC-07-variant.log" 2>&1 \
    || tc07_bad="$tc07_bad banshee-3dfx"
# debug 变体含调试专用串（cirrus 走独立调试路径）；release 变体不含
vfy contains "$ROM_VGABIOS_DBG" "--> Unknown int10" >>"$LOGS/TC-07-variant.log" 2>&1 \
    || tc07_bad="$tc07_bad debug串缺失:vgabios.debug"
vfy contains "$ROM_CIRRUS_DBG" "vgabios cirrus call" >>"$LOGS/TC-07-variant.log" 2>&1 \
    || tc07_bad="$tc07_bad debug串缺失:cirrus.debug"
for rom in "$ROM_VGABIOS" "$ROM_CIRRUS" "$ROM_BANSHEE"; do
    vfy not-contains "$rom" "--> Unknown int10" >>"$LOGS/TC-07-variant.log" 2>&1 \
        || tc07_bad="$tc07_bad release误含debug串:$(basename "$rom")"
done
if [ -n "$tc07_bad" ]; then
    case_fail "$tc07_bad"
else
    case_pass "cirrus/banshee/debug 变体标记全部匹配"
fi

# ── TC-08 biossums 实际修复被破坏的 ROM 校验和 ────────────────
case_begin TC-08-biossums-fix "运行包内 biossums 修复被破坏的 ROM 校验和"
if [ ! -x "$BIOSSUMS" ]; then
    case_fail "bin/biossums 不存在或不可执行"
else
    cp "$ROM_VGABIOS" "$WORK/run/$CUR/rom.bin"
    # 破坏一个载荷字节（偏移 0x2000）→ 校验和随之失效
    python3 - "$WORK/run/$CUR/rom.bin" <<'PY' >>"$LOGS/TC-08-fix.log" 2>&1
import sys
p = sys.argv[1]
d = bytearray(open(p, 'rb').read())
d[0x2000] ^= 0xFF
open(p, 'wb').write(d)
PY
    if vfy checksum "$WORK/run/$CUR/rom.bin" >>"$LOGS/TC-08-fix.log" 2>&1; then
        case_fail "破坏后校验和仍为 0（样本构造失败）"
    else
        ( cd "$WORK/run/$CUR" && "$BIOSSUMS" rom.bin ) >>"$LOGS/TC-08-biossums.stdout" 2>&1
        rc=$?
        size_after=$(stat -c%s "$WORK/run/$CUR/rom.bin")
        payload_ok=$(python3 - "$WORK/run/$CUR/rom.bin" <<'PY'
import sys
d = open(sys.argv[1], 'rb').read()
print("ok" if d[0x2000] == 0xFF else "bad")
PY
)
        if [ $rc -ne 0 ]; then
            case_fail "biossums 退出码 $rc != 0"
        elif ! vfy checksum "$WORK/run/$CUR/rom.bin" >>"$LOGS/TC-08-fix.log" 2>&1; then
            case_fail "biossums 未能修复 ROM 校验和"
        elif [ "$payload_ok" != "ok" ]; then
            case_fail "修复过程丢失了载荷字节 (0x2000)"
        elif [ $((size_after % 512)) -ne 0 ] || [ "$size_after" -lt 38400 ]; then
            case_fail "修复后大小 $size_after 非 512 对齐/小于原 ROM"
        else
            case_pass "biossums exit=0，校验和已修复，载荷保留（38400→${size_after}，追加校验页）"
        fi
    fi
fi

# ── TC-09【鸿蒙特有】OHOS AArch64 原生产物与运行 ──────────────
case_begin TC-09-ohos-host-abi "【鸿蒙特有】bin/biossums 为 OHOS 目标 AArch64 ELF 且可在本机执行"
if [ ! -x "$BIOSSUMS" ]; then
    case_fail "bin/biossums 不存在或不可执行"
else
    OS_NAME="$(uname -s 2>/dev/null || echo unknown)"
    OS_MACH="$(uname -m 2>/dev/null || echo unknown)"
    echo "   本机: $(uname -s -r -m 2>/dev/null)"
    if ! vfy elf-ohos "$BIOSSUMS" >>"$LOGS/TC-09-ohos.log" 2>&1; then
        case_fail "biossums 不是 ELF64/LE/AArch64"
    elif ! ( cd "$WORK/run/$CUR" && cp "$ROM_BANSHEE" r.bin && "$BIOSSUMS" r.bin ) \
            >>"$LOGS/TC-09-run.stdout" 2>&1; then
        case_fail "biossums 无法在 OHOS 本机执行"
    elif [ "$OS_MACH" != "aarch64" ]; then
        case_skip "非 aarch64 运行环境（uname -m=$OS_MACH），仅校验 ELF 目标"
    else
        case_pass "OS=$OS_NAME/$OS_MACH，ELF64/LE/AArch64 且执行成功"
    fi
fi

# ── 汇总 ──────────────────────────────────────────────────────
echo "=============================================================="
echo " 用例明细:"
for r in "${RESULTS[@]}"; do
    echo "   $r"
done
echo "--------------------------------------------------------------"
echo " CASE SUMMARY: total=$TOTAL passed=$PASS failed=$FAIL skipped=$SKIP"
echo " 日志目录: $LOGS"
echo "=============================================================="

if [ "$FAIL" -ne 0 ]; then
    echo "RESULT: FAIL"
    exit 1
fi
echo "RESULT: PASS"
exit 0
