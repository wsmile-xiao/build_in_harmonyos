"""Conan recipe — cal 4.1 (enhanced unix cal, single C file, no deps)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy


class CalConan(ConanFile):
    name = "cal"
    version = "4.1"
    package_type = "application"
    license = "Public Domain"
    description = "Enhanced unix cal command with color and appointment support"
    homepage = "https://packages.debian.org/cal"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "gcc")
        self.run(
            f"{cc} -O2 -Wall -DUNIX -DUSE_REMINDER -o cal cal.c",
            cwd=os.path.join(self.source_folder, "src"))

    def package(self):
        copy(self, "cal", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
