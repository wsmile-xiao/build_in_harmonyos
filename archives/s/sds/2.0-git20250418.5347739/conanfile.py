#!/usr/bin/env python3
"""Conan recipe for SDS 2.0 snapshot 2025-04-18."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SdsConan(ConanFile):
    name = "sds"
    version = "2.0-git20250418.5347739"
    description = "Simple Dynamic Strings library for C"
    license = "BSD-2-Clause"
    homepage = "https://github.com/antirez/sds"
    url = "https://github.com/antirez/sds"
    topics = ("string", "dynamic-string", "binary-safe", "c99")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "SDS currently supports only OHOS armv8 in this recipe"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", os.environ.get("CC", "clang"))
        ar = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        cflags = os.environ.get("CFLAGS", "")
        source = Path(self.source_folder)
        build = Path(self.build_folder)
        build.mkdir(parents=True, exist_ok=True)

        common = (
            f'{shlex.quote(cc)} -std=c99 -Wall -pedantic -O2 {cflags} '
            f'-I{shlex.quote(str(source))}'
        )
        obj = build / "sds.o"
        library = build / "libsds.a"
        self.run(
            f'{common} -c {shlex.quote(str(source / "sds.c"))} '
            f'-o {shlex.quote(str(obj))}',
            env="conanbuild",
        )
        self.run(
            f'{shlex.quote(ar)} rcs {shlex.quote(str(library))} '
            f'{shlex.quote(str(obj))}',
            env="conanbuild",
        )

        test_executable = build / "sds-test"
        self.run(
            f'{common} -DSDS_TEST_MAIN {shlex.quote(str(source / "sds.c"))} '
            f'-o {shlex.quote(str(test_executable))}',
            env="conanbuild",
        )
        self._sign(test_executable)
        self.run(shlex.quote(str(test_executable)), env="conanrun")

    def package(self):
        copy(self, "libsds.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "sds.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "sdsalloc.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sds"]
        self.cpp_info.set_property("cmake_file_name", "sds")
        self.cpp_info.set_property("cmake_target_name", "sds::sds")
        self.cpp_info.set_property("pkg_config_name", "sds")

    @staticmethod
    def _sign(executable):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute upstream tests on OHOS"
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
