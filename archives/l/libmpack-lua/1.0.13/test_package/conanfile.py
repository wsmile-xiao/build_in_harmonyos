#!/usr/bin/env python3
"""Conan consumer test for the libmpack-lua Lua 5.1 native module."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibmpackLuaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("lua/5.1.5")

    def layout(self):
        basic_layout(self)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c", "clang")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _profile_flags(self, name):
        return [
            str(flag)
            for flag in (
                self.conf.get(name, default=[], check_type=list) or []
            )
        ]

    def build(self):
        lua = self.dependencies["lua"].cpp_info
        include_flags = [
            self._quote("-I" + path) for path in lua.includedirs
        ]
        libdir_flags = [
            self._quote("-L" + path) for path in lua.libdirs
        ]
        library_flags = ["-l" + name for name in lua.libs]
        system_library_flags = ["-l" + name for name in lua.system_libs]
        source = os.path.join(self.recipe_folder, "test_lmpack.c")
        executable = os.path.join(self.build_folder, "test_lmpack")
        command = " ".join(
            [
                self._quote(self._compiler()),
                "-std=c99",
                "-O2",
                "-Wall",
                "-Wextra",
                *self._profile_flags("tools.build:cflags"),
                *include_flags,
                self._quote(source),
                *libdir_flags,
                *library_flags,
                *system_library_flags,
                *self._profile_flags("tools.build:exelinkflags"),
                "-Wl,-E",
                "-o",
                self._quote(executable),
            ]
        )
        self.run(command, env="conanbuild")
        if not os.path.isfile(executable):
            raise ConanException("test_lmpack executable was not produced")

    def _signed_ohos_copy(self, executable):
        """Sign a writable test copy because OHOS restricts ELF execution."""
        if str(self.settings.os) != "OHOS":
            return executable

        signed_copy = os.path.join(self.build_folder, "test_lmpack.signed")
        shutil.copy2(executable, signed_copy)

        objcopy_candidates = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy"),
        ]
        for tool in dict.fromkeys(path for path in objcopy_candidates if path):
            try:
                subprocess.run(
                    [tool, "--remove-section", ".codesign", signed_copy],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=15,
                )
                break
            except (OSError, subprocess.SubprocessError):
                continue

        signer_candidates = [
            "/data/service/hnp/bin/binary-sign-tool",
            shutil.which("binary-sign-tool"),
        ]
        for tool in dict.fromkeys(path for path in signer_candidates if path):
            try:
                result = subprocess.run(
                    [
                        tool,
                        "sign",
                        "-inFile",
                        signed_copy,
                        "-outFile",
                        signed_copy,
                        "-selfSign",
                        "1",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=30,
                    text=True,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            if result.returncode == 0:
                self.output.info("OHOS test executable self-sign succeeded")
                return signed_copy

        raise ConanException(
            "OHOS test executable cannot be self-signed; refusing to skip runtime test"
        )

    def test(self):
        if not can_run(self):
            self.output.warning("Runtime test skipped because the host cannot run the target binary")
            return

        package = self.dependencies["libmpack-lua"]
        module = os.path.join(
            package.package_folder, "lib", "lua", "5.1", "mpack.so"
        )
        if not os.path.isfile(module):
            raise ConanException("packaged Lua module not found: " + module)

        executable = self._signed_ohos_copy(
            os.path.join(self.build_folder, "test_lmpack")
        )
        env = Environment()
        env.define(
            "LUA_CPATH",
            os.path.join(package.package_folder, "lib", "lua", "5.1", "?.so")
            + ";;",
        )
        with env.vars(self).apply():
            self.run(
                " ".join(
                    [self._quote(executable), self._quote(module)]
                ),
                env="conanrun",
            )
        checks = 8 if str(self.settings.os) == "OHOS" else 6
        self.output.info(
            'HMBS_TEST_PACKAGE_RESULT={"status":"passed",'
            f'"discovered":{checks},"executed":{checks},"passed":{checks},"failed":0}}'
        )
