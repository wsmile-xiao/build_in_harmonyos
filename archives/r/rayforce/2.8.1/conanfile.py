#!/usr/bin/env python3
"""Conan recipe — rayforce 2.8.1 (Makefile build, zero dependencies).

Rayforce is a pure C17 single-header embeddable engine. Upstream build is a
plain Makefile (`make release` builds the CLI, `make lib` builds librayforce.a).
Adaptation for OHOS: the upstream Makefile branch was inverted so non-Darwin
platforms (Linux *and* HarmonyOS, whose `uname -s` returns `HarmonyOS`) get
the generic `-lm -lpthread --gc-sections` flags instead of the macOS-only
`-Wl,-dead_strip` (see patches/).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RayforceConan(ConanFile):
    name = "rayforce"
    version = "2.8.1"
    description = "Rayforce: pure C zero-dependency columnar analytics + graph traversal engine"
    license = "MIT"
    homepage = "https://github.com/RayforceDB/rayforce"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Rayforce is deliberately zero-dependency (no malloc, no external libs)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler must come from Conan conf, never bare ${CC} (empty on CI).
        comps = self.conf.get("tools.build:compiler_executables", default={},
                              check_type=dict)
        cc = comps.get("c", "clang")
        cxx = comps.get("cpp", "clang++")
        ar = comps.get("ar", "llvm-ar")
        ranlib = comps.get("ranlib", "llvm-ranlib")

        # RAY_VERSION: the Makefile derives it from `git describe`; the tarball
        # has no .git, so inject the release version explicitly.
        makevars = (f"CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib} "
                    f"RAY_VERSION={self.version}")
        # Plain Makefile build: run from the source root (no configure step).
        self.run(f"make release {makevars} -j1", cwd=self.source_folder)
        self.run(f"make lib {makevars} -j1", cwd=self.source_folder)

    def package(self):
        # keep_path=False: 避免 pattern 中 "include/" 前缀被叠加, 将头文件
        # 干净地放入 <pkg>/include/rayforce.h (此前打在 include/include/ 下,
        # 导致 test_package 与 CMakeDeps 找不到头文件)
        copy(self, "include/*.h", self.source_folder,
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "librayforce.a", self.source_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "rayforce", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["rayforce"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]