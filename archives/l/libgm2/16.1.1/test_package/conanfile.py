#!/usr/bin/env python3
"""Consumer test for the packaged libgm2 runtime libraries.

Compiles a real C program against the packaged libm2iso/libm2pim shared
libraries and the packaged libstdc++.a stub, then executes it and checks
the runtime API return values.  R34: genuine link + API call, no empty
shell.
"""

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


class Libgm2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_libgm2.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _sign_program(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "Running OHOS executables requires binary-sign-tool, "
                "llvm-objcopy and llvm-readelf"
            )
        elf_header = subprocess.run(
            [readelf, "-h", path], capture_output=True, text=True, check=True
        )
        if not re.search(r"Type:\s+(?:EXEC|DYN)\b", elf_header.stdout):
            raise ConanInvalidConfiguration(
                "libgm2 test output is not a runnable ELF file: {}".format(path)
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
                [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                 "-selfSign", "1"],
                check=True,
            )
            signed_header = subprocess.run(
                [readelf, "-h", signed],
                capture_output=True, text=True, check=True,
            )
            if not re.search(r"Type:\s+(?:EXEC|DYN)\b", signed_header.stdout):
                raise ConanInvalidConfiguration(
                    "Signing did not produce a runnable ELF: {}".format(path)
                )
            os.replace(signed, path)
            os.chmod(
                path,
                original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
            )

    @property
    def _libdir(self):
        dependency = self.dependencies["libgm2"]
        libdirs = dependency.cpp_info.libdirs
        if not libdirs:
            raise ConanInvalidConfiguration(
                "The libgm2 package does not declare a library directory"
            )
        return os.path.join(dependency.package_folder, libdirs[0])

    def build(self):
        source = os.path.join(self.source_folder, "test_libgm2.c")
        executable = os.path.join(self.build_folder, "libgm2_test_program")
        # --allow-shlib-undefined: the runtime .so files leave weak libc
        # symbols (e.g. __tzname) unresolved; GNU ld tolerates this while
        # LLD defaults to --no-allow-shlib-undefined.
        self.run(
            "clang -O2 -Wl,--allow-shlib-undefined "
            '-L"{}" -lm2iso -lm2pim -lstdc++ -lm '
            '"{}" -o "{}"'.format(self._libdir, source, executable),
            env="conanrun",
            ignore_errors=False,
        )
        self._sign_program(executable)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: libgm2 link test completed; execution skipped"
            )
            return
        executable = os.path.join(self.build_folder, "libgm2_test_program")
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The libgm2 test executable was not found: {}".format(executable)
            )
        self.run(
            "LD_LIBRARY_PATH={} {}".format(
                shlex.quote(self._libdir), shlex.quote(executable)
            ),
            env="conanrun",
            ignore_errors=False,
        )
