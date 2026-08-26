#!/usr/bin/env python3
"""Conan recipe for Parson 1.5.3."""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ParsonConan(ConanFile):
    name = "parson"
    version = "1.5.3"
    description = "Lightweight JSON library written in C"
    license = "MIT"
    homepage = "https://github.com/kgabis/parson"
    url = "https://github.com/kgabis/parson"
    topics = ("json", "parser", "c", "c89")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "parson 1.5.3 currently supports only OHOS armv8"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compiler = self._compiler("c")
        cxx = self._compiler("cpp")
        archiver = self._archiver(compiler)
        source = Path(self.source_folder)
        build = Path(self.build_folder)
        build.mkdir(parents=True, exist_ok=True)

        object_file = build / "parson.o"
        subprocess.run(
            [compiler, "-O2", "-fPIC", "-std=c89", "-c",
             str(source / "parson.c"), "-o", str(object_file)],
            check=True,
        )
        subprocess.run(
            [archiver, "rcs", str(build / "libparson.a"), str(object_file)],
            check=True,
        )

        common = ["-O0", "-g", "-Wall", "-Wextra", "-DTESTS_MAIN"]
        tests = (
            ("test", compiler, ["-std=c89", "-pedantic-errors", "-Wno-long-long"]),
            ("testcpp", cxx, []),
            ("test_hash_collisions", compiler,
             ["-std=c89", "-pedantic-errors", "-Wno-long-long",
              "-DPARSON_FORCE_HASH_COLLISIONS"]),
        )
        for name, executable, extra in tests:
            output = build / name
            subprocess.run(
                [executable, *common, *extra, str(source / "tests.c"),
                 str(source / "parson.c"), "-o", str(output)],
                check=True,
            )
            self._sign(output)
            self.run(f'"{output}" "{source / "tests"}"')

    def package(self):
        copy(self, "parson.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libparson.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["parson"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "parson")
        self.cpp_info.set_property("cmake_target_name", "parson::parson")
        self.cpp_info.set_property("pkg_config_name", "parson")

    def _compiler(self, language):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get(language)
        if not compiler:
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables must define {language!r}"
            )
        return compiler

    @staticmethod
    def _archiver(compiler):
        compiler_dir = Path(compiler).resolve().parent
        for name in ("llvm-ar", "ar"):
            candidate = compiler_dir / name
            if candidate.is_file():
                return str(candidate)
        archiver = shutil.which("llvm-ar") or shutil.which("ar")
        if not archiver:
            raise ConanInvalidConfiguration("llvm-ar or ar is required")
        return archiver

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
