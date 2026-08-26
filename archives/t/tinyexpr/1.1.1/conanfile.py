#!/usr/bin/env python3
"""Conan recipe for TinyExpr 1.1.1."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class TinyExprConan(ConanFile):
    name = "tinyexpr"
    version = "1.1.1"
    description = "Tiny recursive descent parser and evaluator for math expressions"
    license = "Zlib"
    homepage = "https://github.com/codeplea/tinyexpr"
    url = "https://github.com/codeplea/tinyexpr"
    topics = ("expression", "parser", "math", "c99")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "TinyExpr 1.1.1 currently supports only OHOS armv8"
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
            f'{shlex.quote(cc)} -std=c99 -Wall -Wshadow -O2 {cflags} '
            f'-I{shlex.quote(str(source))}'
        )
        self.run(
            f'{common} -c {shlex.quote(str(source / "tinyexpr.c"))} '
            f'-o {shlex.quote(str(build / "tinyexpr.o"))}',
            env="conanbuild",
        )
        self.run(
            f'{shlex.quote(ar)} rcs {shlex.quote(str(build / "libtinyexpr.a"))} '
            f'{shlex.quote(str(build / "tinyexpr.o"))}',
            env="conanbuild",
        )

        variants = (
            ("smoke", ""),
            ("smoke_pr", "-DTE_POW_FROM_RIGHT -DTE_NAT_LOG"),
        )
        for name, definitions in variants:
            executable = build / name
            self.run(
                f'{common} {definitions} {shlex.quote(str(source / "smoke.c"))} '
                f'{shlex.quote(str(source / "tinyexpr.c"))} -lm '
                f'-o {shlex.quote(str(executable))}',
                env="conanbuild",
            )
            self._sign(executable)
            self.run(shlex.quote(str(executable)), env="conanrun")

    def package(self):
        copy(self, "libtinyexpr.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "tinyexpr.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["tinyexpr"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "tinyexpr")
        self.cpp_info.set_property("cmake_target_name", "tinyexpr::tinyexpr")
        self.cpp_info.set_property("pkg_config_name", "tinyexpr")

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
