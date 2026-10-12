#!/usr/bin/env python3
"""Conan recipe for smaz 0.0-git.2f62584 (antirez small-string compression)."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SmazConan(ConanFile):
    name = "smaz"
    version = "0.0-git.2f62584"
    description = "Smaz: a simple compression library suitable for very small strings"
    license = "BSD-3-Clause"
    homepage = "https://github.com/antirez/smaz"
    url = "https://github.com/antirez/smaz"
    topics = ("compression", "small-strings", "c99", "codebook")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "smaz currently supports only OHOS armv8 in this recipe"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c") or "clang"
        ar = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        source = Path(self.source_folder)
        build = Path(self.build_folder)
        build.mkdir(parents=True, exist_ok=True)

        common = (
            f'{shlex.quote(cc)} -std=c99 -Wall -pedantic -O2 '
            f'-I{shlex.quote(str(source))}'
        )
        obj = build / "smaz.o"
        library = build / "libsmaz.a"
        self.run(
            f'{common} -c {shlex.quote(str(source / "smaz.c"))} '
            f'-o {shlex.quote(str(obj))}',
            env="conanbuild",
        )
        self.run(
            f'{shlex.quote(ar)} rcs {shlex.quote(str(library))} '
            f'{shlex.quote(str(obj))}',
            env="conanbuild",
        )

        # Upstream test program, compiled from unmodified smaz.c + smaz_test.c.
        # The upstream Makefile invokes: gcc -o smaz_test -O2 -Wall -W -ansi
        # -pedantic smaz.c smaz_test.c.  -std=gnu99 replaces -ansi so the POSIX
        # random() declaration is visible; the test source itself is unchanged.
        test_executable = build / "smaz-test"
        self.run(
            f'{shlex.quote(cc)} -std=gnu99 -Wall -W -O2 '
            f'-I{shlex.quote(str(source))} '
            f'{shlex.quote(str(source / "smaz.c"))} '
            f'{shlex.quote(str(source / "smaz_test.c"))} '
            f'-o {shlex.quote(str(test_executable))}',
            env="conanbuild",
        )
        self._sign(test_executable)
        self.run(shlex.quote(str(test_executable)), env="conanrun")

    def package(self):
        copy(self, "libsmaz.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "smaz.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["smaz"]
        self.cpp_info.set_property("cmake_file_name", "smaz")
        self.cpp_info.set_property("cmake_target_name", "smaz::smaz")
        self.cpp_info.set_property("pkg_config_name", "smaz")

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
