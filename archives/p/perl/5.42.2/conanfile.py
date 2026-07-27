import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class PerlConan(ConanFile):
    name = "perl"
    version = "5.42.2"
    description = "Perl programming language interpreter"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://www.perl.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("perl", "interpreter", "scripting")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Perl is supported on Linux and OHOS only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tools(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        toolchain_bin = os.path.dirname(cc)
        return (
            cc,
            compilers.get("ar") or os.path.join(toolchain_bin, "llvm-ar"),
            compilers.get("ranlib") or os.path.join(toolchain_bin, "llvm-ranlib"),
        )

    def build(self):
        cc, ar, ranlib = self._tools()
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        configure_args = [
            "-des",
            f"-Dprefix={self.package_folder}",
            f"-Dcc={cc}",
            f"-Dld={cc}",
            f"-Dar={ar}",
            f"-Dranlib={ranlib}",
            # The OHOS libc.so is a linker script. Perl's optional nm scan
            # cannot parse it and falls through to the unavailable `bld` tool.
            "-Uusenm",
            "-Duseshrplib=false",
            "-Dman1dir=none",
            "-Dman3dir=none",
        ]
        self.run(
            f'"{shell}" Configure {" ".join(configure_args)}',
            cwd=self.source_folder,
        )
        # Configure silently drops the root Makefile on OHOS although it
        # generates the other .SH outputs. Makefile.SH writes its result to
        # stdout, so redirect it to the expected file before building.
        self.run(
            f'if [ ! -f Makefile ]; then "{shell}" Makefile.SH > Makefile; fi; '
            'test -f Makefile',
            cwd=self.source_folder,
        )
        # OHOS does not support GNU make's jobserver FIFO implementation.
        self.run("make -j1", cwd=self.source_folder)
        self.run("make test", cwd=self.source_folder)

    def package(self):
        self.run("make install", cwd=self.source_folder)
        copy(self, "Artistic", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "Copying", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
