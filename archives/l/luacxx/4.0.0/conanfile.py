#!/usr/bin/env python3
"""Conan recipe for luacxx 4.0.0 on HarmonyOS.

luacxx is a C++ binding library for Lua (CMake build, C++20).  It depends on
Lua (lua/5.4.8) and its upstream test suite uses Boost.Test.
The OHOS Boost package does not compile libboost_unit_test_framework, so the
patches switch the upstream tests to the header-only Boost.Test entry point
and drop the unit_test_framework component requirement.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)

LUA_HPP = 'extern "C" {\n#include "lua.h"\n#include "lauxlib.h"\n#include "lualib.h"\n}\n'


class LuacxxConan(ConanFile):
    name = "luacxx"
    version = "4.0.0"
    description = "Lua binding library for modern C++"
    license = "MIT"
    homepage = "https://github.com/dafrito/luacxx"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "ohos_specific_test.cpp",
            src=os.path.join(self.recipe_folder, "tests"),
            dst=os.path.join(self.export_sources_folder, "tests"),
        )

    def requirements(self):
        self.requires("lua/5.4.8")

    def build_requirements(self):
        # Boost headers only: the upstream tests use Boost.Test, and the
        # OHOS boost package provides headers (the unit_test_framework
        # library is not built there).
        self.build_requires("boost/1.85.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # The lua conan package ships the C headers only; upstream sources
        # include the C++ wrapper <lua.hpp>, so build a merged include dir.
        lua = self.dependencies["lua"].cpp_info
        merged = os.path.join(self.build_folder, "lua-include")
        for header in os.listdir(lua.includedirs[0]):
            copy(
                self,
                header,
                src=lua.includedirs[0],
                dst=merged,
            )
        save(self, os.path.join(merged, "lua.hpp"), LUA_HPP)
        tc.cache_variables["LUA_INCLUDE_DIR"] = merged
        tc.cache_variables["LUA_LIBRARIES"] = os.path.join(
            lua.libdirs[0], "liblua.a"
        )
        tc.generate()

    def _compile_test(self, src_dir, merged, boost_include, lua_lib, sources, binary):
        """Compile a test binary against the just-built libluacxx.a."""
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        compiler = compiler_executables.get("cpp") or "c++"
        luacxx_lib = os.path.join(self.cpp.build.libdirs[0], "libluacxx.a")
        command = (
            f'"{compiler}" -std=c++20 -DLUACXX_AUTO_METATABLE '
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE "
            f"-I {src_dir}/include -I {merged} -isystem {boost_include} "
            f"{' '.join(sources)} "
            f"{luacxx_lib} {lua_lib} -ldl -lm "
            f"-o {binary}"
        )
        self.run(command)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

        # Run the upstream test suite against the built static library.
        # The OHOS Boost package provides headers only (no compiled
        # unit_test_framework), so the patched tests use the header-only
        # Boost.Test entry point and are compiled directly here.
        boost = self.dependencies.build["boost"]
        boost_include = os.path.join(boost.package_folder, "include")
        merged = os.path.join(self.build_folder, "lua-include")
        src_dir = self.source_folder
        lua_lib = os.path.join(
            self.dependencies["lua"].cpp_info.libdirs[0], "liblua.a"
        )
        bindir = self.cpp.build.bindirs[0]

        test_main = os.path.join(bindir, "luacxx_test_main")
        self._compile_test(
            src_dir, merged, boost_include, lua_lib,
            [
                os.path.join(src_dir, "tests", "main.cpp"),
                os.path.join(src_dir, "tests", "luacxx_convert_vector.cpp"),
            ],
            test_main,
        )
        self.run(f'"{test_main}" --log_level=test_suite', env="conanrun")

        test_without_conversion = os.path.join(bindir, "luacxx_test_without_conversion")
        self._compile_test(
            src_dir, merged, boost_include, lua_lib,
            [os.path.join(src_dir, "tests", "luacxx_without_conversions.cpp")],
            test_without_conversion,
        )
        self.run(f'"{test_without_conversion}" --log_level=test_suite', env="conanrun")

        # HarmonyOS-specific validation test (added in this adaptation).
        ohos_test = os.path.join(bindir, "ohos_specific_test")
        self._compile_test(
            src_dir, merged, boost_include, lua_lib,
            [
                os.path.join(src_dir, "tests", "ohos_specific_test.cpp"),
                os.path.join(src_dir, "src", "algorithm.cpp"),
                os.path.join(src_dir, "src", "log.cpp"),
                os.path.join(src_dir, "src", "error.cpp"),
                os.path.join(src_dir, "src", "reference.cpp"),
                os.path.join(src_dir, "src", "load.cpp"),
                os.path.join(src_dir, "src", "stack.cpp"),
                os.path.join(src_dir, "src", "thread.cpp"),
                os.path.join(src_dir, "src", "global.cpp"),
                os.path.join(src_dir, "src", "convert", "callable.cpp"),
                os.path.join(src_dir, "src", "convert", "const_char_p.cpp"),
                os.path.join(src_dir, "src", "convert", "char.cpp"),
                os.path.join(src_dir, "src", "convert", "numeric.cpp"),
            ],
            ohos_test,
        )
        self.run(f'"{ohos_test}"', env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The lua conan package lacks the C++ wrapper header; ship it with
        # luacxx so downstream consumers can include <luacxx/...> (which
        # includes <lua.hpp>) with only the public headers.
        save(
            self,
            os.path.join(self.package_folder, "include", "lua.hpp"),
            LUA_HPP,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["luacxx"]
        self.cpp_info.requires = ["lua::lua"]
        self.cpp_info.set_property("cmake_file_name", "luacxx")
        self.cpp_info.set_property("cmake_target_name", "luacxx::luacxx")