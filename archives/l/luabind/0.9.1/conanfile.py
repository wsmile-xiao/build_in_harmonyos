#!/usr/bin/env python3
"""Conan recipe for luabind 0.9.1 — a C++ library that helps you create
bindings between C++ and Lua.

Build: upstream uses Boost.Build (bjam) with Jamroot; for OHOS we compile
src/*.cpp directly with the toolchain-provided clang++ (R33: compiler from
Conan conf, never bare shell env vars) and package the static library plus
public headers.

Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuabindConan(ConanFile):
    name = "luabind"
    version = "0.9.1"
    description = "luabind — a library that helps you create bindings between C++ and Lua"
    license = "MIT"
    homepage = "https://github.com/ValyriaTear/luabind"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.1.5")
        self.requires("boost/1.90.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"luabind requires os=Linux or os=OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: resolve toolchain compilers from Conan conf (never shell env).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++")

        src = self.source_folder
        lua = self.dependencies["lua"]
        boost = self.dependencies["boost"]

        include_dirs = [
            src,
            os.path.join(lua.package_folder, "include"),
            os.path.join(boost.package_folder, "include"),
        ]
        cppflags = " ".join(
            ["-O2", "-fPIC", "-std=c++11", "-DBOOST_BIND_GLOBAL_PLACEHOLDERS"]
            + ["-I" + d for d in include_dirs]
        )

        objs = []
        for f in sorted(os.listdir(os.path.join(src, "src"))):
            if f.endswith(".cpp"):
                obj = os.path.join(self.build_folder, f.replace(".cpp", ".o"))
                self.run(
                    f"{cxx} -c {cppflags} {os.path.join(src, 'src', f)} -o {obj}",
                    cwd=src,
                )
                objs.append(obj)

        # Static archive follows upstream name: libluabind.a
        ar = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get(
            "ar", "llvm-ar"
        )
        self.run(
            f"{ar} rcs {os.path.join(self.build_folder, 'libluabind.a')} {' '.join(objs)}",
            cwd=src,
        )

    def package(self):
        copy(self, "libluabind.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "*.hpp",
            os.path.join(self.source_folder, "luabind"),
            os.path.join(self.package_folder, "include", "luabind"),
        )
        copy(
            self,
            "*",
            os.path.join(self.source_folder, "luabind", "detail"),
            os.path.join(self.package_folder, "include", "luabind", "detail"),
        )
        copy(
            self,
            "*.hpp",
            os.path.join(self.source_folder, "luabind", "detail", "policy"),
            os.path.join(self.package_folder, "include", "luabind", "detail", "policy"),
        )
        copy(
            self,
            "*.hpp",
            os.path.join(self.source_folder, "luabind", "detail", "conversion_storage"),
            os.path.join(self.package_folder, "include", "luabind", "detail", "conversion_storage"),
        )

    def package_info(self):
        self.cpp_info.libs = ["luabind"]
        self.cpp_info.system_libs = ["dl", "m"]
        self.cpp_info.defines = ["BOOST_BIND_GLOBAL_PLACEHOLDERS"]
        self.cpp_info.requires = ["lua::lua", "boost::boost"]
        self.cpp_info.set_property("cmake_file_name", "luabind")
        self.cpp_info.set_property("cmake_target_name", "luabind::luabind")