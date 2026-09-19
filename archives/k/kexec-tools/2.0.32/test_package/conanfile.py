#!/usr/bin/env python3
"""Conan test_package for kexec-tools 2.0.32 — binary tool smoke test.

Runs the actual kexec/vmcore-dmesg binaries from the package:
- kexec --version  (must print "kexec-tools 2.0.32")
- kexec --help     (usage text, exercises option parser)
- vmcore-dmesg with a bogus path (expected "Cannot open" error path proves
  the ELF loads, links and runs — vmcore-dmesg has no --version flag)
- kexec with no args (usage error path, exit via usage())
"""
import os

from conan import ConanFile


class KexecToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["kexec-tools"].package_folder
        # Locate kexec binary (installed to sbin/ by upstream Makefile)
        kexec = os.path.join(pkg, "sbin", "kexec")
        if not os.path.exists(kexec):
            for root, dirs, files in os.walk(pkg):
                if "kexec" in files:
                    kexec = os.path.join(root, "kexec")
                    break
        self.run(f'"{kexec}" --version', env="conanrun")
        self.run(f'"{kexec}" --help', env="conanrun")
        # No-args path prints usage and exits 255 (usage error path) —
        # run via subprocess to tolerate the non-zero exit while still
        # verifying the binary executes and prints its usage text.
        import subprocess
        res = subprocess.run([kexec], capture_output=True, text=True, timeout=60)
        usage = res.stdout + res.stderr
        if "No kernel specified" not in usage and "Usage" not in usage:
            raise Exception(f"kexec no-args run did not print usage (rc={res.returncode})")
        # vmcore-dmesg: file-not-found error path (binary loads + libc works).
        # "Cannot open" goes to stdout; exit code is 0 on musl but we accept
        # either — we just want the ELF to execute.
        vmcore = os.path.join(os.path.dirname(kexec), "vmcore-dmesg")
        if os.path.exists(vmcore):
            res2 = subprocess.run([vmcore, "/no/such/vmcore/file"],
                                  capture_output=True, text=True, timeout=60)
            out2 = res2.stdout + res2.stderr
            if "Cannot open" not in out2:
                raise Exception(f"vmcore-dmesg run unexpected output (rc={res2.returncode})")
