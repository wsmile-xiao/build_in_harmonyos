#!/usr/bin/env python3
"""Consumer test for the packaged GCC 14 C compiler."""

import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class Gcc14TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_gcc.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @property
    def _gcc(self):
        dependency = self.dependencies["gcc-14"]
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

    def _sign_program(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "Running GCC output on OHOS requires binary-sign-tool, "
                "llvm-objcopy and llvm-readelf"
            )
        elf_header = subprocess.run(
            [readelf, "-h", path],
            capture_output=True,
            text=True,
            check=True,
        )
        if not re.search(r"Type:\s+(?:EXEC|DYN)\b", elf_header.stdout):
            raise ConanInvalidConfiguration(
                "GCC test output is not a runnable ELF file: {}".format(path)
            )
        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            os.chmod(temp_dir, 0o775)
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", unsigned],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    unsigned,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            signed_header = subprocess.run(
                [readelf, "-h", signed],
                capture_output=True,
                text=True,
                check=True,
            )
            if not re.search(
                r"Type:\s+(?:EXEC|DYN)\b", signed_header.stdout
            ):
                raise ConanInvalidConfiguration(
                    "Signing did not produce a runnable ELF: {}".format(path)
                )
            signed_sections = subprocess.run(
                [readelf, "-S", signed],
                capture_output=True,
                text=True,
                check=True,
            )
            if ".codesign" not in signed_sections.stdout:
                raise ConanInvalidConfiguration(
                    "Signing did not add .codesign: {}".format(path)
                )
            os.replace(signed, path)
            os.chmod(
                path,
                original_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
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
        self._sign_program(executable)

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
