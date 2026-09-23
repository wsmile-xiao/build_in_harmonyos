"""Conan recipe — bootp 2.4.3 (BOOTP server daemon)"""
from conan import ConanFile
from conan.tools.files import get, copy
import os


class BootpConan(ConanFile):
    name = "bootp"
    version = "2.4.3"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    license = "BSD-3-Clause"
    description = "Server for the BOOTP protocol with DHCP support"
    url = "https://packages.debian.org/bootp"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # musl/OHOS: extern int errno → #include <errno.h>
        self.run(
            "sed -i 's/extern int errno;/#include <errno.h>/' report.c",
            cwd=self.source_folder)
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "cc")
        cflags = "-O2 -Wno-error=implicit-function-declaration -Wno-error=implicit-int -Wno-error=int-conversion -Wno-error=deprecated-non-prototype -Wno-error=return-type -Wno-error=incompatible-function-pointer-types"
        progs = "bootpd bootpef bootpgw"
        self.run(f"make CC={cc} SYSDEFS=\"{cflags}\" {progs}", cwd=self.source_folder)

    def package(self):
        copy(self, "bootpd", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "bootpef", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "bootpgw", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "bootptest", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.5", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man5"))
        copy(self, "*.8", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man8"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
