#!/data/service/hnp/bin/bash
# test_package/test.sh — rocminfo 6.4.3 消费者端到端测试 (OpenHarmony PC)
#
# 被测交付件：已安装的 `rocm_agent_enumerator`（上游唯一"无需 ROCm 栈"即可工作的组件）。
# 本脚本以**消费者身份**真实执行该交付件，并校验其可观察契约：
#   stdout 的 GCN ISA 目标列表 + 退出码。
#
# 为什么不用 conanfile.py 里的 self.run() 直接跑 python：
#   AI 检视（rule RV-34/R40）指出"以 `python3 <脚本>` 方式调用时，被测的其实是宿主
#   解释器，而不是包产物" —— 该指出成立。正确的消费者用法是**执行 PATH 上已安装的
#   命令本身**（上游 README: "Upon a successful build the binary, rocminfo, and the
#   python script, rocm_agent_enumerator, will be in the build folder"；上游
#   CMakeLists.txt:180 `install(PROGRAMS ... DESTINATION ${CMAKE_INSTALL_BINDIR})`）。
#   因此这里改为 `command -v rocm_agent_enumerator` 定位 **包安装出来的那个文件**，
#   再直接执行它（它自带 `#!/usr/bin/env python3` shebang），参数与工作目录全部在
#   临时目录中构造，绝不触碰源码树。
#
# 运行环境：conanrun（VirtualRunEnv 已把包 bin/ 前置进 PATH）。
set -eu

PASS=0
fail() { echo "FAIL: $*"; exit 1; }
ok()   { PASS=$((PASS + 1)); echo "PASS $PASS: $*"; }

echo "--- rocminfo 6.4.3 consumer e2e ---"

# ---------------------------------------------------------------- 1/5
# 交付件完整性 + 可执行解释器。
# 交付件是 Python 脚本，消费者必须自带解释器；缺失时明确报错（不静默通过）。
CMD="$(command -v rocm_agent_enumerator 2>/dev/null || true)"
[ -n "$CMD" ] || fail "rocm_agent_enumerator not on PATH after installing the package"
[ -f "$CMD" ] || fail "$CMD is not a regular file"
[ -x "$CMD" ] || fail "$CMD is not executable"
echo "consumer command: $CMD"
grep -q '^#!' "$CMD" || fail "$CMD has no shebang"
PY="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
[ -n "$PY" ] || fail "no python interpreter on this machine: the delivered component is a Python script and cannot run without one"
ok "package artifact present and executable ($CMD), interpreter $PY"

# 临时工作目录：一次性，结束即清理；全部中间文件落在 /tmp 之外的 $TMPDIR。
WORK="$(mktemp -d "${TMPDIR:-/tmp}/rocminfo-e2e-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# 构造"消费者副本"：把包安装出来的脚本复制到临时目录，模拟消费者把它放到自己
# 的部署目录里使用（上游策略 2 的语义就是"脚本同目录下的 target.lst"）。
mkdir -p "$WORK/s1" "$WORK/s2" "$WORK/s3" "$WORK/s4"
for d in s1 s2 s3 s4; do cp "$CMD" "$WORK/$d/rocm_agent_enumerator"; done
chmod +x "$WORK"/s*/rocm_agent_enumerator

# 在给定目录下执行"该目录里的那份交付件"，stdout 存文件后读回。
RC=0
OUT=""
run_enum() {  # run_enum <dir-name> [ROCM_TARGET_LST]
  local name="$1" out="$WORK/$1.out"
  if [ "$#" -ge 2 ]; then
    ( cd "$WORK/$name" && ROCM_TARGET_LST="$2" ./rocm_agent_enumerator > "$out" 2>&1 )
  else
    ( cd "$WORK/$name" && env -u ROCM_TARGET_LST ./rocm_agent_enumerator > "$out" 2>&1 )
  fi
  RC=$?
  OUT="$(sed -e 's/[[:space:]]*$//' "$out" | grep -v '^$' || true)"
}

# ---------------------------------------------------------------- 2/5
# 文档化方式 2：脚本同目录的 target.lst。
# 输入刻意混入 `#` 注释行与空行 —— 上游 getGCNISA(match_from_beginning=True)
# 必须让注释行天然失效，否则解析契约被破坏。
cat > "$WORK/s2/target.lst" <<'EOF'
# OHOS PC target list
gfx906

# next
gfx908
gfx1030
EOF
run_enum s2
[ "$RC" = "0" ] || fail "strategy 2 exit code = $RC (expected 0); output: $OUT"
EXPECT2="$(printf 'gfx906\ngfx908\ngfx1030')"
[ "$OUT" = "$EXPECT2" ] || fail "strategy 2 output mismatch: expected [$EXPECT2], got [$OUT]"
ok "strategy 2 (colocated target.lst, comments/blanks parsed) -> $(echo "$OUT" | tr '\n' ' ')"

# ---------------------------------------------------------------- 3/5
# 文档化方式 1：ROCM_TARGET_LST 环境变量。
printf 'gfx90a\ngfx942\n' > "$WORK/m1.lst"
run_enum s1 "$WORK/m1.lst"
[ "$RC" = "0" ] || fail "strategy 1 exit code = $RC (expected 0); output: $OUT"
EXPECT1="$(printf 'gfx90a\ngfx942')"
[ "$OUT" = "$EXPECT1" ] || fail "strategy 1 output mismatch: expected [$EXPECT1], got [$OUT]"
ok "strategy 1 (ROCM_TARGET_LST env var) -> $(echo "$OUT" | tr '\n' ' ')"

# ---------------------------------------------------------------- 4/5
# 文档化优先级：ROCM_TARGET_LST 必须胜过同目录 target.lst。
printf 'gfx900\n' > "$WORK/s3/target.lst"
run_enum s3 "$WORK/m1.lst"
[ "$RC" = "0" ] || fail "precedence case exit code = $RC (expected 0); output: $OUT"
[ "$OUT" = "$EXPECT1" ] || fail "documented precedence violated (ROCM_TARGET_LST must win over colocated target.lst): got [$OUT]"
ok "documented precedence (env var beats colocated file) -> $(echo "$OUT" | tr '\n' ' ')"

# ---------------------------------------------------------------- 5/5
# 负对照：没有任何目标来源时不得凭空输出目标。
# 注意本机上 /usr/bin/lspci 可能真实存在 —— 那时上游 LSPCI 路径会返回空列表
# （无 AMD PCI 设备），结论仍是"无输出"，故该断言在本平台两种情形下都成立。
run_enum s4
[ "$RC" = "0" ] || fail "negative-control exit code = $RC (expected 0); output: $OUT"
[ -z "$OUT" ] || fail "negative control: expected no output with no target source, got [$OUT]"
ok "negative control (no target source -> no invented target)"

echo "test rocminfo 6.4.3: 5/5 consumer checks PASS"
exit 0
