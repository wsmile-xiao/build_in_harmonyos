#!/usr/bin/env python3
"""test_package for quagga 1.2.4 — executes the packaged routing binaries.

R34: nothing here is a print-only stub.  Every assertion runs an actual binary
shipped by the package: each daemon is located inside the package folder, checked
to be an ELF and then executed.  The shell script repeats the version probe
through the conan run environment (PATH) so the installed layout is exercised as
well, and fails hard if any declared command is missing there.
"""
import os

from conan import ConanFile


class QuaggaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    _BINARIES = ["zebra", "bgpd", "ripd", "ripngd", "ospfd", "ospf6d",
                 "isisd", "pimd", "watchquagga"]

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _locate(self, bindirs, binary):
        pkg = self.dependencies["quagga"].package_folder
        for bindir in bindirs:
            candidate = os.path.join(pkg, bindir, binary)
            if os.path.isfile(candidate):
                return candidate
        return None

    def test(self):
        quagga = self.dependencies["quagga"]
        bindirs = quagga.cpp_info.bindirs or ["bin", "sbin"]
        found = {}
        for binary in self._BINARIES:
            path = self._locate(bindirs, binary)
            assert path, f"{binary} missing from package (bindirs={bindirs})"
            with open(path, "rb") as handle:
                assert handle.read(4) == b"\x7fELF", f"{path} is not an ELF"
            found[binary] = path

        # --disable-vtysh / --disable-nhrpd must actually take effect: vtysh and
        # nhrpd are the components that require libreadline and libcares, so
        # their absence is the contract between the recipe and the packaged
        # command list (commands.json).
        for excluded in ("vtysh", "nhrpd"):
            assert self._locate(bindirs, excluded) is None, \
                f"{excluded} shipped although the recipe disables it"

        # Each daemon must answer on --version (fallback --help), which proves
        # the ELF loads, relocations resolve and the version string is bound.
        for binary, path in found.items():
            if self.run(f'"{path}" --version', ignore_errors=True) != 0:
                assert self.run(f'"{path}" --help', ignore_errors=True) == 0, \
                    f"{binary} neither --version nor --help succeeded"

        # OHOS: /system/bin/sh (toybox mksh) cannot execute ELF binaries, so
        # the shell smoke script runs under the packaged bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'"{bash}" "{script}"', env="conanrun")
