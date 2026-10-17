#!/usr/bin/env bash
# kw_test_runner.sh — test_package harness for kworkflow/0.10 on OHOS (aarch64)
#
# Sections:
#   A. OHOS adaptation cases (new for this port): bash dependency/PATH
#      injection, packaging layout invariants, toybox portability patches,
#      kw smoke (version/help/mktemp path).
#   B. Real upstream unit-test subset (vendored from tag 0.10, executed
#      against the packaged artifacts reconstructed into a repo layout).
#
# Excluded upstream tests are documented in EXCLUDED-TESTS.md / MANIFEST.yml.
set -u

KW_PKG_ROOT="${KW_PKG_ROOT:?KW_PKG_ROOT must be set}"
BASH_PKG_ROOT="${BASH_PKG_ROOT:?BASH_PKG_ROOT must be set}"
TEST_SRC="${TEST_SRC:?TEST_SRC must be set}"
BASH_BIN="${BASH_PKG_ROOT}/bin/bash"

PASS=0
FAIL=0
FAILED_CASES=""

report_pass() { printf '[PASS] %s\n' "$1"; PASS=$((PASS + 1)); }
report_fail() {
  printf '[FAIL] %s\n' "$1"
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES} ${1}"
}

check() {
  # check <name> <expected_rc> <actual_rc>
  if [ "$2" -eq "$3" ]; then
    report_pass "$1"
  else
    report_fail "$1 (rc expected $2, got $3)"
  fi
}

WORK="$(mktemp -d)" || exit 3
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/tmp"
# OHOS /tmp is a read-only tmpfs; keep all temporary state under a writable
# mktemp dir (never inside the worktree). shunit2 honours TMPDIR.
export TMPDIR="$WORK/tmp"

command -v timeout > /dev/null 2>&1 && HAVE_TIMEOUT=1 || HAVE_TIMEOUT=0

# ─────────────────────────────────────────────────────────────────────
# Section A — OHOS adaptation cases
# ─────────────────────────────────────────────────────────────────────
printf '%s\n' '=== Section A: OHOS adaptation cases ==='

# A1: bash dependency satisfies kw's >= 4.3 requirement
bash_version_line="$("$BASH_BIN" --version | head -n 1)"
bash_major="$(printf '%s' "$bash_version_line" | sed -E 's/^.*version ([0-9]+)\.([0-9]+).*$/\1/')"
bash_minor="$(printf '%s' "$bash_version_line" | sed -E 's/^.*version ([0-9]+)\.([0-9]+).*$/\2/')"
if printf '%s' "$bash_version_line" | grep -q 'bash'; then
  if [ "${bash_major:-0}" -gt 4 ] || { [ "${bash_major:-0}" -eq 4 ] && [ "${bash_minor:-0}" -ge 3 ]; }; then
    report_pass "ohos_bash_dependency_version ($bash_version_line)"
  else
    report_fail "ohos_bash_dependency_version (bash >= 4.3 required, got: $bash_version_line)"
  fi
else
  report_fail "ohos_bash_dependency_version (unrecognized bash --version output: $bash_version_line)"
fi

# A2: bash features kw relies on (namerefs, assoc arrays, mapfile)
"$BASH_BIN" -c '
  f() { local -n r="$1"; r="ok"; }
  v=""; f v
  [ "$v" = "ok" ] || exit 1
  declare -A m=([k]=1)
  [ "${m[k]}" = "1" ] || exit 1
  mapfile -t lines <<< "a
b"
  [ "${lines[1]}" = "b" ] || exit 1
'
check "ohos_bash_features_required_by_kw" 0 "$?"

# A3: entry point reachable via injected PATH with portable shebang (E049)
kw_path="$(command -v kw 2> /dev/null)"
if [ "$kw_path" = "${KW_PKG_ROOT}/bin/kw" ]; then
  report_pass "ohos_kw_entry_on_path ($kw_path)"
else
  report_fail "ohos_kw_entry_on_path (command -v kw -> ${kw_path:-nothing})"
fi
shebang="$(head -n 1 "${KW_PKG_ROOT}/bin/kw")"
if [ "$shebang" = '#!/usr/bin/env bash' ]; then
  report_pass "ohos_kw_entry_shebang_portable ($shebang)"
else
  report_fail "ohos_kw_entry_shebang_portable (got: $shebang)"
fi

# A4: packaged layout mirrors setup.sh install layout, VERSION regenerated
layout_ok=0
[ -f "${KW_PKG_ROOT}/lib/kw/lib/kwlib.sh" ] && layout_ok=$((layout_ok + 1))
[ -d "${KW_PKG_ROOT}/lib/kw/plugins" ] && layout_ok=$((layout_ok + 1))
[ -f "${KW_PKG_ROOT}/etc/kw/kworkflow.config" ] && layout_ok=$((layout_ok + 1))
[ -d "${KW_PKG_ROOT}/share/kw/sound" ] && layout_ok=$((layout_ok + 1))
[ -f "${KW_PKG_ROOT}/share/kw/database/kwdb.sql" ] && layout_ok=$((layout_ok + 1))
[ -f "${KW_PKG_ROOT}/share/bash-completion/completions/kw" ] && layout_ok=$((layout_ok + 1))
if [ "$layout_ok" -eq 6 ]; then
  report_pass "ohos_package_layout_invariants"
else
  report_fail "ohos_package_layout_invariants ($layout_ok/6 paths present)"
fi
pkg_version="$(head -n 1 "${KW_PKG_ROOT}/lib/kw/VERSION" 2> /dev/null)"
check "ohos_packaged_version_is_0.10 (got: $pkg_version)" 0 "$([ "$pkg_version" = "0.10" ] && echo 0 || echo 1)"

# A5: no CRLF and no machine-specific absolute paths baked into packaged
# scripts (comment lines are ignored — upstream comments may cite manual
# examples such as XDG docs)
crlf_hits="$(grep -rl "$(printf '\r')" "${KW_PKG_ROOT}/lib/kw" "${KW_PKG_ROOT}/bin" 2> /dev/null | head -3)"
abs_hits="$(grep -rnE '/storage/Users|/data/service|/data/data|/home/[a-zA-Z]' \
  "${KW_PKG_ROOT}/lib/kw" "${KW_PKG_ROOT}/bin" 2> /dev/null \
  | grep -vE ':[0-9]+:[[:space:]]*#' | head -3)"
if [ -z "$crlf_hits" ] && [ -z "$abs_hits" ]; then
  report_pass "ohos_no_crlf_no_absolute_paths"
else
  report_fail "ohos_no_crlf_no_absolute_paths (crlf: ${crlf_hits:-none}, abs: ${abs_hits:-none})"
fi

# A6: toybox portability patch present in exactly the files it touches
PATCHED_FILES=(
  'kw_env.sh'
  'transition_functions.sh'
  'backup.sh'
  'diff.sh'
  'kw_remote.sh'
  'lib/kwlib.sh'
  'lib/kw_string.sh'
  'explore.sh'
)
patch_bad=0
for rel in "${PATCHED_FILES[@]}"; do
  target="${KW_PKG_ROOT}/lib/kw/${rel}"
  grep -qE 'sort --dictionary-order|ln --symbolic|rm --recursive --force|diff --color=always|sed --in-place|tr --delete|base64 --wrap' "$target" && patch_bad=$((patch_bad + 1))
done
grep -q 'ln -sf' "${KW_PKG_ROOT}/lib/kw/kw_env.sh" || patch_bad=$((patch_bad + 1))
grep -q 'tr -d ' "${KW_PKG_ROOT}/lib/kw/lib/kw_string.sh" || patch_bad=$((patch_bad + 1))
check "ohos_toybox_longopts_patch_applied" 0 "$patch_bad"

# A7/A8: kw smoke — version and help through the real entry point.
# NOTE: upstream `kw --help` delegates to the man page (needs sphinx-built
# man, excluded from this package); `kw -h` prints the usage help text.
export KW_LIB_DIR="${KW_PKG_ROOT}/lib"
export XDG_CONFIG_HOME="${KW_PKG_ROOT}/etc"
export XDG_DATA_HOME="${KW_PKG_ROOT}/share"

kw_version="$(kw --version 2> /dev/null)"
if [ "$kw_version" = "0.10" ]; then
  report_pass "ohos_kw_smoke_version ($kw_version)"
else
  report_fail "ohos_kw_smoke_version (got: ${kw_version:-<empty>})"
fi

kw_help="$(kw -h 2> /dev/null | head -n 1)"
if printf '%s' "$kw_help" | grep -q '^Usage: kw'; then
  report_pass "ohos_kw_smoke_help ($kw_help)"
else
  report_fail "ohos_kw_smoke_help (got: ${kw_help:-<empty>})"
fi

# A9: kw smoke walking the mktemp path — `kw env --create/--use` exercises
# configuration parsing, `mktemp -d`, `mv` and the patched `ln -sf` on OHOS.
# Upstream create_new_env returns 22 when no kernel .config is discoverable,
# so seed one (then remove it: --use refuses to switch while .config exists).
SMOKE="$WORK/smoke_env"
mkdir -p "$SMOKE/.kw/envs"
cp "${KW_PKG_ROOT}/etc/kw/build.config" "$SMOKE/.kw/build.config"
cp "${KW_PKG_ROOT}/etc/kw/deploy.config" "$SMOKE/.kw/deploy.config"
cp "${KW_PKG_ROOT}/etc/kw/kworkflow.config" "$SMOKE/.kw/kworkflow.config"
cp "${KW_PKG_ROOT}/etc/kw/send_patch.config" "$SMOKE/.kw/send_patch.config"
cp "${KW_PKG_ROOT}/etc/kw/notification_template.config" "$SMOKE/.kw/notification.config"
cp "${KW_PKG_ROOT}/etc/kw/remote.config" "$SMOKE/.kw/remote.config"
cp "${KW_PKG_ROOT}/etc/kw/vm_template.config" "$SMOKE/.kw/vm.config"
cp "${TEST_SRC}/tests/unit/samples/std_kconfig.config" "$SMOKE/.config"

kw_env_out="$(cd "$SMOKE" && kw env --create ohos_env 2>&1)"
create_rc=$?
check "ohos_kw_smoke_env_create_mktemp_path" 0 "$create_rc"
rm -f "$SMOKE/.config"
if [ "$create_rc" -eq 0 ]; then
  kw_env_out="$(cd "$SMOKE" && kw env --use ohos_env 2>&1)"
  use_rc=$?
  check "ohos_kw_smoke_env_use" 0 "$use_rc"
  if [ "$use_rc" -eq 0 ]; then
    if [ -L "$SMOKE/.kw/kworkflow.config" ] && [ "$(cat "$SMOKE/.kw/env.current" 2> /dev/null)" = "ohos_env" ]; then
      report_pass "ohos_kw_smoke_env_use_symlink_state"
    else
      report_fail "ohos_kw_smoke_env_use_symlink_state (.kw/kworkflow.config not a symlink or env.current wrong)"
    fi
  else
    printf '%s\n' "$kw_env_out" | head -5 | sed 's/^/       /'
  fi
else
  printf '%s\n' "$kw_env_out" | head -5 | sed 's/^/       /'
  report_fail "ohos_kw_smoke_env_use (skipped, create failed)"
fi

# A10: kw's own shared-memory temp dir helper works on OHOS (mktemp probe)
REPO="$WORK/repo"
mkdir -p "$REPO/src" "$REPO/etc"
cp -r "${KW_PKG_ROOT}/lib/kw/." "$REPO/src/"
cp "${KW_PKG_ROOT}/bin/kw" "$REPO/kw"
cp -r "${KW_PKG_ROOT}/etc/kw/." "$REPO/etc/"
"$BASH_BIN" -c '
  set -u
  cd "'"$REPO"'" || exit 99
  export KW_LIB_DIR="$PWD/src"
  . ./src/lib/kw_include.sh --source-only
  export -f include
  include "./src/lib/kwlib.sh" || exit 98
  d="$(create_shared_memory_dir)" || exit 1
  [ -d "$d" ] || exit 1
  rm -rf "$d"
'
check "ohos_create_shared_memory_dir_mktemp" 0 "$?"

# ─────────────────────────────────────────────────────────────────────
# Section B — upstream unit-test subset (real upstream tests, vendored)
# ─────────────────────────────────────────────────────────────────────
printf '%s\n' '=== Section B: upstream unit tests (vendored subset of tag 0.10) ==='

cp -r "${TEST_SRC}/tests" "$REPO/tests"
# Upstream sample `tests/unit/samples/.config` is a dotfile; repo policy (JC5)
# forbids unregistered dotfiles under archives/, so it is vendored under a
# plain name and materialized at runtime for upstream utils.sh compatibility.
cp "$REPO/tests/unit/samples/std_kconfig.config" "$REPO/tests/unit/samples/.config"

# The three disk-boot-sector samples are vendored as single-line base64 text
# (first_set_of_bytes_from_disk_b64/): GitCode PR .diff exports carry no
# GIT binary patch data, so real binary blobs break buildbot's git apply
# ("missing binary patch data"). Materialize them at runtime, bit-identical
# to upstream (sha256-verified; see EXCLUDED-TESTS.md D5).
SAMPLES_B64="$REPO/tests/unit/samples/first_set_of_bytes_from_disk_b64"
SAMPLES_DISK="$REPO/tests/unit/samples/first_set_of_bytes_from_disk"
mkdir -p "$SAMPLES_DISK"
b64_count=0
b64_bad=0
for b64file in "$SAMPLES_B64"/*.b64; do
  [ -f "$b64file" ] || { b64_bad=1; continue; }
  b64_count=$((b64_count + 1))
  tr -d '\n' < "$b64file" | base64 -d > "$SAMPLES_DISK/$(basename "$b64file" .b64)" || b64_bad=1
done
if [ "$b64_count" -ne 3 ] || [ "$b64_bad" -ne 0 ]; then
  report_fail "ohos_b64_disk_samples_materialize (decoded=$b64_count, bad=$b64_bad)"
fi

UPSTREAM_TESTS=(
  'tests/unit/lib_tests/kw_string_test.sh'
  'tests/unit/lib_tests/kw_include_test.sh'
  'tests/unit/lib_tests/kwio_test.sh'
  'tests/unit/kw_test.sh'
  'tests/unit/kw_env_test.sh'
  'tests/unit/kw_remote_test.sh'
  'tests/unit/self_update_test.sh'
  'tests/unit/permissions_test.sh'
  'tests/unit/help_test.sh'
  'tests/unit/diff_test.sh'
  'tests/unit/explore_test.sh'
)

UP_PASS=0
UP_FAIL=0
for test_file in "${UPSTREAM_TESTS[@]}"; do
  test_name="$(basename "$test_file" .sh)"
  printf -- '--- upstream: %s ---\n' "$test_name"
  test_log="$WORK/${test_name}.log"
  (
    cd "$REPO" || exit 99
    unset KW_LIB_DIR KWORKFLOW
    # Mirrors upstream run_tests.sh: init_env + exported include() for the
    # child bash process running the test script.
    export KW_LIB_DIR="$PWD/src"
    export KWORKFLOW='.kw'
    export LANGUAGE='en_US.UTF-8'
    . ./src/lib/kw_include.sh --source-only
    export -f include
    if [ "$HAVE_TIMEOUT" -eq 1 ]; then
      timeout 240 bash "./$test_file"
    else
      bash "./$test_file"
    fi
  ) > "$test_log" 2>&1
  test_rc=$?
  if [ "$test_rc" -eq 0 ]; then
    printf 'UPSTREAM %s PASS\n' "$test_name"
    UP_PASS=$((UP_PASS + 1))
    tail -n 1 "$test_log" | sed 's/^/    /'
  else
    printf 'UPSTREAM %s FAIL (rc=%s)\n' "$test_name" "$test_rc"
    UP_FAIL=$((UP_FAIL + 1))
    grep -E 'FAILED|failed|ASSERT|not ok|Ran [0-9]+' "$test_log" | head -6 | sed 's/^/    /'
  fi
done

printf '%s\n' '=== Summary ==='
printf 'OHOS_CASES:   pass=%s fail=%s\n' "$PASS" "$FAIL"
printf 'UPSTREAM_SUMMARY: pass=%s fail=%s total=%s\n' "$UP_PASS" "$UP_FAIL" "${#UPSTREAM_TESTS[@]}"

TOTAL_FAIL=$((FAIL + UP_FAIL))
if [ "$TOTAL_FAIL" -gt 0 ]; then
  printf 'OVERALL_RESULT: FAIL (%s failed)\n' "$TOTAL_FAIL"
  [ "$FAIL" -gt 0 ] && printf 'failed OHOS cases:%s\n' "$FAILED_CASES"
  exit 1
fi
printf 'OVERALL_RESULT: PASS\n'
exit 0
