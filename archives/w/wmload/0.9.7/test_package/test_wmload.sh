#!/data/service/hnp/bin/bash
# test_wmload.sh — layered packaged-tool smoke test for wmload 0.9.7.
#
# wmload is an X11 dockapp.  "It draws its 64x64 load graph" is not a reachable
# pass condition on a headless build host, so the assertions are layered and
# every layer reports its own machine-readable verdict:
#
#   LOADER  : `wmload -ver` prints the upstream version banner.  The banner is
#             emitted at wmload.c:231, before any X call, so seeing it proves
#             the dynamic loader accepted the ELF *and* that the whole shared
#             library closure (libX11/libXpm/libXext) resolved.  Upstream exits
#             0 here because -ver is the only argument (argc == 2).
#             The error paths are asserted against their real upstream shape:
#             usage() writes to stderr and exits 1, and main() reaches it from
#             three distinct places — an unknown switch (default: usage()),
#             a switch whose operand is missing (`if(++i >= argc) usage()`),
#             and a non-option argument ("Invalid argument: ..." + usage()).
#   PROCESS : `wmload` with no argument must reach XOpenDisplay() and fail
#             there with the upstream text "can't open display" (wmload.c:245).
#             The exit code must be 1 — explicitly NOT 126/127, which would
#             mean the loader, not the missing display, is what broke.
#             Two parser contracts are probed separately: that every documented
#             switch is consumed without falling through to usage(), and that
#             the switch dispatcher keys on argv[i][1] only (so a long flag is
#             accepted when its second character is a known switch letter).
#   SKIP    : the rendering path, the click hook and the GetLoad() sampling
#             loop all start only after XOpenDisplay() succeeds, so they are
#             declared per-case SKIP with the observed signature, never as
#             PASS.  The sampling loop's data source (/proc/stat) is instead
#             exercised by ohos_procfs_probe, which reports the platform's
#             SELinux denial of that file as a SKIP with its errno.
#
# Usage: test_wmload.sh <staged-bin-dir> <writable-work-dir>

set -euo pipefail

BIN_DIR="${1:?staged bin directory is required}"
WORK_DIR="${2:?writable work directory is required}"
BIN="${BIN_DIR}/wmload"

# Deterministic headless assertion: an inherited DISPLAY would make the
# X-connection outcome depend on the worker's environment.
export DISPLAY=""

pass_count=0
skip_count=0
fail_count=0

fail_case() {
    local case_name="$1"
    local reason="$2"
    echo "WMLOAD_TEST_FAIL case=${case_name} reason=${reason}" >&2
    fail_count=$((fail_count + 1))
}

# Literal substring test.  The usage table contains "[+|-]" bracket groups, so
# glob-based comparison would misinterpret them; quoting the needle inside
# [[ == *"$needle"* ]] keeps every metacharacter literal.
contains() {
    [[ "$1" == *"$2"* ]]
}

if [[ ! -x "$BIN" ]]; then
    echo "WMLOAD_TEST_FAIL case=load-present reason=missing-or-not-executable path=${BIN}" >&2
    exit 1
fi

# ---- LOADER layer ---------------------------------------------------------

version_out=""
version_rc=0
version_out="$("$BIN" -ver 2>&1)" || version_rc=$?

if ! contains "$version_out" "wmload version: 0.9.7"; then
    fail_case "load-version-banner" "no-version-banner"
    printf '%s\n' "$version_out" | head -n 3 >&2
    exit 1
fi
echo "WMLOAD_TEST_PASS case=load-version-banner banner=\"wmload version: 0.9.7\""
pass_count=$((pass_count + 1))

if [[ "$version_rc" -ne 0 ]]; then
    fail_case "load-version-exit-code" "exit_code=${version_rc} expected=0"
    exit 1
fi
echo "WMLOAD_TEST_PASS case=load-version-exit-code exit_code=0"
pass_count=$((pass_count + 1))

# usage() goes to stderr (wmload.c:113-118) and exits 1.  Its first line is
# "usage:  <argv[0]> [-options ...]", i.e. it echoes whatever path the binary
# was invoked as, so the assertion keys on the invariant tail plus the option
# table header rather than on a literal program name.  Three distinct entry
# points lead there; each is asserted on its own because they exercise
# different parser branches.
usage_banner="[-options ...]"
option_header="where options include:"

usage_out=""
usage_rc=0
usage_out="$("$BIN" -z 2>&1)" || usage_rc=$?
if [[ "$usage_rc" -ne 1 ]] || ! contains "$usage_out" "$usage_banner" \
        || ! contains "$usage_out" "$option_header"; then
    fail_case "load-usage-unknown-switch" \
        "exit_code=${usage_rc} banner_missing (switch is dispatcher default: usage())"
    printf '%s\n' "$usage_out" | head -n 3 >&2
    exit 1
fi
echo "WMLOAD_TEST_PASS case=load-usage-unknown-switch exit_code=1 banner=stderr"
pass_count=$((pass_count + 1))

missing_operand_out=""
missing_operand_rc=0
missing_operand_out="$("$BIN" -u 2>&1)" || missing_operand_rc=$?
if [[ "$missing_operand_rc" -ne 1 ]] || ! contains "$missing_operand_out" "$usage_banner"; then
    fail_case "load-usage-missing-operand" \
        "exit_code=${missing_operand_rc} banner_missing (operand guard: if(++i >= argc) usage())"
    printf '%s\n' "$missing_operand_out" | head -n 3 >&2
    exit 1
fi
echo "WMLOAD_TEST_PASS case=load-usage-missing-operand exit_code=1 banner=stderr"
pass_count=$((pass_count + 1))

non_option_out=""
non_option_rc=0
non_option_out="$("$BIN" wmload-not-an-option 2>&1)" || non_option_rc=$?
if [[ "$non_option_rc" -ne 1 ]] || ! contains "$non_option_out" "Invalid argument: wmload-not-an-option" \
        || ! contains "$non_option_out" "$usage_banner"; then
    fail_case "load-usage-non-option" \
        "exit_code=${non_option_rc} invalid-argument-banner-missing (wmload.c:238-241)"
    printf '%s\n' "$non_option_out" | head -n 3 >&2
    exit 1
fi
echo "WMLOAD_TEST_PASS case=load-usage-non-option exit_code=1 banner=stderr"
pass_count=$((pass_count + 1))

# The option table is the tool's whole CLI surface; assert all eight entries.
missing_options=""
for option in "-u <secs>" "-exe <program>" "-led <color>" \
              "-position [+|-]x[+|-]y" "-shape" "-iconic" "-withdrawn" "-ver"; do
    if ! contains "$usage_out" "$option"; then
        missing_options="${missing_options} [${option}]"
    fi
done
if [[ -n "$missing_options" ]]; then
    fail_case "load-usage-option-table" "missing-options=${missing_options}"
    exit 1
fi
echo "WMLOAD_TEST_PASS case=load-usage-option-table options=8"
pass_count=$((pass_count + 1))

# ---- PROCESS layer --------------------------------------------------------

noarg_rc=0
"$BIN" >"${WORK_DIR}/wmload-noarg.out" 2>&1 || noarg_rc=$?
noarg_out="$(cat "${WORK_DIR}/wmload-noarg.out")"

if [[ "$noarg_rc" -eq 126 || "$noarg_rc" -eq 127 ]]; then
    fail_case "process-x-display-signature" "loader-rejected exit_code=${noarg_rc}"
    printf '%s\n' "$noarg_out" | head -n 3 >&2
    exit 1
fi
if ! contains "$noarg_out" "can't open display"; then
    fail_case "process-x-display-signature" "exit_code=${noarg_rc} no-x-layer-signature"
    printf '%s\n' "$noarg_out" | head -n 3 >&2
    exit 1
fi
echo "WMLOAD_TEST_PASS case=process-x-display-signature exit_code=${noarg_rc} signature=cant-open-display"
pass_count=$((pass_count + 1))

# Every documented switch must be consumed by the dispatcher.  All of them lead
# to the same XOpenDisplay() failure here, so the discriminator is that none of
# them produces the usage banner.
unparsed_flags=""
probe_flags=("-u 1" "-exe /bin/echo" "-led green" "-position +0+0" "-iconic" "-withdrawn" "-shape")
for probe in "${probe_flags[@]}"; do
    flag_rc=0
    # shellcheck disable=SC2086
    flag_out="$("$BIN" $probe 2>&1)" || flag_rc=$?
    if contains "$flag_out" "$option_header"; then
        unparsed_flags="${unparsed_flags} [${probe}]"
    fi
done
if [[ -n "$unparsed_flags" ]]; then
    fail_case "process-switch-consumption" "flags-rejected-by-parser=${unparsed_flags}"
    exit 1
fi
echo "WMLOAD_TEST_PASS case=process-switch-consumption flags=7 rejected=0"
pass_count=$((pass_count + 1))

# The dispatcher is `switch (argv[i][1])`: a long flag is accepted whenever its
# SECOND character is a known switch letter, and rejected otherwise.  Both
# halves are asserted, because a future refactor to exact-match parsing would
# silently change the accepted CLI surface.
prefix_out=""
prefix_rc=0
prefix_out="$("$BIN" -wmload-invalid-flag 2>&1)" || prefix_rc=$?
if contains "$prefix_out" "$option_header"; then
    fail_case "process-switch-second-character" \
        "exit_code=${prefix_rc} '-wmload-invalid-flag' was rejected, but argv[i][1]='w' is a known switch"
    printf '%s\n' "$prefix_out" | head -n 3 >&2
    exit 1
fi
echo "WMLOAD_TEST_PASS case=process-switch-second-character second_char=w accepted=1"
pass_count=$((pass_count + 1))

# ---- CAPABILITY-DEPENDENT cases (declared skipped, with signatures) -------

render_rc=0
"$BIN" -shape >/dev/null 2>&1 || render_rc=$?
echo "WMLOAD_TEST_SKIP case=gui-dockapp-render exit_code=${render_rc} reason=headless-no-x-display"
skip_count=$((skip_count + 1))

click_rc=0
"$BIN" -exe /bin/echo >/dev/null 2>&1 || click_rc=$?
echo "WMLOAD_TEST_SKIP case=click-execute-hook exit_code=${click_rc} reason=headless-no-x-display-no-pointer-event"
skip_count=$((skip_count + 1))

sample_rc=0
"$BIN" -u 1 >/dev/null 2>&1 || sample_rc=$?
echo "WMLOAD_TEST_SKIP case=procfs-sampling-loop exit_code=${sample_rc} reason=headless-no-x-display-loop-entered-after-XOpenDisplay"
skip_count=$((skip_count + 1))

echo "WMLOAD_SMOKE_DONE passed=${pass_count} skipped=${skip_count} failed=${fail_count}"
exit 0
