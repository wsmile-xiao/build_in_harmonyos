#!/usr/bin/env python3
"""Conan test_package for wraplinux — runs test.sh which invokes the binary."""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class WrapLinuxTestConan(ConanFile):
    """test_package for executable package — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        # Resolve the installed wraplinux binary by absolute path. Relying on
        # `env="conanrun"` alone to put the dependency bin/ on PATH is unreliable
        # for pure application packages on Conan 2.30 (VirtualRunEnv may not
        # inject it), and a bare `wraplinux` invocation then exits 127
        # (`command not found`) — which test.sh would misread as a wraplinux
        # failure. Mirror the proven adr-tools pattern: explicit PATH + absolute
        # path passed down to test.sh via WRAPLINUX_BIN.
        dep = self.dependencies["wraplinux"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        wrap_bin = os.path.join(bin_dir, "wraplinux")

        # Locate bash for OHOS (mksh cannot run ELF test scripts the way we need).
        bash_path = (
            os.environ.get("CONFIG_SHELL")
            or os.environ.get("SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        bash_dir = os.path.dirname(bash_path)
        full_path = f"{bin_dir}:{bash_dir}"

        # Conan 2.30 ConanFile.run() requires `env` to be a list of env *file
        # names* (e.g. "conanrun") or None — NOT a dict. Passing a dict raises
        # `AssertionError: env argument to ConanFile.run() should be a list`.
        # Inject PATH and WRAPLINUX_BIN inline as shell assignments prefixed to
        # the command, exactly like the adr-tools test_package does; env="conanrun"
        # still loads the generated VirtualRunEnv file.
        self.run(
            f'cd "{self.source_folder}" && '
            f'PATH="{full_path}:$PATH" '
            f'WRAPLINUX_BIN="{wrap_bin}" '
            f'"{bash_path}" test.sh',
            env="conanrun",
        )
