"""Conan recipe — cbmbasic 1.0 (Commodore BASIC V2, pure C, Makefile, no deps)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy


class CbmbasicConan(ConanFile):
    name = "cbmbasic"
    version = "1.0"
    package_type = "application"
    license = "BSD-2-Clause"
    description = "Commodore BASIC V2 as a scripting language"
    homepage = "https://github.com/mist64/cbmbasic"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "gcc")
        self.run(f"make CC={cc} CFLAGS='-O2 -Wall -fPIC'", cwd=self.source_folder)

    def package(self):
        copy(self, "cbmbasic", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
