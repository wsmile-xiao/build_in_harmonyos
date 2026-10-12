#!/usr/bin/env python3
"""Conan test_package for tasksh 1.2.0.

Runs the packaged `tasksh` ELF for real (R34):

  * test_tasksh.sh — functional tests driving the interactive REPL over a
    pipe: --version, the help table, `exec` / `!` shell escapes, the
    `diagnostics` report (which proves the static libreadline.a linked),
    delegation of arbitrary commands to Taskwarrior, and clean exit on
    EOF / exit / quit.
  * test_ohos.sh — HarmonyOS-specific assertions: EM_AARCH64/ELF64 triplet,
    PIE, DT_NEEDED closure inside the OHOS runtime, static-link proof, a
    real execution on the OpenHarmony target, and doc/license completeness.

`task` (Taskwarrior) is an optional second argument: when the caller puts the
task/2.6.2 binary on PATH the round-trip assertion runs, otherwise it is
skipped and T1-T7/T9-T18 still fully exercise tasksh.

Execution model
---------------
CI runs this on a real HarmonyOS PC worker, where the OHOS aarch64 ELF is
native: the scripts exec the binary directly and every assertion is strict.

On a host whose architecture differs from the packaged ELF (e.g. an x86_64
Linux dev box compiling for OHOS aarch64) the binary cannot be exec'd. The
decision is taken from the ELF header of the produced binary, NOT from
Conan's cross_building(): the OHOS profiles pass the same file for -pr:h and
-pr:b, so Conan reports host == build even though the ELF is foreign. In that
case the scripts launch it through qemu-aarch64 against an OHOS guest sysroot,
and TASKSH_CROSS_EMULATED=1 downgrades exactly two assertions — the
`param get const.ohos.fullname` platform-identity check (there is no real
OHOS `param` tool off-device) and the man-page/license install check (no need
to re-derive it under emulation). Every other assertion, including the
triplet / PIE / DT_NEEDED / static-link checks and the real execution, stays
strict in both models. Precedent: archives/a/array-hash/0.7.2,
archives/b/breeze-grub/6.7.2.
"""
import os
import platform
import shutil
import struct

from conan import ConanFile

# e_machine values from the ELF spec, restricted to what matters here.
_EM_AARCH64 = 0xB7
_EM_X86_64 = 0x3E

# Guest sysroots searched for the OHOS musl loader/libc when emulating.
_GUEST_ROOTS = ("/opt/ohos-guest",)
# Guest-side fortify shim: OHOS headers reference __fd_chk(), which the musl
# build used for emulation does not provide.
_GUEST_PRELOAD = "libfdchkshim.so"


def _elf_machine(path):
    """Return the ELF e_machine of `path`, or None if it is not an ELF."""
    with open(path, "rb") as handle:
        header = handle.read(20)
    if len(header) < 20 or header[:4] != b"\x7fELF":
        return None
    little_endian = header[5] == 1
    return struct.unpack("<H" if little_endian else ">H", header[18:20])[0]


def _host_machine():
    machine = platform.machine().lower()
    if machine in ("aarch64", "arm64"):
        return _EM_AARCH64
    if machine in ("x86_64", "amd64"):
        return _EM_X86_64
    return None


class TaskshTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _emulation_env(self, tasksh_bin):
        """Environment for executing a foreign-architecture tasksh ELF.

        Empty on the CI worker (the ELF is native there). On a cross-build host
        it names qemu-aarch64, the guest sysroot and the fortify shim, which
        test_package/runner.sh turns into the actual `qemu -L ... -E ...`
        command line. `cross_building()` is deliberately not consulted: the
        OHOS profiles pass the same file for -pr:h and -pr:b, so Conan sees
        host == build even though the ELF is aarch64 and the host is x86_64.
        """
        if _elf_machine(tasksh_bin) == _host_machine():
            return {}

        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            raise Exception(
                "the packaged tasksh ELF targets a foreign architecture and "
                "qemu-aarch64 is required to execute it under test")
        guest = next((root for root in _GUEST_ROOTS
                      if os.path.isdir(os.path.join(root, "lib"))), None)
        if guest is None:
            raise Exception(
                "the packaged tasksh ELF targets a foreign architecture and no "
                f"OHOS guest sysroot was found in {list(_GUEST_ROOTS)}")
        env = {"TASKSH_RUNNER": qemu,
               "TASKSH_GUEST_ROOT": guest,
               "TASKSH_CROSS_EMULATED": "1"}
        preload = os.path.join(guest, "lib", _GUEST_PRELOAD)
        if os.path.isfile(preload):
            env["TASKSH_GUEST_PRELOAD"] = preload
        return env

    def test(self):
        # The test logic itself is host shell: bash, readelf and grep all run
        # natively. Only the tasksh binary goes through the emulation prefix,
        # which is why the qemu command line is built inside runner.sh instead
        # of wrapping this interpreter.
        bash = shutil.which("bash") or "/bin/bash"
        tasksh_bin = os.path.join(
            self.dependencies["tasksh"].cpp_info.bindirs[0], "tasksh")

        # Taskwarrior is a runtime companion of tasksh, not a build dependency.
        # If it happens to be on PATH, hand it over for the round-trip test.
        task_bin = shutil.which("task")

        env = self._emulation_env(tasksh_bin)

        def q(s):
            return '"' + s.replace('"', '\\"') + '"'

        for script in ("test_tasksh.sh", "test_ohos.sh"):
            cmd = " ".join([q(bash),
                            q(os.path.join(self.source_folder, script)),
                            q(tasksh_bin)])
            if script == "test_tasksh.sh":
                cmd += " " + q(task_bin or "")
            if env:
                # ConanFile.run() has no env_append parameter; pass the
                # cross-emulation variables as a command prefix instead.
                env_prefix = " ".join(
                    f"{k}={q(v)}" for k, v in sorted(env.items()))
                cmd = f"{env_prefix} {cmd}"
            self.run(cmd, env="conanrun")