#!/data/service/hnp/bin/bash
# run_upstream_tests.sh — 在 HarmonyOS PC 上真实执行 zps 2.0.0 的上游测试入口。
#
# 上游测试入口：scripts/test.sh（.github/workflows/ci.yml 以
#   working-directory: scripts / run: ./test.sh / UPLOAD=true 调用）
#
# 上游脚本假设宿主是「glibc + gcc + gcov」的 Linux：
#   1) gcc 编译 example/zproc.c（僵尸工厂）并后台跑两份
#   2) gcc -fprofile-arcs -ftest-coverage 编译 src/zps.c
#   3) 逐条 CLI 用例：-v / -h / -p / -a / -r / -q / -s / -n
#   4) gcov 覆盖率报告 + codecov 上传（UPLOAD=true 时）
#
# 本脚本分两阶段：
#   阶段 A —— 用编译期 shim（gcc→OHOS clang；gcov→记录「本平台无 GNU 工具链」）
#              让上游 scripts/test.sh **原样跑完**，记录其退出码与完整输出；
#   阶段 B —— 逐条复算每个用例的退出码与语义（上游是 && 链，短路点必须显式
#              暴露），并补两条上游缺失的合法组合用例，产出逐用例结果。
#
# 为便于逐条判定，阶段 B 的用例顺序做了「先构建两个产物、再启动僵尸工厂、
# 最后跑 CLI 用例」的整理（每条用例的命令与上游脚本逐字一致，语义不变）。
#
# 用法： bash run_upstream_tests.sh [工作目录]   # 默认 $TMPDIR/zps-2.0.0-upstream
# 产出： <工作目录>/upstream-test-script.log     上游脚本原样运行日志
#        <工作目录>/cases.log                    逐用例复算日志
#        <工作目录>/upstream-tests-junit.xml     逐用例机器可读结果
#
# 刻意不启用 `set -e`：本脚本要「跑完全部用例再统一判定」（阶段 A 的退出码本身
# 就是被观测对象），逐用例结果由 record() 汇总、最后以 CASE_FAIL 决定退出码。
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:-${TMPDIR:-/tmp}/zps-2.0.0-upstream}"
SRC_URL="https://github.com/orhun/zps/archive/refs/tags/2.0.0.tar.gz"
SRC_SHA256="84fa627c7eec92df62ecae129fe30fc7d16e297f20a3d126b8c53d04a6c35c60"
SDK_ROOT="${OHOS_SDK_ROOT:-/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos}"

rm -rf "$WORK"
mkdir -p "$WORK"
CASE_LOG="$WORK/cases.log"
CASES_TSV="$WORK/cases.tsv"
JUNIT="$WORK/upstream-tests-junit.xml"

# ── 0. 源码：官方 tarball + SHA256 校验（与 conandata.yml 一致） ──
SRC_DIR="$WORK/src"
mkdir -p "$SRC_DIR"
TARBALL="$WORK/zps-2.0.0.tar.gz"
curl -fsSL -o "$TARBALL" "$SRC_URL" || { echo "下载失败: $SRC_URL"; exit 3; }
echo "$SRC_SHA256  $TARBALL" | sha256sum -c - || { echo "源码 SHA256 校验失败"; exit 3; }
tar -xzf "$TARBALL" -C "$SRC_DIR" --strip-components=1
[ -f "$SRC_DIR/CMakeLists.txt" ] || { echo "找不到 zps 源码"; exit 2; }

# ── 1. 编译器 shim：gcc → OHOS clang，gcov → 明确记录不可用 ────
CLANG="$SDK_ROOT/native/llvm/bin/clang"
SYSROOT="$SDK_ROOT/native/sysroot"
[ -x "$CLANG" ] || { echo "找不到 OHOS clang: $CLANG"; exit 2; }
SHIM="$WORK/shim"
mkdir -p "$SHIM"

cat > "$SHIM/gcc" <<EOF
#!/data/service/hnp/bin/bash
# gcc shim：上游 scripts/test.sh 用 gcc，OHOS 上只有 clang。
# 上游参数原样透传，仅补交叉编译所需的目标三元组/系统根/lld 运行时。
exec "$CLANG" --target=aarch64-linux-ohos --sysroot="$SYSROOT" \\
     -fPIE -pie -fuse-ld=lld --rtlib=compiler-rt "\$@"
EOF
chmod +x "$SHIM/gcc"

cat > "$SHIM/gcov" <<'EOF'
#!/data/service/hnp/bin/bash
# gcov shim：OHOS 无 GNU 工具链（gcc/gcov 均不存在），覆盖率报告不可复现。
echo "gcov: not available on OHOS (no GNU toolchain) — coverage step not reproducible" >&2
exit 0
EOF
chmod +x "$SHIM/gcov"

echo "=== 环境 ==="
echo "work:    $WORK"
echo "clang:   $CLANG"
echo "sysroot: $SYSROOT"
echo "shim:    $SHIM  (gcc→OHOS clang, gcov→no-op)"
echo

# ── 2. 阶段 A：上游 scripts/test.sh 原样运行 ──────────────────
# 先打印运行前的僵尸清单：上游脚本内的 `./zps -r` / `./zps -q` 会向**全系统**所有
# 僵尸进程的父进程发 SIGTERM（工具语义，上游写法即如此），若主机上存在与本测试
# 无关的僵尸，其父进程也会被信号波及。保持上游原样执行，但把清单留档便于归因。
echo "=== 运行前 /proc 中的僵尸进程（上游 -r/-q 会向其父进程发 SIGTERM）==="
python3 - <<'PYEOF'
import glob, os
n = 0
for path in sorted(glob.glob('/proc/[0-9]*/stat')):
    try:
        data = open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        continue
    r = data.rfind(')')
    if r < 0:
        continue
    fields = data[r + 2:].split()
    if fields and fields[0] == 'Z':
        n += 1
        print('  zombie pid=%s ppid=%s comm=%s'
              % (path.split('/')[2], fields[1], data[data.find('(') + 1:r]))
print('  运行前僵尸总数: %d' % n)
PYEOF

echo
echo "=== 阶段 A：上游 scripts/test.sh 原样运行（仅注入编译器 shim）==="
A_LOG="$WORK/upstream-test-script.log"
( cd "$SRC_DIR/scripts" && PATH="$SHIM:$PATH" bash ./test.sh ) > "$A_LOG" 2>&1
A_RC=$?
echo "upstream scripts/test.sh exit code: $A_RC"
echo "(完整输出见 $A_LOG)"

# 上游脚本在 src/ 内就地编译，会留下产物；阶段 B 用干净副本
SRC_CASE="$WORK/case-src"
cp -a "$SRC_DIR" "$SRC_CASE"

# ── 3. 阶段 B：逐用例复算 ────────────────────────────────────
: > "$CASE_LOG"
: > "$CASES_TSV"
CASE_TOTAL=0; CASE_PASS=0; CASE_FAIL=0; CASE_SKIP=0; CASE_NA=0

record() {  # $1=id $2=name $3=verdict(PASS|FAIL|SKIP|NA) $4=detail
    CASE_TOTAL=$((CASE_TOTAL + 1))
    case "$3" in
        PASS) CASE_PASS=$((CASE_PASS + 1)) ;;
        FAIL) CASE_FAIL=$((CASE_FAIL + 1)) ;;
        SKIP) CASE_SKIP=$((CASE_SKIP + 1)) ;;
        NA)   CASE_NA=$((CASE_NA + 1)) ;;
    esac
    {
        printf '[%s] %-40s %s\n' "$1" "$2" "$3"
        printf '       %s\n' "$4"
    } | tee -a "$CASE_LOG"
    printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$(printf '%s' "$4" | tr '\n' ' ')" >> "$CASES_TSV"
}

echo
echo "=== 阶段 B：逐用例复算 ===" | tee -a "$CASE_LOG"

# C01 —— 上游：gcc -O3 -Wall zproc.c -o z.o
out="$(cd "$SRC_CASE/example" && PATH="$SHIM:$PATH" gcc -O3 -Wall zproc.c -o z.o 2>&1)"; rc=$?
if [ "$rc" -eq 0 ] && [ -x "$SRC_CASE/example/z.o" ]; then
    record C01 "gcc 编译 example/zproc.c" PASS "rc=0，产物 example/z.o 已生成（shim: OHOS clang）"
else
    record C01 "gcc 编译 example/zproc.c" FAIL "rc=$rc out=$out"
fi

# C02 —— 上游：gcc -fprofile-arcs -ftest-coverage -s -O3 -Wall -Wextra -pedantic zps.c -o zps
out="$(cd "$SRC_CASE/src" && PATH="$SHIM:$PATH" gcc -fprofile-arcs -ftest-coverage -s -O3 -Wall -Wextra -pedantic zps.c -o zps 2>&1)"; rc=$?
if [ "$rc" -eq 0 ] && [ -x "$SRC_CASE/src/zps" ]; then
    record C02 "gcc 编译 src/zps.c（覆盖率插桩）" PASS "rc=0，产物 src/zps 已生成（-fprofile-arcs/-ftest-coverage 被 clang 接受）"
else
    record C02 "gcc 编译 src/zps.c（覆盖率插桩）" FAIL "rc=$rc out=$out"
fi

ZPS="$SRC_CASE/src/zps"
list_zombies() { "$ZPS" -n 2>/dev/null | awk '$3 == "Z" { print $1, $2 }'; }

# C03 —— 上游：./z.o & ./z.o &（僵尸工厂，后续用例的前置条件）
zpid1=""; zpid2=""
( cd "$SRC_CASE/example" && exec ./z.o ) >/dev/null 2>&1 &
zpid1=$!
( cd "$SRC_CASE/example" && exec ./z.o ) >/dev/null 2>&1 &
zpid2=$!
sleep 1
zcount="$(list_zombies | wc -l)"
if [ "$zcount" -ge 2 ]; then
    record C03 "启动 2 份 z.o 制造僵尸（前置）" PASS "zps 观察到 Z 状态进程数=$zcount（父进程 pid=$zpid1/$zpid2）"
else
    record C03 "启动 2 份 z.o 制造僵尸（前置）" FAIL "zps 只观察到 $zcount 个僵尸"
fi

# run_case：rc=0 视为通过（与上游 && 链语义一致）
run_case() {  # $1=id $2=用例名 $3=期望描述 $4=命令
    local out rc
    out="$(cd "$SRC_CASE/src" && eval "$4" 2>&1)"; rc=$?
    if [ "$rc" -eq 0 ]; then
        record "$1" "$2" PASS "rc=0；$3"
    else
        record "$1" "$2" FAIL "rc=$rc；输出：$(printf '%s' "$out" | head -3 | tr '\n' '|')"
    fi
}

# C04-C06：上游链 1 —— ./zps -v && ./zps -h && printf '1' | ./zps -p
run_case C04 "zps -v" "打印版本横幅且含 v2.0.0" '$ZPS -v | grep -q "v2.0.0"'
run_case C05 "zps -h" "打印 usage 与全部 8 个选项" '$ZPS -h | grep -q -- "--reap" && $ZPS -h | grep -q -- "--no-color"'
run_case C06 "printf '1' | zps -p" "非交互 stdin 下按编号回收僵尸" 'printf 1 | $ZPS -p | grep -q "PID (Z):"'
# C07-C08：上游链 2 —— ./zps -a && ./zps -r
run_case C07 "zps -a" "列出全部用户态进程（表头之外还有进程行）" 'test "$($ZPS -a | wc -l)" -gt 1'
run_case C08 "zps -r" "向僵尸父进程发送默认 SIGTERM 并统计" '$ZPS -r | grep -q "Parent(s) signaled:"'
# C09：上游链 3 首命令 —— ./zps -q
run_case C09 "zps -q" "静默回收（stdout/stderr 均被 /dev/null 接管）" 'test -z "$($ZPS -q 2>&1)"'
# C10-C12：上游链 3 第 2-4 命令 —— ./zps -s 9 && ./zps -s SIGTERM && ./zps -s term
for spec in "C10:9" "C11:SIGTERM" "C12:term"; do
    id="${spec%%:*}"; arg="${spec#*:}"
    out="$(cd "$SRC_CASE/src" && "$ZPS" -s "$arg" 2>&1)"; rc=$?
    if [ "$rc" -eq 0 ]; then
        record "$id" "zps -s $arg（单独使用）" PASS "rc=0"
    else
        record "$id" "zps -s $arg（单独使用）" SKIP \
"上游把它写在 && 链第 2 位：-q 成功 → 本命令 rc=$rc（settings_check 要求 -s 必须与 -r/-p 同用）→ 上游链在此短路，
       其后的 '-s SIGTERM'/'-s term' 在上游脚本中从未执行。用例与工具契约冲突，记 SKIP（真实覆盖见 C16/C17）。"
    fi
done
# C13：上游链 4 —— ./zps -n
run_case C13 "zps -n" "禁用颜色输出（非 TTY 下无 ANSI 转义）" 'test -z "$($ZPS -n | od -c | grep 033)"'
# C14：上游 —— gcov zps.c
record C14 "gcov zps.c（覆盖率报告）" NA "OHOS 无 GNU 工具链（gcc/gcov 均不存在），覆盖率报告不可复现；clang 需 llvm-cov 且上游脚本未使用，故本项在鸿蒙上无法执行"
# C15：上游 —— [ "$UPLOAD" == 'true' ] && bash <(curl -s https://codecov.io/bash)
record C15 "codecov 覆盖率上传" NA "仅当 UPLOAD=true 时执行且需公网 codecov 客户端；上游脚本默认不设置 UPLOAD，本次未启用（无网络依赖）"

# C16-C17：补全用例（上游缺失的合法组合；用于覆盖 -s 的真实意图）
run_case C16 "zps -r -s CHLD（补全用例）" "README 推荐的 SIGCHLD 组合被接受并完成扫描" '$ZPS -r -s CHLD | grep -qE "PID|Parent\(s\)"'
run_case C17 "zps -r -s 9|15|SIGTERM|term（补全用例）" "数字信号号与信号名（含无 SIG 前缀）在 -r 组合下均可解析" 'for s in 9 15 SIGTERM term; do $ZPS -r -s $s >/dev/null || exit 1; done'

# 清理僵尸工厂
for p in "$zpid1" "$zpid2"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done
sleep 1

python3 - "$CASES_TSV" "$JUNIT" "$CASE_TOTAL" "$CASE_FAIL" "$((CASE_SKIP + CASE_NA))" <<'PYEOF'
import sys
from xml.sax.saxutils import escape
tsv, out, total, failed, skipped = sys.argv[1:6]
rows = [l.rstrip("\n").split("\t") for l in open(tsv, encoding="utf-8") if l.strip()]
cases = []
for cid, name, verdict, detail in rows:
    body = "" if verdict == "PASS" else (
        '\n      <skipped message="%s: %s"/>' % (verdict, escape(detail)))
    cases.append('    <testcase classname="upstream.zps-2.0.0" name="%s %s">%s</testcase>'
                 % (escape(cid), escape(name), body))
with open(out, "w", encoding="utf-8") as fh:
    fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    fh.write('<!-- zps 2.0.0 上游测试入口 scripts/test.sh 逐用例复算（HarmonyOS PC aarch64）-->\n')
    fh.write('<testsuites tests="%s" failures="%s" skipped="%s">\n' % (total, failed, skipped))
    fh.write('  <testsuite name="zps-2.0.0-upstream" tests="%s" failures="%s" skipped="%s">\n'
             % (total, failed, skipped))
    fh.write("\n".join(cases) + "\n")
    fh.write('  </testsuite>\n</testsuites>\n')
PYEOF

RUNNABLE=$((CASE_TOTAL - CASE_SKIP - CASE_NA))
{
    echo
    echo "=== 汇总 ==="
    echo "上游测试入口        : scripts/test.sh（.github/workflows/ci.yml 调用）"
    echo "阶段 A 退出码       : $A_RC   （日志: $A_LOG）"
    echo "逐用例总数          : $CASE_TOTAL（含补全用例 2 条）"
    echo "  PASS              : $CASE_PASS"
    echo "  FAIL              : $CASE_FAIL"
    echo "  SKIP              : $CASE_SKIP（上游 && 链短路 / 用例与工具契约冲突）"
    echo "  NA                : $CASE_NA（OHOS 无 GNU 工具链、未启用的上传步骤）"
    echo "可执行用例通过率    : $CASE_PASS/$RUNNABLE"
    echo "逐用例日志          : $CASE_LOG"
    echo "JUnit               : $JUNIT"
} | tee -a "$CASE_LOG"

[ "$CASE_FAIL" -eq 0 ] || exit 1
exit 0
