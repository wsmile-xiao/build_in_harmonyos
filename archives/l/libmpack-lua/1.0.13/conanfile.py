#!/usr/bin/env python3
"""Conan recipe for the libmpack Lua 5.1 native module."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LibmpackLuaConan(ConanFile):
    name = "libmpack-lua"
    version = "1.0.13"
    description = "Lua 5.1 binding for libmpack MessagePack serialization and RPC"
    license = "MIT"
    homepage = "https://github.com/libmpack/libmpack-lua"
    url = "https://github.com/libmpack/libmpack-lua"
    package_type = "shared-library"

    exports_sources = "test/upstream_runner.c", "test/upstream_runner.lua"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("lua/5.1.5")
        self.requires("libmpack/1.0.5")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libmpack-lua requires os=Linux or os=OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c", "clang")

    def _link_environment(self):
        env = Environment()
        if str(self.settings.os) == "OHOS":
            sdk_root = "/data/service/hnp/ohos-sdk.org"
            if os.path.isdir(sdk_root):
                for entry in sorted(os.listdir(sdk_root), reverse=True):
                    llvm_lib = os.path.join(
                        sdk_root, entry, "ohos", "native", "llvm", "lib"
                    )
                    if os.path.isdir(llvm_lib):
                        env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
                        break
        return env

    def _profile_flags(self, name):
        return [
            str(flag)
            for flag in (
                self.conf.get(name, default=[], check_type=list) or []
            )
        ]

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    @staticmethod
    def _include_flags(info):
        return [LibmpackLuaConan._quote("-I" + path) for path in info.includedirs]

    @staticmethod
    def _library_flags(info):
        flags = [LibmpackLuaConan._quote("-L" + path) for path in info.libdirs]
        flags.extend("-l" + name for name in info.libs)
        flags.extend("-l" + name for name in info.system_libs)
        return flags

    def _sign_ohos_executable(self, executable):
        """Sign the upstream-test runner before OHOS executes it."""
        if str(self.settings.os) != "OHOS" or not can_run(self):
            return executable

        objcopy_candidates = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy"),
        ]
        signer_candidates = [
            "/data/service/hnp/bin/binary-sign-tool",
            shutil.which("binary-sign-tool"),
        ]
        objcopy = next(
            (tool for tool in objcopy_candidates if tool and os.path.exists(tool)),
            None,
        )
        signer = next(
            (tool for tool in signer_candidates if tool and os.path.exists(tool)),
            None,
        )
        if not objcopy or not signer:
            raise ConanException(
                "OHOS upstream test runner requires llvm-objcopy and binary-sign-tool"
            )

        subprocess.run(
            [objcopy, "--remove-section", ".codesign", executable],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
        result = subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                executable,
                "-outFile",
                executable,
                "-selfSign",
                "1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
            text=True,
        )
        if result.returncode != 0:
            raise ConanException(
                "OHOS upstream test runner signing failed: " + result.stdout[-1000:]
            )
        return executable

    def build(self):
        lua = self.dependencies["lua"].cpp_info
        mpack = self.dependencies["libmpack"].cpp_info
        cc = self._compiler()
        common_flags = [
            "-std=c99",
            "-O2" if str(self.settings.build_type) == "Release" else "-O0",
            "-fPIC",
            "-Wall",
            "-Wextra",
            "-Wconversion",
            "-Wstrict-prototypes",
            "-Wno-unused-parameter",
            "-pedantic",
        ]
        profile_cflags = self._profile_flags("tools.build:cflags")
        profile_shared_flags = self._profile_flags("tools.build:sharedlinkflags")
        profile_exe_flags = self._profile_flags("tools.build:exelinkflags")

        module = os.path.join(self.build_folder, "mpack.so")
        module_command = " ".join(
            [
                self._quote(cc),
                "-shared",
                *common_flags,
                *profile_cflags,
                "-DMPACK_USE_SYSTEM",
                "-DMPACK_DEBUG_REGISTRY_LEAK",
                *self._include_flags(lua),
                *self._include_flags(mpack),
                self._quote(os.path.join(self.source_folder, "lmpack.c")),
                *self._library_flags(mpack),
                *profile_shared_flags,
                "-Wl,--allow-shlib-undefined",
                "-o",
                self._quote(module),
            ]
        )
        with self._link_environment().vars(self).apply():
            self.run(module_command)

        runner = os.path.join(self.build_folder, "upstream_runner")
        runner_source = os.path.join(
            self.export_sources_folder, "test", "upstream_runner.c"
        )
        runner_command = " ".join(
            [
                self._quote(cc),
                *common_flags,
                *profile_cflags,
                self._quote(runner_source),
                *self._include_flags(lua),
                *self._library_flags(lua),
                *profile_exe_flags,
                "-Wl,-E",
                "-ldl",
                "-lm",
                "-o",
                self._quote(runner),
            ]
        )
        with self._link_environment().vars(self).apply():
            self.run(runner_command)
        runner = self._sign_ohos_executable(runner)

        if can_run(self):
            runner_lua = os.path.join(
                self.export_sources_folder, "test", "upstream_runner.lua"
            )
            upstream_test = os.path.join(self.source_folder, "test.lua")
            command = " ".join(
                [
                    self._quote(runner),
                    self._quote(runner_lua),
                    self._quote(module),
                    self._quote(upstream_test),
                ]
            )
            with self._link_environment().vars(self).apply():
                self.run(command, cwd=self.source_folder)
        else:
            self.output.warning(
                "Cross-building detected: upstream test.lua was compiled into the "
                "recipe workflow but requires an OHOS/Linux runtime to execute"
            )

    def package(self):
        module_dir = os.path.join(self.package_folder, "lib", "lua", "5.1")
        copy(self, "mpack.so", src=self.build_folder, dst=module_dir)
        copy(self, "LICENSE-MIT", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        module = os.path.join(module_dir, "mpack.so")
        if not os.path.isfile(module):
            raise ConanException("expected package artifact missing: lib/lua/5.1/mpack.so")

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "libmpack-lua")
        module_dir = os.path.join(self.package_folder, "lib", "lua", "5.1")
        self.runenv_info.define(
            "LUA_CPATH", os.path.join(module_dir, "?.so") + ";;"
        )
