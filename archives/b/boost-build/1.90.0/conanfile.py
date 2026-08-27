#!/usr/bin/env python3
"""Conan recipe — boost-build 1.90.0 (B2 Build System).

boost-build provides the B2 (formerly Boost.Build/bjam) build system.
Build: bootstrap.sh compiles the b2 engine (C++), then b2 install deploys.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BoostBuildConan(ConanFile):
    name = "boost-build"
    version = "1.90.0"
    description = "B2 (Boost.Build) — a declarative C++ build system"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/build/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"boost-build supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _libxml2_path(self):
        """Find libxml2 lib dir (lld linker depends on it on OHOS)."""
        base = "/data/service/hnp/libxml2.org"
        if os.path.isdir(base):
            for d in os.listdir(base):
                libdir = os.path.join(base, d, "lib")
                if os.path.isfile(os.path.join(libdir, "libxml2.so")):
                    return libdir
        return None

    def build(self):
        apply_conandata_patches(self)

        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cxx = comp.get("cpp", "clang++")
        src = self.source_folder

        # Ensure scripts are executable (conan source copy may lose +x)
        self.run(f"chmod +x bootstrap.sh src/engine/build.sh", env="conanbuild", cwd=src)

        # Fix: lld linker depends on libxml2 which may not be in default search path on CI
        libxml2_lib = self._libxml2_path()
        if libxml2_lib:
            old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = f"{libxml2_lib}:{old_ld}" if old_ld else libxml2_lib

        # Build b2 engine via bootstrap.sh
        self.run(
            f'./bootstrap.sh --cxx="{cxx}" --cxxflags="-fPIC -O2"',
            env="conanbuild",
            cwd=src,
        )

    def package(self):
        src = self.source_folder
        # b2 install doesn't support DESTDIR; use --prefix directly
        self.run(
            f'./b2 install --prefix={self.package_folder} toolset=clang',
            env="conanbuild",
            cwd=src,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
