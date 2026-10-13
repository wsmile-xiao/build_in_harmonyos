#!/bin/sh
# syslog-ng 4.8.1 消费者测试 — 设备上跑在 conanrun 环境里
# （PATH / LD_LIBRARY_PATH / SYSLOGNG_PREFIX 由配方 package_info 导出）。
# 用法: sh test.sh <workdir>

set -u

WORK="${1:-}"
[ -n "$WORK" ] || WORK="$(pwd)"
WORK="$(cd "$WORK" 2>/dev/null && pwd)" || WORK="$(pwd)"

TMPD="$WORK/syslog-ng-ct-$$"
EXTRA_CTL_DIR=""
rm -rf "$TMPD"
mkdir -p "$TMPD" || { echo "cannot create work dir $TMPD"; exit 1; }
trap 'rm -rf "$TMPD"; if [ -n "$EXTRA_CTL_DIR" ]; then rm -rf "$EXTRA_CTL_DIR"; fi; :' EXIT INT TERM

ASSERT=0
PASS=0
FAIL=0

ok()  { ASSERT=$((ASSERT+1)); PASS=$((PASS+1)); echo "PASS[$ASSERT] $1"; }
bad() { ASSERT=$((ASSERT+1)); FAIL=$((FAIL+1)); echo "FAIL[$ASSERT] $1"; }

# 进程存活判定：/proc 存在且状态非 Z（kill -0 对僵尸也返回真，会把等待
# 循环拖满；/proc 不可读时退回 kill -0）。
alive() {
    _pid="$1"
    if [ -r "/proc/$_pid/stat" ]; then
        _st="$(cut -d' ' -f3 < "/proc/$_pid/stat" 2>/dev/null)"
        [ "$_st" != "Z" ]
    else
        kill -0 "$_pid" 2>/dev/null
    fi
}

# ---- 前置：runenv 导出与二进制位置 ------------------------------------------
PREFIX="${SYSLOGNG_PREFIX:-}"
if [ -n "$PREFIX" ] && [ -d "$PREFIX" ]; then
    ok "SYSLOGNG_PREFIX exported by runenv: $PREFIX"
else
    bad "SYSLOGNG_PREFIX not set or not a directory"
fi

SYSLOGNG=""
SYSLOGNG_CTL=""
for d in "$PREFIX/bin" "$PREFIX/sbin"; do
    [ -x "$d/syslog-ng" ] && SYSLOGNG="$d/syslog-ng"
    [ -x "$d/syslog-ng-ctl" ] && SYSLOGNG_CTL="$d/syslog-ng-ctl"
done
if [ -n "$SYSLOGNG" ] && [ -n "$SYSLOGNG_CTL" ]; then
    ok "binaries installed: $SYSLOGNG / $SYSLOGNG_CTL"
else
    bad "syslog-ng / syslog-ng-ctl not found under prefix bin,sbin"
fi

# ---- 用例 1：版本横幅 + 模块目录重定位 --------------------------------------
VER_OUT="$TMPD/version.out"
if "$SYSLOGNG" --version > "$VER_OUT" 2>&1; then
    ok "--version exits 0"
else
    bad "--version exit code nonzero"
    cat "$VER_OUT"
fi

FIRST_LINE="$(head -n 1 "$VER_OUT" 2>/dev/null)"
case "$FIRST_LINE" in
    syslog-ng" "*4.8.1*) ok "banner: $FIRST_LINE" ;;
    *) bad "banner first line unexpected: $FIRST_LINE" ;;
esac

MODLINE="$(grep '^Module-Directory:' "$VER_OUT" 2>/dev/null | head -n 1 | sed 's/^Module-Directory:[ ]*//')"
case "$MODLINE" in
    "$PREFIX"/lib/syslog-ng*) ok "Module-Directory relocated under prefix: $MODLINE" ;;
    *) bad "Module-Directory not relocated: '$MODLINE'" ;;
esac

if grep '^Available-Modules:' "$VER_OUT" 2>/dev/null | grep -q 'affile'; then
    ok "affile listed in Available-Modules"
else
    bad "affile missing from Available-Modules"
fi

# ---- 用例 2：模块注册表（对每个模块 .so 全量 dlopen）------------------------
REG_OUT="$TMPD/registry.out"
if "$SYSLOGNG" --module-registry > "$REG_OUT" 2>&1; then
    ok "--module-registry exits 0"
else
    bad "--module-registry exit code nonzero"
fi

MODCOUNT="$(grep -c '^Module: ' "$REG_OUT" 2>/dev/null)"
[ -n "$MODCOUNT" ] || MODCOUNT=0
if [ "$MODCOUNT" -ge 25 ]; then
    ok "module registry loaded $MODCOUNT modules"
else
    bad "module registry only lists $MODCOUNT modules (<25)"
fi

if grep -q 'Status: Unable' "$REG_OUT" 2>/dev/null; then
    bad "module registry reports load failures"
    grep 'Status: Unable' "$REG_OUT" | head -n 10
else
    ok "all registered modules dlopen/init cleanly"
fi

# ---- 用例 3：配置解析 + 完整启动检查 ----------------------------------------
CFG_VER="$(grep '^Config version:' "$VER_OUT" 2>/dev/null | head -n 1 | sed 's/^Config version:[ ]*//')"
[ -n "$CFG_VER" ] || CFG_VER="4.8"

CONF="$TMPD/test.conf"
OUTLOG="$TMPD/out.log"
cat > "$CONF" <<EOF
@version: $CFG_VER
options {
    flush-lines(1);
};
source s_int {
    internal();
};
destination d_out {
    file("$OUTLOG");
};
log {
    source(s_int);
    destination(d_out);
};
EOF

if "$SYSLOGNG" -s -f "$CONF" > "$TMPD/syntax.out" 2>&1; then
    ok "config parses (--syntax-only rc=0)"
else
    bad "--syntax-only rejected the config"
    cat "$TMPD/syntax.out"
fi

if "$SYSLOGNG" --check-startup --no-caps -f "$CONF" -R "$TMPD/check.persist" -c "$TMPD/check.ctl" > "$TMPD/check-startup.out" 2>&1; then
    ok "full startup check rc=0 (--check-startup)"
else
    bad "--check-startup exit code nonzero"
    cat "$TMPD/check-startup.out"
fi

# ---- 用例 4：端到端守护进程（internal() → file() 路由 + control socket）----
# 控制套接字目录：套接字文件创建要求所在卷允许 AF_UNIX 节点。OHOS 的 HMDFS
# 用户卷（$WORK 所在）拒绝创建（bind: EPERM，实测），app 沙箱卷
# /data/storage/el2/base 允许；普通平台通常 $TMPD 即可。按候选顺序实测，
# 以守护进程真正建出套接字为准；可用 SYSLOGNG_CTL_DIR 显式指定。
rm -f "$OUTLOG"
CTL_SOCK=""
E2E_PID=""
FOUND=0
for CAND in "${SYSLOGNG_CTL_DIR:-}" "$TMPD" "/data/storage/el2/base/tmp/syslog-ng-ct-$$"; do
    [ -n "$CAND" ] || continue
    mkdir -p "$CAND" 2>/dev/null
    if [ ! -d "$CAND" ] || [ ! -w "$CAND" ]; then
        continue
    fi
    rm -f "$CAND/e2e.ctl" "$OUTLOG"
    "$SYSLOGNG" -F --no-caps -f "$CONF" -p "$TMPD/e2e.pid" -R "$TMPD/e2e.persist" -c "$CAND/e2e.ctl" > "$TMPD/e2e.stdout" 2>&1 &
    E2E_PID=$!

    FOUND=0
    n=0
    while [ "$n" -lt 30 ]; do
        if [ -f "$OUTLOG" ] && grep -q 'syslog-ng starting up' "$OUTLOG" 2>/dev/null; then
            FOUND=1
            break
        fi
        if ! alive "$E2E_PID"; then
            break
        fi
        sleep 1
        n=$((n+1))
    done
    # 启动行出现后再给套接字最多 4 秒出现窗口（创建发生在守护进程初始化期）
    m=0
    while [ "$FOUND" -eq 1 ] && [ "$m" -lt 4 ] && [ ! -S "$CAND/e2e.ctl" ]; do
        sleep 1
        m=$((m+1))
    done

    if [ "$FOUND" -eq 1 ] && [ -S "$CAND/e2e.ctl" ]; then
        CTL_SOCK="$CAND/e2e.ctl"
        [ "$CAND" = "$TMPD" ] || EXTRA_CTL_DIR="$CAND"
        break
    fi
    # 该目录无法承载套接字（或守护进程异常退出）→ 杀掉换下一候选目录重试
    kill -TERM "$E2E_PID" 2>/dev/null
    wait "$E2E_PID" 2>/dev/null
    E2E_PID=""
    [ "$CAND" = "$TMPD" ] || rm -rf "$CAND"
done

if [ "$FOUND" -eq 1 ] && [ -n "$CTL_SOCK" ]; then
    ok "daemon routed 'syslog-ng starting up' into file() destination (ctl socket: $CTL_SOCK)"
else
    bad "no startup message in destination file within 30s, or no AF_UNIX-capable ctl dir"
    echo "--- destination file ---"
    cat "$OUTLOG" 2>/dev/null
    echo "--- daemon stdout/stderr ---"
    cat "$TMPD/e2e.stdout" 2>/dev/null
fi

if [ -n "$CTL_SOCK" ] && alive "$E2E_PID"; then
    # 4.8.1 语法：命令必须在选项前（get_mode 取首个非 '-' 参数为命令名，
    # `-c <path> stats` 会把 socket 路径当命令 → "Unknown command"）。
    STATS="$("$SYSLOGNG_CTL" stats -c "$CTL_SOCK" 2>&1)"
    CTL_RC=$?
    if [ "$CTL_RC" -eq 0 ] && printf '%s\n' "$STATS" | grep -q 'd_out'; then
        ok "syslog-ng-ctl stats rc=0, d_out statistics present"
    else
        bad "syslog-ng-ctl stats failed (rc=$CTL_RC) or no d_out entry"
        printf '%s\n' "$STATS" | head -n 20
    fi
elif [ -n "$CTL_SOCK" ]; then
    bad "daemon exited before control-channel stats check"
else
    bad "no control socket created on any candidate ctl directory"
fi

# SIGTERM 优雅停机（看门狗兜底 SIGKILL；wait 阻塞到真退出）
if [ -n "$E2E_PID" ]; then
    ( sleep 20; kill -9 "$E2E_PID" 2>/dev/null ) &
    WATCHDOG=$!
    kill -TERM "$E2E_PID" 2>/dev/null
    wait "$E2E_PID"
    TERM_RC=$?
    kill "$WATCHDOG" 2>/dev/null
    wait "$WATCHDOG" 2>/dev/null
    if [ "$TERM_RC" -eq 0 ]; then
        ok "SIGTERM shutdown: daemon exited rc=0"
    else
        bad "SIGTERM shutdown: rc=$TERM_RC (137 = watchdog SIGKILL timeout)"
        tail -n 20 "$TMPD/e2e.stdout" 2>/dev/null
    fi
else
    bad "no daemon running for SIGTERM shutdown check"
fi

# ---- 汇总 -------------------------------------------------------------------
echo ""
echo "==== SYSLOG-NG CONSUMER TEST SUMMARY ===="
echo "cases: version-banner, module-registry, config-checks, end-to-end"
echo "assertions: $ASSERT  passed: $PASS  failed: $FAIL"
if [ "$FAIL" -eq 0 ]; then
    echo "RESULT: ALL_PASS"
    exit 0
else
    echo "RESULT: SOME_FAILED"
    exit 1
fi
