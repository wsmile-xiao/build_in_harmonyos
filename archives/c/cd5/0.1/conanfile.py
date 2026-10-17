"""Conan recipe — cd5 0.1 (compute checksum of CD tracks, plain Makefile + libmhash)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy


class Cd5Conan(ConanFile):
    name = "cd5"
    version = "0.1"
    package_type = "application"
    license = "GPL-2.0"
    description = "Compute checksum of individual tracks on CD-ROMs"
    homepage = "https://packages.debian.org/cd5"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("mhash/0.9.9.9")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "cc")
        dep_libs = []
        dep_incs = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                dep_libs.append(os.path.join(pf, "lib"))
                dep_incs.append(os.path.join(pf, "include"))
        ldflags = " ".join(f"-L{d}" for d in dep_libs)
        inc_flags = " ".join(f"-I{d}" for d in dep_incs)
        self.run(
            f"make CC={cc} CFLAGS='-O2 -fPIC {inc_flags}' "
            f"LIBS='{ldflags} -lmhash'",
            cwd=self.source_folder)

    def package(self):
        copy(self, "cd5", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
