#!/bin/sh
# test_package 判定脚本 — yp-tools 4.2.3
#
# 用法: sh test_yp_tools.sh <package_folder>
#
# 用例分三组：
#   A. 上游工具样例（9 个工具的 --version / --usage / 功能性调用，以及 4 个别名）
#   B. 上游内建测试工具 yptest 的 9 个用例名（Test 1..Test 9）
#   C. 鸿蒙（OHOS/musl/HMDFS）特有约束（≥1，本脚本共 6 条）
# 逐条输出 PASS/FAIL/SKIP，任一 FAIL 则以非零码退出。
set -u

PKG=${1:?usage: test_yp_tools.sh <package_folder>}
BIN="$PKG/bin"
SBIN="$PKG/sbin"

# 工具发现（readelf/nm 位于 SDK bin 目录；测试环境 PATH 可能不含）
for d in /data/service/hnp/bin /usr/bin /bin; do
  [ -d "$d" ] && PATH="$d:$PATH"
done
export PATH
READELF=$(command -v readelf 2>/dev/null || true)
NM=$(command -v nm 2>/dev/null || true)

PASS=0
FAIL=0
SKIP=0
pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; }
skip() { SKIP=$((SKIP + 1)); echo "SKIP: $1"; }

# 在 bin/ 或 sbin/ 中定位工具
tool_path() {
  for d in "$BIN" "$SBIN"; do
    [ -x "$d/$1" ] && { echo "$d/$1"; return 0; }
  done
  echo ""
}

TOOLS="ypwhich ypmatch ypcat yppasswd domainname yppoll ypset yp_dump_binding yptest"

echo "== A. upstream tool samples (--version / --usage / functional) =="
for t in $TOOLS; do
  p=$(tool_path "$t")
  if [ -z "$p" ]; then
    fail "A-sample-$t-present"
    continue
  fi
  out=$("$p" --version 2>&1)
  rc=$?
  if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "4\.2\.3"; then
    pass "A-sample-$t-version"
  else
    fail "A-sample-$t-version (rc=$rc)"
  fi
done

for t in $TOOLS; do
  p=$(tool_path "$t")
  [ -z "$p" ] && { fail "A-sample-$t-usage"; continue; }
  out=$("$p" --usage 2>&1)
  rc=$?
  if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qi "usage"; then
    pass "A-sample-$t-usage"
  else
    fail "A-sample-$t-usage (rc=$rc)"
  fi
done

# 功能性调用：无 NIS 服务器环境下必须"优雅报错"，而不是崩溃/静默成功
run_expect() {           # <case> <expected-rc> <grep-pattern> <cmd...>
  case_name=$1; want_rc=$2; pattern=$3; shift 3
  out=$("$@" 2>&1)
  rc=$?
  if [ "$rc" -ne "$want_rc" ]; then
    fail "$case_name (rc=$rc, want=$want_rc)"
    return
  fi
  if printf '%s' "$out" | grep -qiE "$pattern"; then
    pass "$case_name"
  else
    fail "$case_name (missing pattern: $pattern)"
  fi
}

run_expect "A-func-domainname" 0 "^[A-Za-z0-9._-]+$|unknown" "$(tool_path domainname)"
run_expect "A-func-ypwhich-no-ypbind" 1 "ypbind" "$(tool_path ypwhich)"
run_expect "A-func-ypcat-no-server" 1 "map|NIS|bind" "$(tool_path ypcat)" -k passwd
run_expect "A-func-ypmatch-no-server" 1 "match|NIS|bind" "$(tool_path ypmatch)" user passwd
run_expect "A-func-yppoll-no-server" 1 "contact|server" "$(tool_path yppoll)" -h 127.0.0.1 -d localdomain passwd.byname
run_expect "A-func-ypset-no-server" 1 "ypserv" "$(tool_path ypset)" -d localdomain 127.0.0.1
run_expect "A-func-yp_dump_binding" 0 "binding" "$(tool_path yp_dump_binding)"

# 别名（bin/ 中的软链）
for a in ypchsh ypchfn ypdomainname nisdomainname; do
  p="$BIN/$a"
  if [ ! -x "$p" ]; then
    fail "A-alias-$a-present"
    continue
  fi
  out=$("$p" --version 2>&1)
  rc=$?
  if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "4\.2\.3"; then
    pass "A-alias-$a-version"
  else
    fail "A-alias-$a-version (rc=$rc)"
  fi
done

echo "== B. upstream built-in test tool: yptest case battery =="
YPTEST=$(tool_path yptest)
if [ -z "$YPTEST" ]; then
  fail "B-yptest-present"
else
  ypout=$("$YPTEST" 2>&1)
  yprc=$?
  for c in "1:domainname" "2:ypbind" "3:yp_match" "4:yp_first" \
           "5:yp_next" "6:yp_master" "7:yp_order" "8:yp_maplist" "9:yp_all"; do
    n=${c%%:*}
    name=${c#*:}
    if printf '%s' "$ypout" | grep -q "^Test $n: $name"; then
      # 无 NIS 服务器时这些用例会报错，但必须"被执行到"（yptest rc!=0 属预期）
      pass "B-yptest-case$n-$name"
    else
      fail "B-yptest-case$n-$name (not executed)"
    fi
  done
  echo "     yptest exit status: $yprc (无 NIS 服务器环境下非 0 属预期)"
fi

echo "== C. OHOS (musl libc / HMDFS) specific checks =="
ALLBIN=""
for t in $TOOLS ypchsh ypchfn ypdomainname nisdomainname; do
  p=$(tool_path "$t")
  [ -n "$p" ] && ALLBIN="$ALLBIN $p"
done

# C1: 所有产物必须是 aarch64（OHOS PC）ELF
if [ -z "$READELF" ]; then
  skip "C1-ohos-elf-aarch64 (readelf 不可用)"
else
  bad=""
  for p in $ALLBIN; do
    "$READELF" -h "$p" 2>/dev/null | grep -q "AArch64" || bad="$bad $(basename "$p")"
  done
  if [ -z "$bad" ]; then
    pass "C1-ohos-elf-aarch64"
  else
    fail "C1-ohos-elf-aarch64 (not aarch64:$bad)"
  fi
fi

# C2: 自包含 —— OHOS 无 libnsl/libtirpc/libintl/libcrypt，四者均已静态进包，
#     运行时动态依赖只能有 musl 的 libc.so
if [ -z "$READELF" ]; then
  skip "C2-ohos-static-thirdparty (readelf 不可用)"
else
  bad=""
  for p in $ALLBIN; do
    needed=$("$READELF" -d "$p" 2>/dev/null | awk '/NEEDED/{print $NF}' | tr -d '[]')
    for lib in $needed; do
      case "$lib" in
        libc.so) ;;
        *) bad="$bad $(basename "$p"):$lib" ;;
      esac
    done
  done
  if [ -z "$bad" ]; then
    pass "C2-ohos-static-thirdparty (only libc.so NEEDED)"
  else
    fail "C2-ohos-static-thirdparty (unexpected runtime deps:$bad)"
  fi
fi

# C3: getpass() 回退实现被编入 yppasswd —— OHOS musl 的共享 libc.so 既无声明也无该符号
if [ -z "$NM" ]; then
  skip "C3-ohos-getpass-fallback (nm 不可用)"
else
  p=$(tool_path yppasswd)
  if [ -n "$p" ] && "$NM" --defined-only "$p" 2>/dev/null | grep -qE "[0-9a-f]+ [TWi] getpass$"; then
    pass "C3-ohos-getpass-fallback"
  else
    fail "C3-ohos-getpass-fallback (getpass not defined in yppasswd)"
  fi
fi

# C4: gettext/libintl 静态链接生效 —— OHOS sysroot 的 libintl.h 是无原型桩且无 libintl 库
if [ -z "$NM" ]; then
  skip "C4-ohos-gettext-static-link (nm 不可用)"
else
  p=$(tool_path ypwhich)
  if [ -n "$p" ] && "$NM" "$p" 2>/dev/null | grep -q "libintl_gettext"; then
    pass "C4-ohos-gettext-static-link"
  else
    fail "C4-ohos-gettext-static-link (libintl_gettext missing)"
  fi
fi

# C5: NLS 目录数据随包安装（de/sv 翻译）
if [ -f "$PKG/share/locale/de/LC_MESSAGES/yp-tools.mo" ] && \
   [ -f "$PKG/share/locale/sv/LC_MESSAGES/yp-tools.mo" ]; then
  pass "C5-ohos-nls-catalogs"
else
  fail "C5-ohos-nls-catalogs (yp-tools.mo missing)"
fi

# C6: 安装别名必须是符号链接（HMDFS 不支持硬链接，link(2) 返回 EPERM）
bad=""
for a in ypchsh ypchfn ypdomainname nisdomainname; do
  [ -L "$BIN/$a" ] || bad="$bad $a"
done
if [ -z "$bad" ]; then
  pass "C6-ohos-hmdfs-symlink-aliases"
else
  fail "C6-ohos-hmdfs-symlink-aliases (not symlinks:$bad)"
fi

echo
echo "== SUMMARY: PASS=$PASS FAIL=$FAIL SKIP=$SKIP (total=$((PASS + FAIL + SKIP))) =="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
