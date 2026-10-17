#!/bin/sh
# mmh 0.4 上游测试套件 — OHOS 真机等效驱动
#
# 等效复刻 test/runalltests + test/runtest，差异全部显式（逐条见
# reports/upstream-test-run.md 与 summary 输出）：
#   D1 runtest 以 `sh ./runtest` 启动（OHOS 拒绝 shebang 脚本 execve）；
#   D2 runtest 内硬编码 /bin/sh：设备无可用 /bin/sh 时以 bash 执行
#      （REPLICA 模式内联复刻 runtest 主流程，唯一语义差异）；
#   D3 预置 test-temp-dir + $TEMPDIR/build/Makefile 跳过 setup-test
#      （其 configure 走 execve 在 OHOS 必失败）；
#   D4 make install 以 LN=cp 替代硬链接（HMDFS link(2) EPERM）；
#   D5 6 个脚本命令 bin/<c> 换 C launcher 垫片、原脚本存 <c>.real；
#   D6 configure 追加 --with-locking=fcntl（缺省 dot-lock 靠 link(2) 建
#      锁，HMDFS 上 EPERM；表观错误为 context 写入 ENOENT 假象——lockit
#      重试循环最终 errno 停在 stat 的 ENOENT——57 例全部 rc=74。F_SETLK
#      内核锁真机可用，与归档配方 --with-locking=fcntl 一致）。
#   D7 设备无 ed（toybox/HNP 均无）；tests/show/test-longlines 的退出 trap
#      用 ed 删 profile 一行做清理，trap 失败毒化用例退出码。套件以
#      mmh-fix/edshim.c 编译最小 ed（/RE/d、w、q 子集）放入临时 bin。
#
# 用法（设备）：sh $HOME/mmh-fix/run-mmh-suite.sh
. "$HOME/mmh-fix/env.sh"
FIX="$HOME/mmh-fix"
LOGD="$FIX/logs/suite"
SRCD="$FIX/src/mmh-0.4"
TEMPD="$FIX/suite-temp"
mkdir -p "$LOGD"
rm -rf "$FIX/src" "$TEMPD"
mkdir -p "$FIX/src"
tar -xzf "$FIX/mmh-0.4-patched.tar.gz" -C "$FIX/src" || exit 1
echo "SRC=$SRCD"

NCDIR=$(ls -d "$CONAN_HOME"/p/ncurs*/p 2>/dev/null | head -n 1)
if [ -z "$NCDIR" ]; then
	echo "ncurses package dir not found under $CONAN_HOME/p"
	exit 1
fi
echo "NCDIR=$NCDIR"

mkdir -p "$TEMPD/build"
cd "$TEMPD/build" || exit 1
sh "$SRCD/configure" -q --prefix="$TEMPD" --enable-debug --with-locking=fcntl \
	CC=/data/service/hnp/bin/clang \
	CPPFLAGS="-I$NCDIR/include" LDFLAGS="-L$NCDIR/lib" \
	CFLAGS="-O2 -fcommon" \
	> "$LOGD/configure.log" 2>&1
rc=$?
echo "CONFIGURE_RC=$rc"
if [ $rc -ne 0 ]; then
	tail -n 25 "$LOGD/configure.log"
	exit 1
fi

make -s all install LN=cp > "$LOGD/make.log" 2>&1
rc=$?
echo "MAKE_RC=$rc"
if [ $rc -ne 0 ]; then
	tail -n 30 "$LOGD/make.log"
	exit 1
fi
echo "BIN: $(ls "$TEMPD/bin" | wc -l) 个文件（含链接与垫片）"

# D5 垫片
/data/service/hnp/bin/clang -O2 -o "$TEMPD/bin/.mmhshim" "$FIX/mmhshim.c" > "$LOGD/shim.log" 2>&1
if [ $? -ne 0 ]; then
	echo "SHIM_BUILD_FAIL"
	cat "$LOGD/shim.log"
	exit 1
fi
for c in mmh mhsign mhpgp print-mimetype sendfiles whatnow2; do
	if [ -f "$TEMPD/bin/$c" ] && [ ! -f "$TEMPD/bin/$c.real" ]; then
		mv "$TEMPD/bin/$c" "$TEMPD/bin/$c.real"
		cp "$TEMPD/bin/.mmhshim" "$TEMPD/bin/$c"
	fi
done
rm -f "$TEMPD/bin/.mmhshim"
ls -l "$TEMPD/bin/mhsign" "$TEMPD/bin/mhsign.real" 2>&1

# D7 ed 垫片
/data/service/hnp/bin/clang -O2 -o "$TEMPD/bin/ed" "$FIX/edshim.c" >> "$LOGD/shim.log" 2>&1
if [ $? -ne 0 ]; then
	echo "ED_SHIM_BUILD_FAIL"
	cat "$LOGD/shim.log"
	exit 1
fi
ls -l "$TEMPD/bin/ed"

# D3 预置（跳过 setup-test）
echo "$TEMPD" > "$SRCD/test/test-temp-dir"

cd "$SRCD/test" || exit 1
MODE="runtest"
if ! { [ -x /bin/sh ] && /bin/sh -c 'exit 0' 2>/dev/null; }; then
	MODE="replica"
fi
echo "MODE=$MODE"

TOUT=""
if command -v timeout >/dev/null 2>&1; then
	TOUT="timeout 600"
fi

total=0; pass=0; fail=0; skip=0
: > "$LOGD/summary.txt"
echo "--- per-test results (stdout of runtest) ---"
for t in $(find tests -name 'test-*' ! -name '*~' -type f | LC_ALL=C sort); do
	total=$((total + 1))
	logf="$LOGD/$(echo "$t" | tr '/' '_').log"
	if [ "$MODE" = "runtest" ]; then
		$TOUT sh ./runtest "$t" > "$logf" 2>&1
		rc=$?
	else
		# REPLICA：内联复刻 runtest 主流程（/bin/sh -> bash）
		export MH_TEST_COMMON="$PWD/common.sh"
		export MH_TEST_DIR=$(cat test-temp-dir)
		unset MMHP MMHC
		export PATH="$MH_TEST_DIR/bin:$PATH"
		export MMH="$MH_TEST_DIR/.mmh"
		MAILDIR="$MH_TEST_DIR/Mail"
		rm -rf "$MAILDIR" "$MMH"
		mkdir "$MAILDIR" "$MMH"
		{
			echo "Path: $MAILDIR"
			echo "Inbox: +inbox"
		} > "$MMH/profile"
		folder -create $(mhparam inbox) >/dev/null
		folder -create $(mhparam trashfolder) >/dev/null
		folder -create $(mhparam draftfolder) >/dev/null
		for i in 1 2 3 4 5 6 7 8 9 10; do
			{
				echo "From: Test$i <test$i@example.com>"
				echo "To: Some User <user@example.com>"
				echo "Date: Fri, 29 Sep 2006 00:00:00"
				echo "Subject: Testing message $i"
				echo ""
				echo "This is message number $i"
			} > "$MAILDIR/inbox/$i"
		done
		folder +inbox >/dev/null
		export SHELL="${SHELL:-$HNP/bash}"
		$TOUT bash "$t" > "$logf" 2>&1
		rc=$?
	fi
	case $rc in
	0) pass=$((pass + 1)); echo "PASS $t" ;;
	2) skip=$((skip + 1)); echo "SKIP $t" ;;
	*) fail=$((fail + 1)); echo "FAIL($rc) $t" ;;
	esac
	echo "$t rc=$rc" >> "$LOGD/summary.txt"
done

echo
echo "=== FINAL: TOTAL=$total PASS=$pass SKIP=$skip FAIL=$fail MODE=$MODE ==="
grep -v '^PASS ' "$LOGD/summary.txt" || true
sh ./teardown-test >/dev/null 2>&1
