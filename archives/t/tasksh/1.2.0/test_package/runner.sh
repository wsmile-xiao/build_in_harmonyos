#!/usr/bin/env bash
# test_package/runner.sh — shared tasksh launcher for the test scripts.
#
# Sourced by test_tasksh.sh and test_ohos.sh, which must set TSH to the path of
# the packaged tasksh binary before sourcing.
#
# The packaged ELF is aarch64/OpenHarmony. Two execution models are supported
# and are told apart by the ELF header of the produced binary (NOT by Conan's
# cross_building(): the OHOS profiles pass the same file for -pr:h and -pr:b,
# so Conan reports host == build even when the ELF is foreign):
#
#   native  — the ELF matches the build host (the CI case: a HarmonyOS PC
#             aarch64 worker). exec it directly; TASKSH_RUNNER stays unset.
#   emulated— an x86_64 Linux box compiling for OHOS aarch64. exec it under
#             qemu-aarch64 against a guest sysroot that carries the OHOS musl
#             loader/libc, because the box's own /lib/ld-linux-aarch64.so.1
#             does not exist. TASKSH_CROSS_EMULATED=1 is exported in that case.
#
# Environment read from test_package/conanfile.py:
#   TASKSH_RUNNER         path to qemu-aarch64 (emulated model only)
#   TASKSH_GUEST_ROOT     guest sysroot root (passed to qemu -L)
#   TASKSH_GUEST_PRELOAD  guest-side fortify shim providing __fd_chk
#   TASKSH_CROSS_EMULATED "1" on the emulated model

# tsh_run [args...] — run tasksh, forwarding stdin and the exit status.
tsh_run() {
    if [ -z "${TASKSH_RUNNER:-}" ]; then
        "$TSH" "$@"
        return $?
    fi

    local qemu_args=(-L "$TASKSH_GUEST_ROOT"
                     -E "QEMU_LD_PREFIX=$TASKSH_GUEST_ROOT")
    if [ -n "${TASKSH_GUEST_PRELOAD:-}" ]; then
        # OHOS's <sys/select.h> injects __fd_chk() into FD_SET, but the guest
        # musl used for emulation does not implement it, so the binary would
        # die with "Error relocating ...: __fd_chk: symbol not found".
        # -E (not a plain LD_PRELOAD= on the command line) keeps the variable
        # out of qemu's own environment: an exported LD_PRELOAD would also hit
        # every host x86_64 child, which cannot load the aarch64 shim.
        qemu_args+=(-E "LD_PRELOAD=$TASKSH_GUEST_PRELOAD")
    fi

    # tasksh's own `exec`/`!` escapes and its delegation to Taskwarrior go
    # through popen(), so their children are plain host binaries that inherit
    # the guest LD_PRELOAD and each print one benign loader line. Strip that
    # one known line so it cannot be misread as a tasksh failure; a genuinely
    # broken shim still surfaces, because then tasksh itself dies with
    # "Error relocating ... __fd_chk: symbol not found", which is not filtered.
    "$TASKSH_RUNNER" "${qemu_args[@]}" "$TSH" "$@" 2>&1 |
        grep -v -F "from LD_PRELOAD cannot be preloaded"
    return "${PIPESTATUS[0]}"
}