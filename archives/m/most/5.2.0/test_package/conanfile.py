#!/usr/bin/env python3
"""Conan test_package — most 5.2.0

L1 test: verify the most binary is installed and can display help/version.
"""
import os

from conan import ConanFile


class MostTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # most links slang dynamically (-lslang). OHOS's dynamic loader does
        # not honor the rpath embedded at link time (-Wl,-R...), so the most
        # binary fails to start unless slang's lib dir is on LD_LIBRARY_PATH.
        # Pattern proven by espeak-ng 1.51 (status: built).
        slang = self.dependencies["slang"]
        slang_lib_dir = os.path.join(slang.package_folder, "lib")
        # most is installed to <pkg>/usr/bin/most (prefix=/usr). Although
        # package_info declares cpp_info.bindirs=["usr/bin"], VirtualRunEnv
        # may not have populated PATH yet at test time, so prepend it explicitly.
        most = self.dependencies["most"]
        most_bin_dir = os.path.join(most.package_folder, "usr", "bin")
        # HMBS injects SHELL=/bin/sh (toybox), so Conan runs test.sh via
        # /bin/sh regardless of the {bash} prefix. The script is written to
        # be POSIX/toybox-compatible (no `set -eu`) and emits the
        # HMBS_TEST_PACKAGE_RESULT marker itself. Export LD_LIBRARY_PATH and
        # PATH so the `most` invocations inside test.sh resolve and start.
        self.run(
            f'export LD_LIBRARY_PATH="{slang_lib_dir}"; '
            f'export PATH="{most_bin_dir}:$PATH"; '
            f'sh test.sh',
            env="conanrun",
        )