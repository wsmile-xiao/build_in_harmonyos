#!/usr/bin/env python3
"""Consumer test for the packaged GCC 9 C compiler."""

import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class GccTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_gcc.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @property
    def _gcc(self):
        dependency = self.dependencies["gcc"]
        bindirs = dependency.cpp_info.bindirs
        if not bindirs:
            raise ConanInvalidConfiguration(
                "The GCC package does not declare a binary directory"
            )
        executable = os.path.join(
            dependency.package_folder,
            bindirs[0],
            "gcc",
        )
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The packaged GCC executable was not found: {}".format(
                    executable
                )
            )
        return executable

    def _assert_lld_signed(self, path):
        """Assert the linked ELF carries the LLD .codesign section.

        The packaged driver bakes the OHOS SDK LLD (DEFAULT_LINKER), which
        signs every ELF it links.  A missing .codesign section means the
        toolchain silently regressed to an unsigned linker and the kernel
        would refuse to run the program, so fail loudly here.
        """
        if str(self.settings.os) != "OHOS":
            return
        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
        )
        if not readelf:
            raise ConanInvalidConfiguration(
                "The OHOS .codesign assertion requires llvm-readelf or readelf"
            )
        sections = subprocess.run(
            [readelf, "-S", path],
            capture_output=True,
            text=True,
            check=True,
        )
        if not re.search(r"\.codesign", sections.stdout):
            raise ConanInvalidConfiguration(
                "GCC-linked ELF has no .codesign section (unsigned linker "
                "regression): {}".format(path)
            )

    def build(self):
        # Explicitly propagate every compiler/test failure. Conan's
        # ignore_errors=False contract raises on non-zero exit status.
        self.run(
            '"{}" --version'.format(self._gcc),
            env="conanrun",
            ignore_errors=False,
        )
        define = "-DEXPECT_OHOS=1" if str(self.settings.os) == "OHOS" else ""
        source = os.path.join(self.source_folder, "test_gcc.c")
        executable = os.path.join(self.build_folder, "gcc_test_program")
        self.run(
            '"{}" -O2 {} "{}" -o "{}"'.format(
                self._gcc, define, source, executable
            ),
            env="conanrun",
            ignore_errors=False,
        )
        self._assert_lld_signed(executable)

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: GCC compile and link test completed; execution skipped")
            return
        executable = os.path.join(self.build_folder, "gcc_test_program")
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The GCC test executable was not found: {}".format(executable)
            )
        self.run(
            shlex.quote(executable),
            env="conanrun",
            ignore_errors=False,
        )
