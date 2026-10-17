#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class OnednnTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            libdirs = []
            try:
                items = self.dependencies.host.items()
            except AttributeError:
                items = self.dependencies.items()
            for _, dep in items:
                base = getattr(dep, "package_folder", None) or ""
                for p in dep.cpp_info.libdirs:
                    if not os.path.isabs(p) and base:
                        p = os.path.join(base, p)
                    if os.path.isdir(p):
                        libdirs.append(p)
            ldpath = os.pathsep.join(dict.fromkeys(libdirs))
            exe = os.path.join(self.cpp.build.bindirs[0], "test_onednn")
            self.run(
                "env LD_LIBRARY_PATH=\"%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\" \"%s\""
                % (ldpath, exe),
                env="conanrun",
            )
