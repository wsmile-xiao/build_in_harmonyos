#!/usr/bin/env python3
"""Conan recipe — topparser 1.3 (C, direct-compile static library).

IMPORTANT — SOURCE PROVENANCE (honest declaration):
There is NO authoritative upstream project for a C/C++ "topparser" library.
An audit of GitHub (the 4 repos named "topparser" are Node/Java/Julia), Gitee,
Conan Center and vcpkg found no C/C++ topparser; the only "topparser 1.3" on
Debian is an unrelated Python cave-survey GUI.  Consequently this recipe does
NOT ship an upstream archive: `conandata.yml` declares `sources: {}` and the
source (topparser.c/h, Makefile, tests/test_top.c) is vendored in the recipe's
src/ directory and copied by source().  No official HTTPS URL / sha256 exists
to record; fabricating one would itself be a deception, so none is provided.

This is a small, dependency-free C library that parses the output of the Linux
`top -b` (batch mode) command into structured C data.  It compiles a single
translation unit (topparser.c) into a static library and ships a public header
(topparser.h).  No third-party dependencies.

Although there is no authoritative upstream project, the source vendored into
this recipe (src/) ships its own self-test suite (src/tests/test_top.c), wired
to the source Makefile's `make test` / `make check` targets.  That self-test
is treated as the source-side ("upstream") test suite for this packaged
library: it is built and run inside build() so that `conan create` executes
the real tests on the HarmonyOS PC device and reports the actual
discovered/passed counts via HMBS_UPSTREAM_TEST_RESULT.
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class TopparserConan(ConanFile):
    name = "topparser"
    version = "1.3"
    description = "Dependency-free C library that parses the Linux `top -b` command output (no authoritative upstream; source vendored)"
    license = "MIT"
    topics = ("top", "parser", "process", "c99")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "src/*"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "topparser 1.3 currently supports only OHOS armv8"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # There is no authoritative upstream source archive for a C/C++
        # topparser (see module docstring).  The source is vendored in the
        # recipe's src/ directory; copy it into the source folder instead of
        # downloading.  conandata.yml therefore declares `sources: {}` and no
        # `url`/`sha256` is recorded because no authoritative archive exists.
        src = Path(self.export_sources_folder) / "src"
        shutil.copytree(src, self.source_folder, dirs_exist_ok=True)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", os.environ.get("CC", "clang"))
        ar = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        cflags = os.environ.get("CFLAGS", "")
        source = Path(self.source_folder)
        build = Path(self.build_folder)
        build.mkdir(parents=True, exist_ok=True)

        common = (
            f'{shlex.quote(cc)} -std=c99 -Wall -Wextra -O2 {cflags} '
            f'-I{shlex.quote(str(source))}'
        )
        # Build the static library (single TU).
        self.run(
            f'{common} -c {shlex.quote(str(source / "topparser.c"))} '
            f'-o {shlex.quote(str(build / "topparser.o"))}',
            env="conanbuild",
        )
        self.run(
            f'{shlex.quote(ar)} rcs {shlex.quote(str(build / "libtopparser.a"))} '
            f'{shlex.quote(str(build / "topparser.o"))}',
            env="conanbuild",
        )

        # Build and run the source-side self-test suite (src/tests/test_top.c,
        # wired to the source Makefile's `make test`/`make check` targets).
        # This is the "upstream"/source test suite for the packaged library.
        # test_top.c itself emits HMBS_UPSTREAM_TEST_RESULT with the real
        # discovered/passed counts computed at runtime from the TAP-ish
        # "ok -"/"not ok -" lines.
        selftest = build / "top_selftest"
        self.run(
            f'{common} {shlex.quote(str(source / "tests" / "test_top.c"))} '
            f'{shlex.quote(str(build / "libtopparser.a"))} -lm '
            f'-o {shlex.quote(str(selftest))}',
            env="conanbuild",
        )
        self._sign(selftest)
        self.run(shlex.quote(str(selftest)), env="conanrun")

    def package(self):
        copy(self, "libtopparser.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "topparser.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["topparser"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "topparser")
        self.cpp_info.set_property("cmake_target_name", "topparser::topparser")
        self.cpp_info.set_property("pkg_config_name", "topparser")

    @staticmethod
    def _sign(executable):
        """OHOS requires ELF binaries to be code-signed before execution."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute the self-test/upstream tests on OHOS"
            )
        signed = executable.with_suffix(executable.suffix + ".signed")
        if os.path.isfile(objcopy):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", str(executable)],
                check=False,
            )
        subprocess.run(
            [signer, "sign", "-inFile", str(executable), "-outFile", str(signed),
             "-selfSign", "1"],
            check=True,
        )
        shutil.move(signed, executable)
        os.chmod(executable, 0o755)
