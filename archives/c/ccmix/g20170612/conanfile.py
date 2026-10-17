"""Conan recipe — ccmix g20170612 (Westwood MIX format manipulator, C++ gmake + Crypto++)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy


class CcmixConan(ConanFile):
    name = "ccmix"
    version = "g20170612"
    package_type = "application"
    license = "GPL-2.0"
    description = "Westwood Studios MIX format file manipulator"
    homepage = "https://github.com/OmniBlade/ccmix"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("cryptopp/8.9.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = cc_execs.get("cpp", "g++")
        dep_libs = []
        dep_incs = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                dep_libs.append(os.path.join(pf, "lib"))
                dep_incs.append(os.path.join(pf, "include"))
        ldflags = " ".join(f"-L{d}" for d in dep_libs)
        inc_flags = " ".join(f"-I{d}" for d in dep_incs)
        # Direct compilation bypassing Makefile/CMake CC override issues
        self.run(f"mkdir -p build", cwd=self.source_folder)
        objs = []
        for cpp in ["mixid.cpp", "mix_db_gamedb.cpp", "mix_db_gmd.cpp",
                     "mix_db_lmd.cpp", "mix_file.cpp", "mix_header.cpp", "ccmix.cpp"]:
            obj = f"src/{cpp.replace('.cpp', '.o')}"
            self.run(
                f"{cxx} -c -O2 -fPIC -Wno-c++11-narrowing {inc_flags} -o {obj} src/{cpp}",
                cwd=self.source_folder)
            objs.append(obj)
        self.run(
            f"{cxx} {' '.join(objs)} -o build/ccmix {ldflags} -lcryptopp -lpthread",
            cwd=self.source_folder)
        # Also build gmdedit
        self.run(
            f"{cxx} -c -O2 -fPIC {inc_flags} -o src/gmdedit/gmdedit.o src/gmdedit/gmdedit.cpp",
            cwd=self.source_folder)
        self.run(
            f"{cxx} src/gmdedit/gmdedit.o src/mixid.o src/mix_db_gamedb.o src/mix_db_gmd.o "
            f"-o build/gmdedit {ldflags} -lcryptopp",
            cwd=self.source_folder)

    def package(self):
        copy(self, "ccmix", src=os.path.join(self.source_folder, "build"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "gmdedit", src=os.path.join(self.source_folder, "build"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
