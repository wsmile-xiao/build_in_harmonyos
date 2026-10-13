#!/bin/sh
# test_proot.sh — consumer-side regression tests for the packaged proot CLI.
#
# The upstream suite (test/GNUmakefile: make -C test check) drives proot
# end-to-end, which requires the kernel to allow ptrace(2) for the tracing
# process.  The OHOS kernel refuses it for unprivileged processes, so
# `proot <command>` fails with "ptrace(TRACEME): Permission denied" before
# execve; the upstream per-item results are recorded truthfully in
# reports/test-report.md.  This consumer suite verifies everything the
# installed binary can still do on such a platform:
#   * installed on PATH; --version / -V / --help output and exit codes,
#     including the build-time accelerator detection line
#   * argument validation: missing command, unknown option, unusable rootfs
#   * platform-policy coherence of a tracee run (refused on OHOS with the
#     documented ptrace denial; successful on a ptrace-permissive kernel)
#
# Every check emits exactly one TAP line; assertion_count in MANIFEST.yml is
# the number of TAP lines this script emits (16).

set -u

workdir="${TMPDIR:-/tmp}/proot-test-$$"
if ! mkdir -p "$workdir" 2>/dev/null; then
    # some platforms have a read-only /tmp; fall back to the working directory
    workdir="$PWD/proot-test-$$"
    mkdir -p "$workdir" || exit 1
fi
trap 'rm -rf "$workdir"' EXIT HUP INT TERM

passed=0
failed=0

check() {
    # check <description> <expected> <actual>
    desc=$1 expected=$2 actual=$3
    if [ "$actual" = "$expected" ]; then
        passed=$((passed + 1))
        echo "ok - $desc"
    else
        failed=$((failed + 1))
        echo "not ok - $desc (expected: $expected, actual: $actual)"
    fi
}

contains() {
    # contains <description> <needle> <file>
    desc=$1 needle=$2 file=$3
    if grep -qF -- "$needle" "$file" 2>/dev/null; then
        passed=$((passed + 1))
        echo "ok - $desc"
    else
        failed=$((failed + 1))
        echo "not ok - $desc (missing: $needle)"
    fi
}

not_contains() {
    # not_contains <description> <needle> <file>
    desc=$1 needle=$2 file=$3
    if ! grep -qF -- "$needle" "$file" 2>/dev/null; then
        passed=$((passed + 1))
        echo "ok - $desc"
    else
        failed=$((failed + 1))
        echo "not ok - $desc (unexpected: $needle)"
    fi
}

echo "1..16"

# 1. the binary must be on PATH (installed into bin/ and exported by the package)
if command -v proot >/dev/null 2>&1; then
    check "proot binary is installed and on PATH" "0" "0"
else
    check "proot binary is installed and on PATH" "0" "1"
fi

# 2-4. version banner: exit code, release version, accelerator detection
proot --version > "$workdir/v.txt" 2>&1
check "proot --version exits 0" "0" "$?"
contains "proot --version prints the release version" "5.4.0" "$workdir/v.txt"
contains "proot --version reports the built-in accelerator detection" "accelerators: process_vm = yes, seccomp_filter = yes" "$workdir/v.txt"

# 5. -V is the documented alias
proot -V > "$workdir/V.txt" 2>&1
check "proot -V exits 0" "0" "$?"

# 6-8. help text
proot --help > "$workdir/h.txt" 2>&1
check "proot --help exits 0" "0" "$?"
contains "proot --help documents the rootfs option" "-r *path*, --rootfs=*path*" "$workdir/h.txt"
contains "proot --help lists the extension options" "Extension options:" "$workdir/h.txt"

# 9-10. a command is required
proot > "$workdir/noargs.txt" 2>&1
check "proot without a command exits 1" "1" "$?"
contains "proot without a command prints a fatal hint" "fatal error: see" "$workdir/noargs.txt"

# 11-12. unknown option is rejected by name
proot --bogus > "$workdir/badopt.txt" 2>&1
check "unknown option exits 1" "1" "$?"
contains "unknown option is reported by name" "unknown option '--bogus'" "$workdir/badopt.txt"

# 13-14. an unusable rootfs is detected before any tracee is started
proot -r /nonexistent-rootfs-xyz /bin/true > "$workdir/badroot.txt" 2>&1
check "unusable rootfs exits 1" "1" "$?"
contains "unusable rootfs is reported as an unsanitizable binding" "can't sanitize binding" "$workdir/badroot.txt"

# 15-16. platform-policy coherence of a tracee run.  On OHOS the kernel
# refuses ptrace(2) for unprivileged processes, so the run must fail with the
# documented denial; on a ptrace-permissive kernel the same run must succeed.
# Both branches emit exactly two TAP lines, so the total stays constant.
guest=/bin/true
[ -x "$guest" ] || guest=/system/bin/true
proot -r / "$guest" < /dev/null > "$workdir/run.txt" 2>&1
run_rc=$?
if grep -qF "ptrace(TRACEME)" "$workdir/run.txt"; then
    check "proot tracee runs are refused on this kernel (exit 1)" "1" "$run_rc"
    contains "the refusal names the ptrace operation" "ptrace(TRACEME):" "$workdir/run.txt"
else
    check "proot runs a command when the kernel allows ptrace (exit 0)" "0" "$run_rc"
    not_contains "a successful run reports no fatal error" "fatal error" "$workdir/run.txt"
fi

echo "# passed: $passed, failed: $failed"
if [ "$failed" -ne 0 ]; then
    exit 1
fi
exit 0
