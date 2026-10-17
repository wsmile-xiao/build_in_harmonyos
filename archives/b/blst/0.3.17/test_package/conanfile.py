#!/usr/bin/env python3
"""Conan test_package for blst 0.3.17 on HarmonyOS PC.

Layer 1 (any host, incl. cross-build host): ohos_abi_check.py inspects the
    packaged artifacts instead of executing them - ELF64/AArch64, OHOS musl
    interpreter, .note.ohos.ident, no host RPATH/RUNPATH, NX/PIE/RELRO, and -
    specific to this package - that the AArch64 assembly routines really are
    inside libblst.a (blst_sha256_block_armv8, mul_mont_384, add_mod_384,
    ct_inverse_mod_384, sqr_mont_384, ...).  A portable-only build would fail
    this layer, which is exactly the property path C claims.

Layer 2 (can_run only): test_blst.c is compiled against the packaged headers
    and library and executed on the HarmonyOS worker.  It runs an RFC 9380
    hash-to-curve known-answer test taken from upstream's own vector file,
    a sign/verify round-trip, a negative verification case, and a G1
    compression round-trip.

This is a *consumer* suite.  Upstream's own tests live in bindings/go and
bindings/rust and are reported separately, never merged into this count.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run


class BlstTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"blst test supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _conf_tool(self, key, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(key, default)

    def test(self):
        pkg = self.dependencies["blst"].package_folder
        if not pkg:
            raise ConanException("blst package folder is not available")

        # ---- Layer 1: artifact/ABI inspection (host independent) --------
        checker = os.path.join(os.path.dirname(__file__), "ohos_abi_check.py")
        if not os.path.isfile(checker):
            raise ConanException(f"ohos_abi_check.py missing: {checker}")
        self.run(
            f'python3 "{checker}" --package "{pkg}" --source '
            f'"{os.path.dirname(os.path.dirname(__file__))}"',
            env="conanrun",
        )

        # ---- Layer 2: real execution on the target ----------------------
        if not can_run(self):
            self.output.info("cross-build host: skipping on-target execution")
            return

        cc = self._conf_tool("c", "clang")
        src = os.path.join(os.path.dirname(__file__), "test_blst.c")
        if not os.path.isfile(src):
            raise ConanException(f"test_blst.c missing: {src}")
        exe = os.path.join(self.build_folder, "test_blst")
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        self.run(
            f'{cc} -O2 -fno-builtin -I"{inc}" "{src}" -o "{exe}" '
            f'-L"{lib}" -lblst -lm',
            env="conanrun",
        )
        self.run(f'"{exe}"', env="conanrun")
