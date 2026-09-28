#!/bin/sh
# test_libcob.sh — TAP driver for the packaged libcob4 (libcob.so.4).
#
# usage: sh test_libcob.sh <path-to-test_libcob-binary> <package-folder>
#
# 只依赖 POSIX sh 内建 + toybox/busybox 一定有的 mkdir/chmod/grep/head/cat([)。
# 不使用 tr / strings / nm / readelf / grep -a —— 这些在 OHOS 侧不保证存在
# （见 knowledge 中 ondir 9492 的教训）。所有断言都是**可观测的运行时行为**或
# **文件存在性**，不做二进制内容匹配。
#
# TMPDIR 相关断言为什么必须换进程：libcob 的临时目录解析结果
# （libcob/common.c: cob_gettmpdir() 内的 static tmpdir）是**进程内静态缓存**，
# 一个进程里只有第一次调用会真正读环境变量。

set -u

BIN=${1:-}
PKG=${2:-}
if [ -z "$BIN" ] || [ ! -x "$BIN" ]; then
    echo "usage: sh $0 <test_libcob-binary> <package-folder>" >&2
    exit 2
fi

if command -v timeout >/dev/null 2>&1; then
    RUN="timeout 120"
else
    RUN=""
fi

WORK=$(pwd)/libcob4-tap-$$
mkdir -p "$WORK" || exit 2
trap 'rm -rf "$WORK"' EXIT

OK=0
FAIL=0
TOTAL=0

check() {
    TOTAL=$((TOTAL + 1))
    if [ "$1" = "1" ]; then
        OK=$((OK + 1))
        echo "ok $TOTAL - $2"
    else
        FAIL=$((FAIL + 1))
        echo "not ok $TOTAL - $2"
    fi
}

# 解析 <mode> 运行的 stdout 里 `KEY=value` 形式的单行输出
field() {
    _line=$(grep "^$2=" "$1" 2>/dev/null | head -n 1)
    echo "${_line#*=}"
}

# ── 1/2：api 模式（运行时初始化状态机 + 内存 API + 字段边界 + getpid 绑定）──
$RUN "$BIN" api >"$WORK/api.out" 2>"$WORK/api.err"
RC=$?
check "$([ "$RC" = "0" ] && echo 1 || echo 0)" \
      "test_libcob api exits 0 (cob_init/tidy + cob_malloc/free + cob_get_field_str bounds + cob_sys_getpid)"

if grep -qE "Error loading shared library|error while loading shared libraries|cannot open shared object|Error relocating|undefined symbol|symbol not found" "$WORK/api.err"; then
    check 0 "api mode ran without dynamic loader errors"
else
    check 1 "api mode ran without dynamic loader errors"
fi

# ── 3/4/5：可用 TMPDIR → 必须被采用，并回写环境 ──────────────────────────
mkdir -p "$WORK/tmp-ok"
TMPDIR="$WORK/tmp-ok" $RUN "$BIN" tmpdir >"$WORK/ok.out" 2>"$WORK/ok.err"
NAME_OK=$(field "$WORK/ok.out" TEMPNAME)
TMPENV_OK=$(field "$WORK/ok.out" TMPDIR_ENV)

case "$NAME_OK" in
    "$WORK/tmp-ok"/cob*) check 1 "cob_temp_name() uses a writable TMPDIR (resolved: ${NAME_OK})" ;;
    *)                   check 0 "cob_temp_name() uses a writable TMPDIR (got: '${NAME_OK}')" ;;
esac

case "$NAME_OK" in
    /*) check 1 "cob_temp_name() returns an absolute path" ;;
    *)  check 0 "cob_temp_name() returns an absolute path (got: '${NAME_OK}')" ;;
esac

if [ "$TMPENV_OK" = "$WORK/tmp-ok" ]; then
    check 1 "libcob re-exports the resolved directory through TMPDIR (=${TMPENV_OK})"
else
    check 0 "libcob re-exports the resolved directory through TMPDIR (got: '${TMPENV_OK}')"
fi

# ── 6：TMPDIR 指向不存在的目录 → 静默退化，且绝不在该路径下造临时名 ────────
#    HarmonyOS 侧 TMPDIR 可能指向一个不存在/已卸载的路径，libcob 必须
#    拒绝它并退化到其它可用目录（common.c: check_valid_env_tmpdir → 回退链）。
TMPDIR="$WORK/does-not-exist" $RUN "$BIN" tmpdir >"$WORK/miss.out" 2>"$WORK/miss.err"
RC_MISS=$?
NAME_MISS=$(field "$WORK/miss.out" TEMPNAME)

if [ "$RC_MISS" != "0" ]; then
    check 0 "non-existent TMPDIR degrades gracefully (exit code $RC_MISS)"
elif [ -z "$NAME_MISS" ]; then
    check 0 "non-existent TMPDIR degrades gracefully (no temporary name produced)"
else
    case "$NAME_MISS" in
        "$WORK/does-not-exist"/*) check 0 "non-existent TMPDIR is not used (got: ${NAME_MISS})" ;;
        *)                        check 1 "non-existent TMPDIR degrades to a usable directory (resolved: ${NAME_MISS})" ;;
    esac
fi

# ── 7：TMPDIR 指向一个普通文件 → 同样必须被拒绝（stat 成功但不是目录）──────
: > "$WORK/regular-file"
TMPDIR="$WORK/regular-file" $RUN "$BIN" tmpdir >"$WORK/file.out" 2>"$WORK/file.err"
RC_FILE=$?
NAME_FILE=$(field "$WORK/file.out" TEMPNAME)

if [ "$RC_FILE" != "0" ]; then
    check 0 "a regular file used as TMPDIR is rejected (exit code $RC_FILE)"
elif [ -z "$NAME_FILE" ]; then
    check 0 "a regular file used as TMPDIR is rejected (no temporary name produced)"
else
    case "$NAME_FILE" in
        "$WORK/regular-file"/*) check 0 "a regular file is never used as a temporary directory (got: ${NAME_FILE})" ;;
        *)                      check 1 "TMPDIR pointing at a regular file is rejected (resolved: ${NAME_FILE})" ;;
    esac
fi

# ── 8：不可写 TMPDIR → patch 0005 的 access(W_OK) 检查必须拒绝它 ──────────
#    HarmonyOS/HMFS 上临时目录可能是只读挂载；上游原版只做 stat+S_ISDIR，
#    会选中一个只读目录，导致后续临时文件创建失败。0005 补丁补上可写性检查。
mkdir -p "$WORK/tmp-ro"
chmod 500 "$WORK/tmp-ro"
if [ -w "$WORK/tmp-ro" ]; then
    # 以 root 运行时 chmod 无法造成不可写，这一格无法构造，如实记为跳过
    check 1 "unwritable TMPDIR is never chosen (skip: running with privileges that ignore mode bits)"
else
    TMPDIR="$WORK/tmp-ro" $RUN "$BIN" tmpdir >"$WORK/ro.out" 2>"$WORK/ro.err"
    RC_RO=$?
    NAME_RO=$(field "$WORK/ro.out" TEMPNAME)
    if [ "$RC_RO" != "0" ]; then
        check 0 "unwritable TMPDIR is rejected (exit code $RC_RO)"
    elif [ -z "$NAME_RO" ]; then
        check 1 "unwritable TMPDIR is rejected (no temporary name produced)"
    else
        case "$NAME_RO" in
            "$WORK/tmp-ro"/*) check 0 "unwritable TMPDIR is not used (got: ${NAME_RO})" ;;
            *)                check 1 "unwritable TMPDIR falls back to a usable directory (resolved: ${NAME_RO})" ;;
        esac
    fi
fi
chmod 700 "$WORK/tmp-ro" 2>/dev/null || true

# ── 9/10/11/12/13：包布局（ABI 4 的文件名 / 链接名 / 公共头 / 纯库包）──────
if [ -n "$PKG" ] && [ -d "$PKG" ]; then
    [ -e "$PKG/lib/libcob.so.4" ]      && check 1 "lib/libcob.so.4 present (runtime SONAME, ABI 4)" \
                                        || check 0 "lib/libcob.so.4 present (runtime SONAME, ABI 4)"
    [ -e "$PKG/lib/libcob.so.4.2.0" ]  && check 1 "lib/libcob.so.4.2.0 present (libtool ABI file name)" \
                                        || check 0 "lib/libcob.so.4.2.0 present (libtool ABI file name)"
    [ -e "$PKG/lib/libcob.so" ]        && check 1 "lib/libcob.so present (link-time name for -lcob)" \
                                        || check 0 "lib/libcob.so present (link-time name for -lcob)"
    if [ -f "$PKG/include/libcob.h" ] && [ -f "$PKG/include/libcob/common.h" ]; then
        check 1 "include/libcob.h and include/libcob/common.h present"
    else
        check 0 "include/libcob.h and include/libcob/common.h present"
    fi
    if [ -e "$PKG/bin" ]; then
        check 0 "package ships no compiler/executables (library-only package) (got: bin/ present)"
    else
        check 1 "package ships no compiler/executables (library-only package)"
    fi
else
    check 0 "package folder argument is a directory (got: '$PKG')"
fi

echo "1..$TOTAL"
echo "# libcob4 assertions: pass=$OK fail=$FAIL total=$TOTAL"
[ "$FAIL" = "0" ] || exit 1
exit 0
