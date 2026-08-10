#!/usr/bin/env python3
"""Conan recipe for AdapterRemoval 2.3.4."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AdapterRemovalConan(ConanFile):
    name = "adapterremoval"
    version = "2.3.4"
    description = "Adapter trimming and merging tool for sequencing reads"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/MikkelSchubert/adapterremoval"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("zlib/1.3.2")
        self.requires("bzip2/1.0.8")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    @staticmethod
    def _quote(value):
        return shlex.quote(str(value).replace("\\", "/"))

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("cpp", "clang++")

    def _archiver(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "")
        cxx_dir = os.path.dirname(cxx)
        candidate = os.path.join(cxx_dir, "llvm-ar") if cxx_dir else "llvm-ar"
        return candidate if cxx_dir and os.path.exists(candidate) else "llvm-ar"

    def _dependency_flags(self):
        include_flags = []
        libdir_flags = []
        lib_flags = []
        for name in ("zlib", "bzip2"):
            cpp_info = self.dependencies[name].cpp_info
            include_flags.extend(f"-I{path}" for path in cpp_info.includedirs)
            libdir_flags.extend(f"-L{path}" for path in cpp_info.libdirs)
            lib_flags.extend(f"-l{lib}" for lib in cpp_info.libs)
            lib_flags.extend(f"-l{lib}" for lib in cpp_info.system_libs)
        return include_flags, libdir_flags, lib_flags

    def _conf_list(self, name):
        return [str(value) for value in self.conf.get(name, default=[], check_type=list)]

    def _make_arguments(self):
        include_flags, libdir_flags, lib_flags = self._dependency_flags()
        cxxflags = (
            ["-std=c++11", "-O2", "-DNDEBUG"]
            + include_flags
            + self._conf_list("tools.build:cxxflags")
        )
        ldflags = libdir_flags + self._conf_list("tools.build:exelinkflags")
        libraries = ["-pthread"] + libdir_flags + lib_flags
        assignments = {
            "CXX": self._compiler(),
            "AR": self._archiver(),
            "MKDIR": "mkdir -p",
            "QUIET_BUILD": "no",
            "COLOR_BUILD": "no",
            "CXXFLAGS": " ".join(cxxflags),
            "LDFLAGS": " ".join(ldflags),
            "LIBRARIES": " ".join(libraries),
        }
        return " ".join(f"{key}={self._quote(value)}" for key, value in assignments.items())

    def build(self):
        make_args = self._make_arguments()
        self.run(f"make -j1 {make_args}", cwd=self.source_folder, env="conanbuild")
        if can_run(self):
            self.run(f"make -j1 {make_args} test", cwd=self.source_folder, env="conanbuild")
        else:
            self.output.warning("Skipping upstream unit tests because target binaries cannot run")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "AdapterRemoval", os.path.join(self.source_folder, "build"), os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "AdapterRemoval.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "share", "adapterremoval"), keep_path=False)
        copy(self, "*", os.path.join(self.source_folder, "examples"), os.path.join(self.package_folder, "share", "adapterremoval", "examples"))
        exe = os.path.join(self.package_folder, "bin", "AdapterRemoval")
        if os.path.isfile(exe) and os.name != "nt":
            os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
