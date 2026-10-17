#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer assertions for the installed pgbackrest binary.
# Runs inside the ConanRunEnv (PATH contains the package bin/).
set -euo pipefail

BIN="$(command -v pgbackrest || true)"
if [ -z "${BIN}" ] || [ ! -x "${BIN}" ]; then
    echo "FAIL: pgbackrest binary not found on PATH"
    exit 1
fi
echo "[test] binary: ${BIN}"

failures=0
assert_ok() { echo "PASS: $*"; }
assert_no() { echo "FAIL: $*"; failures=$((failures + 1)); }

# ── C1: --version reports the adapted upstream version ───────────────────────
out="$("${BIN}" --version 2>&1 || true)"
case "${out}" in
    *"2.59.0"*) assert_ok "C1 --version -> ${out}" ;;
    *) assert_no "C1 --version unexpected output: ${out}" ;;
esac

# ── C2: version command ──────────────────────────────────────────────────────
out="$("${BIN}" version 2>&1 || true)"
case "${out}" in
    *"2.59.0"*) assert_ok "C2 version command" ;;
    *) assert_no "C2 version command unexpected output: ${out}" ;;
esac

# ── C3: --help lists the backup/restore commands ─────────────────────────────
help_out="$("${BIN}" --help 2>&1 || true)"
if printf '%s' "${help_out}" | grep -q "stanza-create" \
        && printf '%s' "${help_out}" | grep -q "backup" \
        && printf '%s' "${help_out}" | grep -q "restore"; then
    assert_ok "C3 --help lists commands"
else
    assert_no "C3 --help output unexpected"
fi

# ── C4: unknown option is rejected with a non-zero exit code ─────────────────
if "${BIN}" --this-option-does-not-exist version >/dev/null 2>&1; then
    assert_no "C4 invalid option accepted"
else
    assert_ok "C4 invalid option rejected"
fi

# ── H1: target data model — ELF64, little-endian, AArch64 ────────────────────
hdr="$(readelf -h "${BIN}" 2>&1 || true)"
if printf '%s' "${hdr}" | grep -q "AArch64" \
        && printf '%s' "${hdr}" | grep -q "ELF64" \
        && printf '%s' "${hdr}" | grep -q "little endian"; then
    assert_ok "H1 ELF64 little-endian AArch64"
else
    assert_no "H1 unexpected ELF header"
fi

# Dynamic section, read once and shared by H2 and P2.
dyn="$(readelf -d "${BIN}" 2>&1 || true)"
dyn_needed="$(printf '%s' "${dyn}" | grep "NEEDED" || true)"

# ── H2: musl runtime — the dynamic dependencies reference musl libc ──────────
if printf '%s' "${dyn_needed}" | grep -q "libc.so" \
        && ! printf '%s' "${dyn_needed}" | grep -q "libc.so.6"; then
    assert_ok "H2 musl runtime (libc.so, no glibc libc.so.6)"
else
    assert_no "H2 musl runtime not detected: ${dyn_needed:-<no NEEDED entries>}"
fi

# ── P1: HarmonyOS PC ELF signature section ───────────────────────────────────
if readelf -S "${BIN}" 2>&1 | grep -q "\.codesign"; then
    assert_ok "P1 .codesign section present"
else
    assert_no "P1 .codesign section missing"
fi

# ── P2: no build-host RPATH/RUNPATH leaked into the binary ───────────────────
if [ -z "${dyn_needed}" ]; then
    assert_no "P2 cannot read the dynamic section"
elif printf '%s' "${dyn}" | grep -qE "\(RPATH\)|\(RUNPATH\)"; then
    assert_no "P2 RPATH/RUNPATH present: $(printf '%s' "${dyn}" | grep -E '\(RPATH\)|\(RUNPATH\)' || true)"
else
    assert_ok "P2 no RPATH/RUNPATH"
fi

if [ "${failures}" -ne 0 ]; then
    echo "FAILED: ${failures} assertion(s)"
    exit 1
fi

echo "OK: all consumer assertions passed"
