#!/usr/bin/env bash
# test_package/test_ohos.sh — OHOS（鸿蒙 PC aarch64）独立验证
# 在 conanrun 环境（PATH 含已安装的 bin/）中执行，验证打包产物在
# OHOS 上的二进制形态与真实终端运行：
#   1. ELF64 + AArch64 + musl 解释器
#   2. OHOS 标识段（.note.ohos.ident）与代码签名段（.codesign）
#   3. RPATH/RUNPATH：mdp 静态链接 ncursesw，仅依赖系统 libc.so，
#      不应携带指向构建机的 RPATH
#   4. 真实终端（pty + TERM）下的 TUI 运行与退出
# 断言工具优先用 PATH 中的 readelf（OHOS SDK llvm 工具链自带），
# 缺失时回退到 od/grep 二进制扫描，不依赖任何固定安装路径。
set -euo pipefail

DISCOVERED=0
PASSED=0

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# 定位被测二进制：conanrun PATH 中的 mdp
MDP_BIN="$(command -v mdp)" || { echo "FAIL: mdp not found in PATH"; exit 1; }
export MDP_BIN
echo "testing: $MDP_BIN"

# readelf 取 PATH 中的（OHOS SDK llvm-readelf / binutils），可缺失
READELF="$(command -v readelf || command -v llvm-readelf || true)"

# ── Test 1: ELF64 LSB + AArch64 ──────────────────────────────
DISCOVERED=$((DISCOVERED + 1))
ELF_HDR="$(od -An -tx1 -N 20 "$MDP_BIN" | tr -d ' \n')"
# e_ident: 7f 45 4c 46(ELF magic) 02(64-bit) 01(LSB) 01(current) 00(sysv)
# e_machine: b7 00(AArch64 = 183)
ELF_OK=1
case "$ELF_HDR" in
    7f454c4602010100*) ;;
    *) ELF_OK=0 ;;
esac
MACHINE="$(printf '%s' "$ELF_HDR" | cut -c37-40)"
if [ "$ELF_OK" -eq 1 ] && [ "$MACHINE" = "b700" ]; then
    echo "OK: ELF64 LSB AArch64 (e_machine=0xb7)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: unexpected ELF header ($ELF_HDR machine=$MACHINE)"
fi

# ── Test 2: musl 解释器 /lib/ld-musl-aarch64.so.1 ────────────
DISCOVERED=$((DISCOVERED + 1))
MUSL_OK=0
if [ -n "$READELF" ]; then
    if "$READELF" -lW "$MDP_BIN" 2>/dev/null | grep -q "ld-musl-aarch64.so.1"; then
        MUSL_OK=1
    fi
elif grep -aq "ld-musl-aarch64.so.1" "$MDP_BIN"; then
    MUSL_OK=1
fi
if [ "$MUSL_OK" -eq 1 ]; then
    echo "OK: musl interpreter /lib/ld-musl-aarch64.so.1 present"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: musl interpreter not found"
fi

# ── Test 3: OHOS 标识 + .codesign 段 ─────────────────────────
# 段名记录在 section header string table 中：有 readelf 时查段表，
# 无 readelf 时 grep 二进制字符串（.note.ohos.ident/.codesign 段名）
DISCOVERED=$((DISCOVERED + 1))
NOTE_OK=0
SIG_OK=0
if [ -n "$READELF" ]; then
    "$READELF" -SW "$MDP_BIN" 2>/dev/null | grep -q "note.ohos.ident" && NOTE_OK=1
    "$READELF" -SW "$MDP_BIN" 2>/dev/null | grep -q "\.codesign" && SIG_OK=1
else
    grep -aq "note.ohos.ident" "$MDP_BIN" && NOTE_OK=1
    grep -aq "\.codesign" "$MDP_BIN" && SIG_OK=1
fi
if [ "$NOTE_OK" -eq 1 ] && [ "$SIG_OK" -eq 1 ]; then
    echo "OK: .note.ohos.ident and .codesign sections present"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: OHOS ident note=$NOTE_OK codesign=$SIG_OK"
fi

# ── Test 4: 无构建机 RPATH ───────────────────────────────────
DISCOVERED=$((DISCOVERED + 1))
RPATH_FOUND=0
if [ -n "$READELF" ]; then
    if "$READELF" -d "$MDP_BIN" 2>/dev/null | grep -qiE "rpath|runpath"; then
        RPATH_FOUND=1
    fi
else
    # 无 readelf 时退化为启发式：二进制内不应出现 conan 缓存路径字符串
    if grep -aqE "\.conan2/p|/conan/" "$MDP_BIN"; then
        RPATH_FOUND=1
    fi
fi
if [ "$RPATH_FOUND" -eq 0 ]; then
    echo "OK: no RPATH/RUNPATH (static ncursesw, system libc only)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: RPATH/RUNPATH present (static ncursesw build should not need one)"
fi

# ── Test 5: NEEDED 仅系统 libc ───────────────────────────────
DISCOVERED=$((DISCOVERED + 1))
if [ -n "$READELF" ]; then
    NEEDED="$("$READELF" -d "$MDP_BIN" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/' | sort | tr '\n' ' ')"
    if [ "$NEEDED" = "libc.so " ]; then
        echo "OK: only libc.so NEEDED (ncursesw statically linked)"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL: unexpected NEEDED set: '$NEEDED'"
    fi
else
    # 无 readelf：回退检查 musl 依赖的库名集合（libc.so 出现、
    # libncurses* 不出现即等价于仅系统 libc）
    if grep -aq "libc\.so" "$MDP_BIN" && ! grep -aq "libncurses" "$MDP_BIN"; then
        echo "OK: no libncurses dynamic dependency (static, fallback check)"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL: dynamic libncurses dependency found"
    fi
fi

# ── Test 6: 真实终端（pty）运行 + 退出 ───────────────────────
# musl ncurses 默认 terminfo 搜索路径不含 /usr/share/terminfo，
# 显式设置 TERMINFO 后 TERM=xterm-256color 才能初始化（OHOS 系统
# terminfo 数据库随基础环境安装在 /usr/share/terminfo）。
DISCOVERED=$((DISCOVERED + 1))
TERMINFO_DIR=""
for d in /usr/share/terminfo /data/usr/share/terminfo /system/usr/share/terminfo; do
    if [ -d "$d/x" ]; then
        TERMINFO_DIR="$d"
        break
    fi
done
if [ -z "$TERMINFO_DIR" ]; then
    echo "FAIL: no terminfo database found on this OHOS system"
else
PTY_OUT="$(TERMINFO="$TERMINFO_DIR" python3 - <<'PYEOF' 2>&1
import os, pty, signal, sys
signal.alarm(20)
mdp = os.environ.get("MDP_BIN", "mdp")
terminfo = os.environ.get("TERMINFO", "")
md = b"# OHOS Slide\n\n- pty terminal check\n"
r, w = os.pipe()
os.write(w, md)
os.close(w)
pid, fd = pty.fork()
if pid == 0:
    os.dup2(r, 0)
    os.close(r)
    os.environ["TERM"] = "xterm-256color"
    if terminfo:
        os.environ["TERMINFO"] = terminfo
    os.execvp(mdp, [mdp, "-"])
os.close(r)
out = b""
try:
    while True:
        d = os.read(fd, 4096)
        if not d:
            break
        out += d
        if b"OHOS Slide" in out:
            os.write(fd, b"q")  # quit viewer
            break
except OSError:
    pass
try:
    os.close(fd)
except OSError:
    pass
_, status = os.waitpid(pid, 0)
sys.stdout.buffer.write(out)
PYEOF
)" || true
PTY_CLEAN="$(printf '%s' "$PTY_OUT" | tr -d '\r')"
# ncurses 交替屏渲染:进入序列 1049h,标题文本须出现
if printf '%s' "$PTY_CLEAN" | grep -q "OHOS Slide" && \
   printf '%s' "$PTY_OUT" | grep -aq $'\x1b\[?1049h'; then
    echo "OK: mdp renders a slide on a real pty terminal and quits on 'q'"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: pty render failed (got: $PTY_OUT)"
fi
fi

echo "test_ohos: ${PASSED}/${DISCOVERED} checks passed"

if [ "$PASSED" -eq "$DISCOVERED" ]; then
    HMBS_PASSED=true
else
    HMBS_PASSED=false
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test_ohos.sh","discovered":%d,"passedCount":%d}\n' \
    "$HMBS_PASSED" "$DISCOVERED" "$PASSED"

[ "$PASSED" -eq "$DISCOVERED" ] || exit 1
