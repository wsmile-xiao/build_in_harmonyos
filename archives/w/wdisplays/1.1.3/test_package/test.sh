#!/data/service/hnp/bin/bash
# test_package/test.sh — wdisplays 1.1.3 consumer test + HarmonyOS platform test
#
# Usage: bash test.sh <package bin dir>
#
# 消费者视角断言（R34：真实使用被交付物）+ 鸿蒙特有断言（9 条）：
#   1. bin/wdisplays 存在且可执行
#   2. ELF 为 AArch64
#   3. ELF 带 .codesign 段（HMFS 未签名 ELF 不可执行，OHOS 专有要求）
#   4/5. 动态链接 OHOS 制品仓的 libwayland-client / libgtk-3
#   6. libepoxy 以静态方式链接进来（OHOS 制品仓 libepoxy 为 .a）
#   7. 鸿蒙 GDK-Wayland 兼容层（补丁 0001）确已编入产物
#   8. gnome.compile_resources 产出的界面资源确已编入产物
#   9. 真机运行 wdisplays --help（GApplication 内建选项，无需 compositor）
set -u

BIN_DIR="${1:-}"
BIN="${BIN_DIR}/wdisplays"
READELF="/data/service/hnp/bin/llvm-readelf"
NM="/data/service/hnp/bin/llvm-nm"
STRINGS="/data/service/hnp/bin/llvm-strings"

pass=0
fail=0
skip=0
ok()   { echo "  [PASS] $1"; pass=$((pass + 1)); }
bad()  { echo "  [FAIL] $1"; fail=$((fail + 1)); }
note() { echo "  [SKIP] $1"; skip=$((skip + 1)); }

echo "[test] wdisplays package content: ${BIN_DIR}"

# ── 1. artifact present ────────────────────────────────────────────────
if [ -x "${BIN}" ]; then
  ok "bin/wdisplays present and executable"
else
  bad "bin/wdisplays missing or not executable: ${BIN}"
  echo "[test] RESULT: pass=${pass} fail=${fail} skip=${skip}"
  exit 1
fi

# ── 2/3. OHOS ELF identity, signing and shared linkage ─────────────────
if [ -f "${READELF}" ]; then
  machine="$("${READELF}" -h "${BIN}" 2>/dev/null | grep -m1 'Machine:')"
  case "${machine}" in
    *AArch64*) ok "ELF machine is AArch64" ;;
    *)         bad "unexpected ELF machine: ${machine}" ;;
  esac

  if "${READELF}" -S "${BIN}" 2>/dev/null | grep -q '\.codesign'; then
    ok "ELF carries a .codesign section (OHOS self-signed)"
  else
    bad "ELF has no .codesign section; HMFS would refuse to execute it"
  fi

  needed="$("${READELF}" -d "${BIN}" 2>/dev/null)"
  for lib in libwayland-client libgtk-3; do
    if echo "${needed}" | grep -q "${lib}"; then
      ok "links ${lib} (OHOS repository dependency)"
    else
      bad "${lib} not present in DT_NEEDED"
    fi
  done
else
  note "llvm-readelf not found; ELF checks skipped"
fi

# ── 4. epoxy arrives statically from the OHOS repository ───────────────
if [ -f "${NM}" ]; then
  if "${NM}" "${BIN}" 2>/dev/null | grep -q 'epoxy_conservative_gl_version'; then
    ok "libepoxy linked statically (epoxy symbols present in binary)"
  else
    bad "libepoxy not linked into the binary"
  fi

  # ── 5. OHOS GDK-Wayland compatibility layer compiled in ──────────────
  if "${NM}" "${BIN}" 2>/dev/null | grep -q 'gdk_wayland_display_get_wl_display'; then
    ok "OHOS gdkwayland compat layer symbol present (patch 0001 linked)"
  else
    bad "OHOS gdkwayland compat layer symbol missing"
  fi
else
  note "llvm-nm not found; symbol checks skipped"
fi

# ── 6. compiled-in GResource bundle ────────────────────────────────────
if [ -f "${STRINGS}" ]; then
  if "${STRINGS}" "${BIN}" 2>/dev/null | grep -q 'wdisplays-resources'; then
    ok "GResource bundle wdisplays-resources embedded"
  else
    bad "GResource bundle not embedded"
  fi
else
  note "llvm-strings not found; resource check skipped"
fi

# ── 7. real executable smoke run ───────────────────────────────────────
# wdisplays is a wayland GUI client; --help is handled by GApplication before
# any display/compositor is required, so it works head-less.
help_out="$("${BIN}" --help 2>&1)"
help_rc=$?
echo "  [info] 'wdisplays --help' exit=${help_rc}"
printf '%s\n' "${help_out}" | sed 's/^/  [info]   /'
if [ "${help_rc}" -eq 0 ] && printf '%s\n' "${help_out}" | grep -qiE 'usage|wdisplays'; then
  ok "binary runs on device: 'wdisplays --help' exit 0 with usage output"
else
  bad "'wdisplays --help' did not run cleanly (exit=${help_rc})"
fi

echo "[test] RESULT: pass=${pass} fail=${fail} skip=${skip} (total=$((pass + fail + skip)))"
if [ "${fail}" -ne 0 ]; then
  exit 1
fi
echo "[test] wdisplays 1.1.3 HarmonyOS test suite PASSED"
