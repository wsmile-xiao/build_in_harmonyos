#!/usr/bin/env bash
# Werror-autotools 知识库拓展 — 复现脚本（Step4）
#
# 双向验证（干净环境 conan create 全流程）：
#   ① 不启用 SKILL（剔除 Werror 处理补丁）→ 编译失败，复现原始 [-Werror] 报错
#   ② 启用 SKILL（应用补丁模板）→ 编译通过
#
# 样例库：schism 20260524（上游 configure 硬编码 -Werror + 9 处 -Werror=<flag>）
#
# 用法：
#   bash reproduce.sh <配方目录> <工作输出目录>
#   例: bash reproduce.sh archives/s/schism/20260524 "$HOME/tmp/werror-repro"
#   （输出目录勿用 /tmp：本平台 /tmp 只读，E002 陷阱）
#
# 约束：
#   - 不写死本地绝对路径：配方目录/输出目录均由参数传入；conan profile 经
#     REPO_ROOT（脚本相对定位）或环境变量 OHC_PROFILE 指定
#   - 规避 SIGPIPE：所有命令输出重定向到日志文件（绝不直接管道给 head 等
#     可能提前关闭管道的读端），读取日志用循环逐行或 read_file 方式
#   - 仅依赖项目内置 clang 工具链（conan profile 决定），不依赖终端缓存
set -u

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
RECIPE_DIR="${1:?usage: reproduce.sh <recipe-dir> <out-dir>}"
OUT_DIR="${2:?usage: reproduce.sh <recipe-dir> <out-dir>}"
PROFILE="${OHC_PROFILE:-$REPO_ROOT/ci/conan/profiles/ohos-aarch64}"

CONAN="${CONAN:-conan}"
LOG_MAIN="$OUT_DIR/reproduce-main.log"
mkdir -p "$OUT_DIR"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >> "$LOG_MAIN"; }

# ---------- 准备两个配方副本：A=无补丁（复现失败） B=有补丁（SKILL 生效） ----------
setup_variant() {
  local dst="$1" mode="$2"
  rm -rf "$dst"
  mkdir -p "$dst"
  cp "$RECIPE_DIR"/conanfile.py "$RECIPE_DIR"/conandata.yml "$dst/"
  cp -r "$RECIPE_DIR"/test_package "$dst/" 2>>"$LOG_MAIN"
  mkdir -p "$dst/patches"
  if [ "$mode" = "noskill" ]; then
    # 仅保留与 Werror 无关的补丁（config.guess/sub 属平台探测，非本 SKILL 策略），
    # 剔除 0003/0004 两个 Werror 处理补丁 —— 模拟"未启用 SKILL"
    for p in "$RECIPE_DIR"/patches/*.patch; do
      case "$(basename "$p")" in
        0003-*|0004-*) : ;;                 # skip Werror patches
        *) cp "$p" "$dst/patches/" ;;
      esac
    done
    # 从 conandata.yml 中去掉 0003/0004 补丁声明
    grep -v -E '0003-|0004-' "$RECIPE_DIR"/conandata.yml > "$dst/conandata.yml"
  else
    # 启用 SKILL：全量补丁（含 0003/0004 Werror 处理）
    cp "$RECIPE_DIR"/patches/*.patch "$dst/patches/" 2>>"$LOG_MAIN"
    cp "$RECIPE_DIR"/conandata.yml "$dst/"
  fi
}

run_create() {
  local dst="$1" logfile="$2"
  # 输出重定向到文件（SIGPIPE 安全），退出码由 wait 捕获
  ( cd "$dst" && "$CONAN" create . -pr:h="$PROFILE" -pr:b="$PROFILE" \
      --build=missing -nr > "$logfile" 2>&1 )
  echo $?
}

# ---------- ① 不启用 SKILL：应复现 -Werror 编译失败 ----------
log "=== variant A: noskill (expect FAIL with -Werror evidence) ==="
A_DIR="$OUT_DIR/variant-noskill"
A_LOG="$OUT_DIR/variant-noskill-build.log"
setup_variant "$A_DIR" noskill
A_RC=$(run_create "$A_DIR" "$A_LOG")
log "variant-noskill conan create rc=$A_RC"

# 从日志提取 [-Werror] 证据行（写入文件，不经管道 head）
EVIDENCE_LOG="$OUT_DIR/werror-evidence.log"
grep -m 20 -n -E 'error:.*\[-Werror' "$A_LOG" > "$EVIDENCE_LOG" 2>>"$LOG_MAIN"
EVIDENCE_N=$(grep -c -E 'error:.*\[-Werror' "$A_LOG" 2>>"$LOG_MAIN" || true)
log "werror evidence lines: $EVIDENCE_N (see $EVIDENCE_LOG)"

# ---------- ② 启用 SKILL：应编译通过 ----------
log "=== variant B: skill-on (expect PASS) ==="
B_DIR="$OUT_DIR/variant-skill"
B_LOG="$OUT_DIR/variant-skill-build.log"
setup_variant "$B_DIR" skill
B_RC=$(run_create "$B_DIR" "$B_LOG")
log "variant-skill conan create rc=$B_RC"

# ---------- 汇总判定（写入结果文件 + stdout 摘要） ----------
RESULT_FILE="$OUT_DIR/reproduce-result.json"
if [ "$A_RC" -ne 0 ] && [ "$EVIDENCE_N" -gt 0 ] && [ "$B_RC" -eq 0 ]; then
  VERDICT="pass"
elif [ "$A_RC" -eq 0 ]; then
  # 上游可能已修复 Werror 或环境差异：视为不适用，而非失败
  VERDICT="not-applicable (noskill build passed; Werror issue absent in this env)"
else
  VERDICT="fail"
fi

cat > "$RESULT_FILE" <<EOF
{
  "skill": "werror-autotools",
  "sample": "$(basename "$RECIPE_DIR")",
  "noskill_rc": $A_RC,
  "skill_rc": $B_RC,
  "werror_evidence_lines": $EVIDENCE_N,
  "evidence_log": "$(basename "$EVIDENCE_LOG")",
  "verdict": "$VERDICT"
}
EOF

log "=== verdict: $VERDICT ==="
printf '%s\n' "$VERDICT"
printf 'result: %s\nevidence: %s\n' "$RESULT_FILE" "$EVIDENCE_LOG"
[ "$VERDICT" = "pass" ] && exit 0 || exit 1
