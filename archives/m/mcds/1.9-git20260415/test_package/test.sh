#!/bin/sh
# test_package/test.sh — mcds 1.9-git20260415 消费者测试（R34：真跑被测二进制）
#
# 用法：sh test.sh <被测 mcds 绝对路径> <该包 package_folder 绝对路径>
#
# 全部用例离线：不访问任何 CardDAV 服务器。查询打到 127.0.0.1:1（必然
# ECONNREFUSED / URL 非法），用来证明 libcurl 确实被链入并执行到请求构造之后。
#
# 上游在本提交没有任何测试套件（清点证据见 MANIFEST.yml 与 reports/
# upstream-test-scan.txt），因此本脚本的断言计为「消费者测试」，
# 不计入上游测试分母。
set -u

MCDS="$1"
PKGFOLDER="$2"
PASS=0
FAIL=0
TOTAL=0
WORK="${TMPDIR:-/tmp}/mcds-test-package.$$"

ok() {
	TOTAL=$((TOTAL + 1))
	PASS=$((PASS + 1))
	printf 'PASS %s\n' "$1"
}

ko() {
	TOTAL=$((TOTAL + 1))
	FAIL=$((FAIL + 1))
	printf 'FAIL %s\n' "$1"
}

mkdir -p "$WORK" || { echo "cannot create $WORK"; exit 1; }
# 固定一个干净的 HOME：本目录里不放 .mcdsrc，避免宿主用户配置影响断言。
# mcds 在既没有 username 也没有 netrc 时会读 getenv("USER")，故给出非空值。
export HOME="$WORK"
export USER=mcdstest

# T1 被测二进制必须就是 conan 解析出来的**本包**产物（不是 PATH 上的同名件）
#    —— harmonybrew 里另有同名 mcds，绝对路径 + 前缀核对才是有效防呆。
case "$PKGFOLDER" in
	*harmonybrew*)
		ko "T1 package folder resolved to harmonybrew: $PKGFOLDER" ;;
	/*)
		if [ "$MCDS" = "$PKGFOLDER/bin/mcds" ]; then
			ok "T1 binary is the conan package artifact, not a PATH hit: $MCDS"
		else
			ko "T1 binary path does not match package folder: $MCDS vs $PKGFOLDER/bin/mcds"
		fi ;;
	*)
		ko "T1 package folder is not an absolute path: $PKGFOLDER" ;;
esac

# T1b 该路径存在且可执行
if [ -x "$MCDS" ]; then
	ok "T1b binary is executable"
else
	ko "T1b binary is not executable: $MCDS"
	echo "MCDS_TEST_SUMMARY total=$TOTAL passed=$PASS failed=$FAIL"
	rm -rf "$WORK"
	exit 1
fi

# T2 --version：输出上游版本行；上游 print_version() 以 exit(EXIT_FAILURE)
#    收尾，所以退出码必须是 1（不是 0）。
out=$("$MCDS" --version 2>&1)
rc=$?
if [ "$rc" -eq 1 ] && printf '%s\n' "$out" | grep -F "mcds (GNU mcds) 1.8" >/dev/null; then
	ok "T2 --version prints upstream version line (rc=1)"
else
	ko "T2 --version unexpected (rc=$rc): $out"
fi
printf '%s\n' "$out" | sed -n '1,12p'

# T2b --version 的编译期特性回显：确认两处功能裁剪真的编进了产物
if printf '%s\n' "$out" | grep -F "with-out GPGME support" >/dev/null \
   && printf '%s\n' "$out" | grep -F "with-out libsecret support" >/dev/null; then
	ok "T2b --version reports both feature cuts (no GPGME / no libsecret)"
else
	ko "T2b --version feature flags unexpected: $out"
fi

# T3 --help：usage 首行逐字对齐上游 usage 串。
#    %s 处填的是 program_name()，在 OHOS musl（无 getprogname、无
#    program_invocation_short_name）上靠补丁 0001 的 __progname 兜底才
#    打印出 "usage: mcds"，否则是 "usage: unknown"。
out=$("$MCDS" --help 2>&1)
rc=$?
if [ "$rc" -eq 1 ] \
   && printf '%s\n' "$out" | grep -F "usage: mcds [-c config] [-h] [-q a|e|n|t] [-s a|e|n|t] [-u URL] [-V] [-v] string" >/dev/null; then
	ok "T3 --help prints upstream usage with resolved program name (rc=1)"
else
	ko "T3 --help unexpected (rc=$rc): $out"
fi

# T4 缺查询串：走 parse_argv 的 usage 分支
out=$("$MCDS" 2>&1)
rc=$?
if [ "$rc" -eq 1 ] && printf '%s\n' "$out" | grep -F "usage: mcds" >/dev/null; then
	ok "T4 no-argument invocation exits 1 with usage"
else
	ko "T4 no-argument behaviour unexpected (rc=$rc): $out"
fi

# T5 查询字段构造：默认 -q 是 FN，加 -q a 必须变成 ADR（实测读数），
#    证明选项解析真的驱动了 carddav.c 的 prop-filter 选择。
def=$("$MCDS" -v fred 2>&1)
if printf '%s\n' "$def" | grep -F "Query             : FN" >/dev/null; then
	ok "T5a default query field is FN"
else
	ko "T5a default query field unexpected: $def"
fi
adr=$("$MCDS" -q a -v fred 2>&1)
if printf '%s\n' "$adr" | grep -F "Query             : ADR" >/dev/null; then
	ok "T5b -q a switches the query field to ADR"
else
	ko "T5b -q a did not change query field: $adr"
fi

# T6 端到端离线查询：证明 curl.c/carddav.c 主链路真的执行到 libcurl，
#    并在失败时给出可诊断错误；同时断言生成的 REPORT 请求体是 carddav 命名空间。
out=$("$MCDS" -v -u http://127.0.0.1:1/ fred 2>&1)
rc=$?
if [ "$rc" -ne 0 ] \
   && printf '%s\n' "$out" | grep -F "Sending" >/dev/null \
   && printf '%s\n' "$out" | grep -F "Unable to search for fred" >/dev/null \
   && printf '%s\n' "$out" | grep -F "urn:ietf:params:xml:ns:carddav" >/dev/null; then
	ok "T6 offline CardDAV REPORT reaches libcurl and fails diagnosably (rc=$rc)"
else
	ko "T6 offline query unexpected (rc=$rc): $out"
fi
printf '%s\n' "$out" | sed -n '1,20p'

rm -rf "$WORK"

echo "MCDS_TEST_SUMMARY total=$TOTAL passed=$PASS failed=$FAIL"
if [ "$FAIL" -ne 0 ]; then
	exit 1
fi
exit 0
