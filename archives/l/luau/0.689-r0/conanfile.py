#!/usr/bin/env python3
"""Conan recipe for luau 0.689."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class LuauConan(ConanFile):
    name = "luau"
    version = "0.689-r0"
    license = "MIT"
    author = "Roblox"
    url = "https://github.com/luau-lang/luau"
    description = "A fast, small, safe, gradually typed embeddable scripting language derived from Lua"
    topics = ("lua", "scripting", "language", "roblox")
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}
    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Luau declares these options before project(), so they must be passed
        # on the CMake command line rather than only through the toolchain file.
        tc.cache_variables["LUAU_BUILD_CLI"] = True
        tc.cache_variables["LUAU_BUILD_TESTS"] = can_run(self)
        tc.cache_variables["LUAU_BUILD_WEB"] = False
        tc.cache_variables["LUAU_WERROR"] = False
        tc.cache_variables["LUAU_STATIC_CRT"] = False
        tc.cache_variables["LUAU_EXTERN_C"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            for test_binary in ("Luau.UnitTest", "Luau.Conformance", "Luau.CLI.Test"):
                test_path = os.path.join(self.build_folder, test_binary)
                self.run(f'"{test_path}"', cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "Ast", "include"))
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "Compiler", "include"))
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "VM", "include"))
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "Analysis", "include"))
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "CodeGen", "include"))
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "Config", "include"))
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "EqSat", "include"))
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.source_folder, "Require", "include"))
        
        copy(self, "*.a", dst=os.path.join(self.package_folder, "lib"), src=self.build_folder, keep_path=False)
        
        for executable in (
            "luau",
            "luau-analyze",
            "luau-ast",
            "luau-bytecode",
            "luau-compile",
            "luau-reduce",
        ):
            copy(
                self,
                executable,
                dst=os.path.join(self.package_folder, "bin"),
                src=self.build_folder,
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = [
            "Luau.Analysis",
            "Luau.Ast",
            "Luau.CodeGen",
            "Luau.Compiler",
            "Luau.Config",
            "Luau.EqSat",
            "Luau.Require",
            "Luau.RequireNavigator",
            "Luau.VM"
        ]
        self.cpp_info.defines = ["LUAU_STATIC"]
        
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
