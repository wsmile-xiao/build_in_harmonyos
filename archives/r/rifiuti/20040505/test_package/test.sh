#!/data/service/hnp/bin/bash
# test_package/test.sh — rifiuti 20040505 功能测试（消费者视角，跑真实安装产物）
#
# rifiuti 的唯一职责就是解析 Windows 回收站的 INFO2 文件，所以本测试全部围绕
# "给定一条 INFO2 记录，输出的字段是否与记录里的字节一致" 来断言：
#   * 记录长度取自文件偏移 0x0C 的 DWORD          (rifiuti.c:165-166)
#   * 第一条记录从文件偏移 0x10 开始              (rifiuti.c:182)
#   * 记录内：路径 @+0x04，索引 @+0x108，盘符 @+0x10C(DWORD)，
#             删除时间 @+0x110(Windows FILETIME, 8 字节)，大小 @+0x118(DWORD)
#                                                (rifiuti.c:191-201)
#   * FILETIME -> POSIX 秒 = v*1e-7 - 11644473600 (rifiuti.c:86-94)
#   * 打印格式 "%02d/%02d/%02d %02d:%02d:%02d" = 月/日/年 时:分:秒 (rifiuti.c:199)
# 样本由本脚本内嵌的 python3 片段按上述偏移现场构造（构造脚本可复核、无外部
# 依赖、不落盘到 /tmp —— OHOS 上 /tmp 只读，故用 $TMPDIR/$HOME/tmp）。
#
# 上游没有测试套件（src/Makefile 只有 all/install/installwin/clean 四个目标，
# 无 check；包内无 tests/），所以"上游测试数"与"test_package 断言数"分开记账，
# 见 test_package/MANIFEST.yml 与 notes.md 的五维测试账本。
# 安全模式按仓内 .gitcode/code-style.md §7：脚本一律以 set -euo pipefail 开头。
# 因此这里把"取命令退出码"的调用点统一写成 rc=0; cmd || rc=$? 形态——与被替换的
# cmd; rc=$? 逐字等价（rc 仍是该命令自身的退出码），区别只在于真断言失败时仍会走到
# ck/SUMMARY 记账，而不是被 set -e 当场打断（旧脚本只有 set -u，故无此约束）。
set -euo pipefail

TAB=$'\t'
PASS=0
FAIL=0
TOTAL=0

ck() { # ck <label> <rc>
    TOTAL=$((TOTAL + 1))
    if [ "$2" -eq 0 ]; then
        PASS=$((PASS + 1))
        printf '[PASS] %s\n' "$1"
    else
        FAIL=$((FAIL + 1))
        printf '[FAIL] %s\n' "$1"
    fi
}

command -v python3 >/dev/null 2>&1 || {
    echo '[FAIL] python3 不可用：无法构造 INFO2 测试样本（硬失败，不作跳过处理）'
    exit 1
}

# ---------- 0. 产物存在且是 aarch64 ELF ----------
BIN="$(command -v rifiuti || true)"
ck "rifiuti 已安装并可在 conanrun PATH 中解析" "$([ -n "$BIN" ] && echo 0 || echo 1)"
if [ -z "$BIN" ]; then
    printf '\nSUMMARY total=%d pass=%d fail=%d\n' "$TOTAL" "$PASS" "$FAIL"
    exit 1
fi
s=0
readelf -h "$BIN" 2>/dev/null | grep -q "AArch64" || s=$?
ck "产物机器码为 AArch64（readelf -h）" "$s"
file_out="$(file "$BIN" 2>/dev/null || true)"
echo "  [info] $BIN -> $file_out"

# ---------- 1. 构造 INFO2 样本 ----------
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/rifiuti-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

python3 - "$TESTDIR" <<'PYEOF'
import struct
import sys

testdir = sys.argv[1]
RECSIZE = 0x11C  # 284：记录长度，写进文件偏移 0x0C，同时是每条记录的实际字节数


def header(recsize=RECSIZE):
    # 0x00..0x0B 是上游工具根本不读的装饰字段（取 INFO2 常见魔数便于人读）；
    # 只有 0x0C 的 DWORD 会被 rifiuti.c:165-166 当成记录长度使用。
    return struct.pack("<IIII", 0x00000044, 0x000121FC, 0x00000020, recsize)


def record(index, drive, path, filetime, size):
    buf = bytearray(RECSIZE)
    struct.pack_into("<I", buf, 0x00, 0x00000044)   # 记录首 4 字节（路径从 +0x04 起）
    raw = path.encode("ascii") + b"\x00"
    assert len(raw) <= 0x108 - 0x04, "path overflows INFO2 record"
    buf[0x04:0x04 + len(raw)] = raw
    struct.pack_into("<I", buf, 0x108, index)       # rifiuti.c:192
    struct.pack_into("<I", buf, 0x10C, drive)       # rifiuti.c:193
    struct.pack_into("<Q", buf, 0x110, filetime)    # rifiuti.c:195 (FILETIME)
    struct.pack_into("<I", buf, 0x118, size)        # rifiuti.c:201
    return bytes(buf)


def win_ft(y, mo, d, h, mi, s):
    import calendar
    ts = calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0))
    return (ts + 11644473600) * 10 ** 7


rec1 = record(1, 0x43, "C:\\WINDOWS\\TEMP\\notes.txt", win_ft(2004, 5, 5, 12, 34, 56), 12345)
rec2 = record(2, 0x44, "D:\\ARCHIVE\\setup.log", win_ft(2000, 1, 1, 0, 0, 0), 1048576)
rec3 = record(3, 0x43, "C:\\EMPTY.DAT", 0, 0)   # FILETIME==0 -> 走 rifiuti.c:89 的零值分支

open(testdir + "/info2.3rec", "wb").write(header() + rec1 + rec2 + rec3)
open(testdir + "/info2.trunc", "wb").write(header() + rec1 + b"\x00" * 100)
open(testdir + "/info2.bigrec", "wb").write(header(4096) + b"\x00" * 100)
print("  [info] fixtures: info2.3rec=%d info2.trunc=%d info2.bigrec=%d bytes" % (
    16 + 3 * RECSIZE, 16 + RECSIZE + 100, 16 + 100))
PYEOF

F3="$TESTDIR/info2.3rec"
FT="$TESTDIR/info2.trunc"
FB="$TESTDIR/info2.bigrec"

# 样本自身的完整性（避免"断言其实建立在一个坏样本上"）
ck "样本 info2.3rec 长度 = 16 + 3*284 = 868" \
   "$([ "$(wc -c < "$F3")" -eq 868 ] && echo 0 || echo 1)"
dword="$(dd if="$F3" bs=1 skip=12 count=4 2>/dev/null | od -An -tx1 | tr -d ' \n')"
ck "样本偏移 0x0C 的记录长度 DWORD = 1c010000 (=284)" \
   "$([ "$dword" = "1c010000" ] && echo 0 || echo 1)"

# ---------- 2. 错误路径 ----------
out_noargs="$TESTDIR/noargs.txt"
rc=0
rifiuti >"$out_noargs" 2>&1 || rc=$?
s=0
grep -qF "Usage:  rifiuti [options] <filename>" "$out_noargs" || s=$?
ck "无参数时打印 usage" "$s"
ck "无参数时退出码 = 254（上游 exit(-2)）" "$([ "$rc" -eq 254 ] && echo 0 || echo 1)"

out_missing="$TESTDIR/missing.txt"
rc=0
rifiuti "$TESTDIR/does-not-exist" >"$out_missing" 2>&1 || rc=$?
s=0
grep -qF "ERROR - The INFO2 file cannot be opened!" "$out_missing" || s=$?
ck "打开失败时打印cannot be opened错误" "$s"
ck "打开失败时退出码 = 253（上游 exit(-3)）" "$([ "$rc" -eq 253 ] && echo 0 || echo 1)"

# ---------- 3. 正常解析：TAB 分隔 ----------
out3="$TESTDIR/parse3.txt"
rc=0
TZ=UTC rifiuti "$F3" >"$out3" 2>&1 || rc=$?
s=0
grep -qF "INFO2 File: $F3" "$out3" || s=$?
ck "首行回报被解析的 INFO2 文件路径" "$s"
s=0
grep -qxF "INDEX${TAB}DELETED TIME${TAB}DRIVE NUMBER${TAB}PATH${TAB}SIZE" "$out3" || s=$?
ck "表头行字段与分隔符正确（默认 TAB）" "$s"

exp1="1${TAB}05/05/2004 12:34:56${TAB}67${TAB}C:\\WINDOWS\\TEMP\\notes.txt${TAB}12345"
exp2="2${TAB}01/01/2000 00:00:00${TAB}68${TAB}D:\\ARCHIVE\\setup.log${TAB}1048576"
exp3="3${TAB}01/01/1970 00:00:00${TAB}67${TAB}C:\\EMPTY.DAT${TAB}0"
s=0; grep -qxF -- "$exp1" "$out3" || s=$?; ck "记录 1 逐字段解析（索引/删除时间/盘符/路径/大小）" "$s"
s=0; grep -qxF -- "$exp2" "$out3" || s=$?; ck "记录 2 逐字段解析（含 1 MiB 大小与 D 盘符）" "$s"
s=0; grep -qxF -- "$exp3" "$out3" || s=$?; ck "记录 3 的 FILETIME=0 零值分支解析为 1970-01-01" "$s"
n="$(awk 'NR>3 && length($0)>0' "$out3" | wc -l)"
ck "数据记录条数 = 3（不多不少）" "$([ "$n" -eq 3 ] && echo 0 || echo 1)"
ck "解析成功时退出码 = 0" "$([ "$rc" -eq 0 ] && echo 0 || echo 1)"

# ---------- 4. -t 自定义分隔符 ----------
outc="$TESTDIR/parse3.comma.txt"
rc=0; TZ=UTC rifiuti -t , "$F3" >"$outc" 2>&1 || rc=$?
s=0
grep -qxF "INDEX,DELETED TIME,DRIVE NUMBER,PATH,SIZE" "$outc" || s=$?
ck "-t , 生效：表头改为逗号分隔" "$s"
s=0
grep -qxF "1,05/05/2004 12:34:56,67,C:\WINDOWS\TEMP\notes.txt,12345" "$outc" || s=$?
ck "-t , 生效：数据行改为逗号分隔" "$s"

# ---------- 5. 边界：尾部残缺记录 / 声明记录长度超大 ----------
outt="$TESTDIR/trunc.txt"
rc=0
TZ=UTC rifiuti "$FT" >"$outt" 2>&1 || rc=$?
n="$(awk 'NR>3 && length($0)>0' "$outt" | wc -l)"
ck "尾部残缺记录被丢弃：只解析出 1 条" "$([ "$n" -eq 1 ] && echo 0 || echo 1)"
s=0; grep -qxF -- "$exp1" "$outt" || s=$?; ck "残缺样本里的第 1 条记录内容仍然正确" "$s"
ck "残缺样本不导致崩溃（退出码 0）" "$([ "$rc" -eq 0 ] && echo 0 || echo 1)"

outb="$TESTDIR/bigrec.txt"
rc=0
TZ=UTC rifiuti "$FB" >"$outb" 2>&1 || rc=$?
n="$(awk 'NR>3 && length($0)>0' "$outb" | wc -l)"
ck "声明记录长度 4096 而文件不足时输出 0 条" "$([ "$n" -eq 0 ] && echo 0 || echo 1)"
ck "同上场景退出码 0（无崩溃）" "$([ "$rc" -eq 0 ] && echo 0 || echo 1)"

printf '\nSUMMARY total=%d pass=%d fail=%d\n' "$TOTAL" "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
