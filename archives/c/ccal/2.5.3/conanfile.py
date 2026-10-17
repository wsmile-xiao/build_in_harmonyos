"""Conan recipe — ccal 2.5.3 (Chinese calendar, C++ gmake, no external deps)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy


class CcalConan(ConanFile):
    name = "ccal"
    version = "2.5.3"
    package_type = "application"
    license = "GPL-2.0"
    description = "Console calendar with Chinese lunar calendar support"
    homepage = "https://ccal.chinesebay.com/ccal/"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = cc_execs.get("cpp", "g++")
        # Fix hardcoded CXX in Makefile
        self.run(f"sed -i 's|^CXX=.*|CXX={cxx}|' Makefile", cwd=self.source_folder)
        self.run(
            f"make CXXFLAGS='-O2 -fPIC -DUSE_YEARCACHE'",
            cwd=self.source_folder)

    def package(self):
        copy(self, "ccal", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
