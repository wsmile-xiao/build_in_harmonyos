#!/bin/sh
# =============================================================================
# repro-code-sign-closure.sh — 依赖制品 .codesign 段「存在但失效」检测 / 三态复现
#
# 解决的问题（知识库草稿 DRAFT-lomiri-polkit-agent-0.3.3-dep-closure-codesign-resign）：
#   已发布依赖包里的共享库带 .codesign 段，但签名对 OHOS 加载器无效
#   → 消费者运行期 dlopen 被静默拒载，表现为下游符号解析失败
#     （Error relocating ...: symbol not found / ConanException: Error 127），
#   编译链接全绿，极易误判为「漏依赖 / 搜索路径」。
#   注意：段存在 ≠ 有效；`llvm-readelf -S | grep -c codesign` 只能作存在性参考。
#
# 用法:
#   sh repro-code-sign-closure.sh scan <lib_dir> [<lib_dir> ...]
#       对目录下每个 *so* 做 dlopen 探针，输出 OK / UNSIGNED(签名失效) 清单。
#
#   sh repro-code-sign-closure.sh demo <lib_dir> <soname>
#       三态对照（唯一变量 = 签名）：
#         a) 原件            → 期望可加载
#         b) 去 .codesign 段 → 期望被拒载（复现机制）
#         c) 去段 + selfSign → 期望恢复
#       全部符合预期 exit 0；任一不符 exit 1；用法错误 exit 2。
#
# 设计约束（遵循仓库规则）:
#   · 只在私有可写临时目录内改文件（复制目标库过去），绝不原地改 conan 缓存或共享前缀
#     （E524/R49：注入/改写共享前缀会与 CI worker 互相污染）
#   · 工具经 PATH 探测 + 已知 HNP 目录兜底，不硬编码作者本机路径
#   · 日志一律重定向到文件，不接 head 等提前退出的消费者（规避 SIGPIPE）
#   · 签名工具缺失即 exit 1（不静默跳过、不伪造通过）
# =============================================================================
set -u

PY=python3
W="${TMPDIR:-/tmp}/repro-codesign-$$"
LOG="$W/repro.log"
STAGE="$W/stage"
ORIG_LDP="${LD_LIBRARY_PATH:-}"

die() { printf '%s\n' "ERROR: $*" >&2; exit 1; }
usage() { sed -n '2,30p' "$0" >&2; exit 2; }

# ---- 工具探测：PATH 优先，已知 HNP 目录兜底（不硬编码作者本机路径） ----
find_tool() {
  _n="$1"
  _p="$(command -v "$_n" 2>/dev/null || true)"
  if [ -z "$_p" ]; then
    for _d in /data/service/hnp/bin "$HOME/usr/local/bin" "$HOME/.local/bin"; do
      if [ -x "$_d/$_n" ]; then _p="$_d/$_n"; break; fi
    done
  fi
  printf '%s' "$_p"
}

OBJCOPY="$(find_tool llvm-objcopy)"
[ -n "$OBJCOPY" ] || OBJCOPY="$(find_tool objcopy)"
SIGNER="$(find_tool binary-sign-tool)"

# ---- dlopen 探针：OK / UNSIGNED(被拒载) / MISSING / OTHER ----
# 结果写 stdout（单行状态词），详细输出进日志。
probe() {
  _dir="$1"; _so="$2"
  _out="$W/probe.out"
  # 只看本次调用的 stderr：累计日志里的历史错误会污染分类
  LD_LIBRARY_PATH="$_dir${ORIG_LDP:+:$ORIG_LDP}" "$PY" -c \
    'import ctypes,sys; ctypes.CDLL(sys.argv[1]); print("LOADED")' "$_so" >"$_out" 2>&1 || true
  if grep -q '^LOADED' "$_out" 2>/dev/null; then
    printf 'OK'
  elif grep -qE 'Permission denied|Operation not permitted' "$_out" 2>/dev/null; then
    printf 'UNSIGNED'
  elif grep -qE 'cannot open shared object|No such file' "$_out" 2>/dev/null; then
    printf 'MISSING'
  else
    printf 'OTHER'
  fi
}

copy_target() {
  # 把目标库及其软链复制进 STAGE（软链用 rm -f && ln -s 重建，HMDFS 不支持 ln -sf 覆盖）
  _dir="$1"; _soname="$2"
  mkdir -p "$STAGE" || die "无法创建临时目录 $STAGE"
  _n=0
  for _f in "$_dir/$_soname"*; do
    [ -e "$_f" ] || continue
    _base="${_f##*/}"
    rm -f "$STAGE/$_base"
    if [ -L "$_f" ]; then
      ln -s "$(readlink "$_f")" "$STAGE/$_base" || die "建链失败 $_base"
    else
      cp -p "$_f" "$STAGE/$_base" || die "复制失败 $_base"
    fi
    _n=$((_n + 1))
  done
  [ "$_n" -gt 0 ] || die "目标不存在: $_dir/$_soname"
}

cmd_scan() {
  _any=0
  for _dir in "$@"; do
    [ -d "$_dir" ] || { printf 'SKIP  %s (不是目录)\n' "$_dir"; continue; }
    for _f in "$_dir"/*so*; do
      [ -f "$_f" ] || [ -L "$_f" ] || continue
      [ -L "$_f" ] && continue          # 只探实体文件，软链由其目标代表
      _r="$(probe "$_dir" "${_f##*/}")"
      printf '%-9s %s\n' "$_r" "$_f"
      [ "$_r" = "UNSIGNED" ] && _any=1
    done
  done
  [ "$_any" -eq 0 ] && printf 'RESULT: 未发现签名失效的共享库\n' || printf 'RESULT: 存在签名失效的共享库（消费者侧 dlopen 会被拒载）\n'
  return "$_any"
}

cmd_demo() {
  _dir="$1"; _so="$2"
  [ -n "$OBJCOPY" ] || die "找不到 llvm-objcopy/objcopy"
  [ -n "$SIGNER" ]  || die "找不到 binary-sign-tool（签名工具缺失 → 按 env_unsupported 上报，不得跳过）"
  mkdir -p "$W/sign" || die "无法创建 $W/sign"
  copy_target "$_dir" "$_so"

  printf '== 工具: objcopy=%s signer=%s\n' "$OBJCOPY" "$SIGNER"
  printf '== 工作副本: %s/%s*（不改动原始目录）\n' "$STAGE" "$_so"

  rc=0
  # a) 原件
  _a="$(probe "$STAGE" "$_so")"
  printf 'a) 原件              -> %s (期望 OK)\n' "$_a"
  [ "$_a" = "OK" ] || { printf '   前置不成立：副本原件不可加载（%s），换一个已知可加载的库再试\n' "$_a"; rc=1; }

  # b) 仅去 .codesign 段
  for _f in "$STAGE"/*so*; do
    [ -f "$_f" ] && [ ! -L "$_f" ] || continue
    "$OBJCOPY" --remove-section .codesign "$_f" >>"$LOG" 2>&1 || die "去段失败: $_f"
  done
  _b="$(probe "$STAGE" "$_so")"
  printf 'b) 仅去段            -> %s (期望 UNSIGNED)\n' "$_b"
  [ "$_b" = "UNSIGNED" ] || { printf '   未复现：去段后仍可加载，说明本库不是签名门禁路径\n'; rc=1; }

  # c) 去段 + 统一重签
  for _f in "$STAGE"/*so*; do
    [ -f "$_f" ] && [ ! -L "$_f" ] || continue
    _out="$W/sign/${_f##*/}"
    "$SIGNER" sign -inFile "$_f" -outFile "$_out" -selfSign 1 >>"$LOG" 2>&1 \
      || die "签名失败: $_f（不得跳过，运行期错误会下移到消费者）"
    cp -f "$_out" "$_f" || die "回写失败: $_f"
  done
  _c="$(probe "$STAGE" "$_so")"
  printf 'c) 去段 + selfSign   -> %s (期望 OK)\n' "$_c"
  [ "$_c" = "OK" ] || { printf '   重签后仍不可加载：查 mode/LD_LIBRARY_PATH/依赖是否同样失效\n'; rc=1; }

  if [ "$rc" -eq 0 ]; then
    printf 'RESULT: 三态符合预期 —— 已确认为「.codesign 段存在但失效」，需在消费者侧对依赖闭包重签\n'
  else
    printf 'RESULT: 三态不符合预期 —— 见上面逐条说明（详细日志 %s）\n' "$LOG"
  fi
  return "$rc"
}

# ---------------- main ----------------
[ "$#" -ge 2 ] || usage
cmd="$1"; shift
mkdir -p "$W" 2>/dev/null || die "无法创建可写临时工作目录 $W（/tmp 在 OHOS 上常只读，请设置 TMPDIR）"
printf '# repro-code-sign-closure %s\n# workdir=%s\n' "$cmd" "$W" >"$LOG"

case "$cmd" in
  scan) cmd_scan "$@"; rc=$? ;;
  demo) [ "$#" -eq 2 ] || usage; cmd_demo "$1" "$2"; rc=$? ;;
  *)    usage ;;
esac
printf '# 详细日志: %s\n' "$LOG"
exit "$rc"
