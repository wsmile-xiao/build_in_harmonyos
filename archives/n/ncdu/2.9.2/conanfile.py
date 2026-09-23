#!/usr/bin/env python3
"""Conan recipe for ncdu 2.9.2."""

import glob
import os
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class NcduConan(ConanFile):
    name = "ncdu"
    version = "2.9.2"
    description = "NCurses Disk Usage analyzer, Zig implementation"
    license = "MIT"
    homepage = "https://dev.yorhel.nl/ncdu"
    url = "https://code.blicky.net/yorhel/ncdu"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    default_options = {
        "ncurses/*:shared": False,
        "zstd/*:shared": True,
    }

    def requirements(self):
        self.requires("ncurses/6.6")
        self.requires("zstd/1.5.7.1")

    def build_requirements(self):
        # ncdu 2.9.2 supports Zig 0.14 and 0.15. The matching OHOS tool
        # package must be adapted and published independently first.
        self.tool_requires("zig/0.15.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports native Linux/OHOS builds only"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _zig(self):
        package_folder = self.dependencies.build["zig"].package_folder
        executable = os.path.join(package_folder, "bin", "zig")
        if os.path.isfile(executable):
            return executable
        found = shutil.which("zig")
        if found:
            return found
        raise ConanInvalidConfiguration(
            "zig/0.15.2 is required but no zig executable was found"
        )

    def _dependency_prefix(self, name):
        package_folder = self.dependencies[name].package_folder
        if not package_folder or not os.path.isdir(package_folder):
            raise ConanInvalidConfiguration(
                f"{name} package folder is unavailable: {package_folder}"
            )
        return package_folder

    def _ohos_arch_include(self):
        if str(self.settings.os) != "OHOS":
            return None

        candidates = []
        configured = os.environ.get("OHOS_SYSROOT")
        if configured:
            candidates.append(configured)

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        compiler = (
            os.environ.get("CC")
            or executables.get("c")
            or shutil.which("clang")
        )
        if compiler:
            compiler = shlex.split(compiler)[0]
            try:
                result = subprocess.run(
                    [compiler, "--print-sysroot"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip():
                    candidates.append(result.stdout.strip())
            except (OSError, subprocess.CalledProcessError):
                pass

            compiler = os.path.realpath(compiler)
            candidates.append(
                os.path.normpath(
                    os.path.join(
                        os.path.dirname(compiler), "..", "..", "sysroot"
                    )
                )
            )

        candidates.extend(
            reversed(
                sorted(
                    glob.glob(
                        "/data/service/hnp/ohos-sdk.org/"
                        "ohos-sdk_*/ohos/native/sysroot"
                    )
                )
            )
        )

        for sysroot in candidates:
            include = os.path.join(
                sysroot, "usr", "include", "aarch64-linux-ohos"
            )
            if os.path.isfile(os.path.join(include, "bits", "alltypes.h")):
                return include

        raise ConanInvalidConfiguration(
            "OHOS architecture headers were not found under the compiler sysroot"
        )

    def _find_ohos_tool(self, env_name, command, fallback):
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.exists(configured):
                return configured
        found = shutil.which(command)
        if found:
            return found
        if os.path.exists(fallback):
            return fallback
        return None

    def _sign_ohos_executable(self, path):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._find_ohos_tool(
            "OHOS_LLVM_OBJCOPY",
            "llvm-objcopy",
            "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
        )
        signer = self._find_ohos_tool(
            "OHOS_BINARY_SIGN_TOOL",
            "binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
        )
        if objcopy:
            self.run(
                f'{shlex.quote(objcopy)} --remove-section .codesign '
                f'{shlex.quote(path)} 2>/dev/null || true'
            )
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to package ncdu on OHOS"
            )
        signed = f"{path}.signed"
        self.run(
            f'{shlex.quote(signer)} sign -inFile {shlex.quote(path)} '
            f'-outFile {shlex.quote(signed)} -selfSign 1'
        )
        shutil.move(signed, path)
        os.chmod(
            path,
            os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )

    def build(self):
        zig = self._zig()
        ncurses = self._dependency_prefix("ncurses")
        zstd = self._dependency_prefix("zstd")
        install_prefix = os.path.join(self.build_folder, "zig-out")
        global_cache = os.path.join(self.build_folder, "zig-global-cache")
        local_cache = os.path.join(self.build_folder, "zig-local-cache")
        for path in (install_prefix, global_cache, local_cache):
            os.makedirs(path, exist_ok=True)

        environment = Environment()
        environment.define_path("ZIG_GLOBAL_CACHE_DIR", global_cache)
        environment.define_path("ZIG_LOCAL_CACHE_DIR", local_cache)
        environment.define(
            "ZIG_OHOS_SIGN_ROOTS",
            " ".join((global_cache, local_cache, install_prefix)),
        )
        arch_include = self._ohos_arch_include()
        if arch_include:
            # Zig treats OHOS as native Linux, but its libc probe only keeps the
            # generic sysroot include directory. musl's bits/ headers live in
            # the target-specific directory and must precede it.
            environment.prepend_path("CPATH", arch_include)
        command = " ".join(
            (
                shlex.quote(zig),
                "build",
                "-j1",
                "--prefix",
                shlex.quote(install_prefix),
                "--search-prefix",
                shlex.quote(ncurses),
                "--search-prefix",
                shlex.quote(zstd),
                "-Doptimize=ReleaseFast",
                "-Dstrip=true",
            )
        )
        test_command = " ".join(
            (
                shlex.quote(zig),
                "build",
                "test",
                "-j1",
                "--search-prefix",
                shlex.quote(ncurses),
                "--search-prefix",
                shlex.quote(zstd),
            )
        )

        with environment.vars(self).apply():
            self.run(f"{shlex.quote(zig)} version", env="conanbuild")
            self.run(command, cwd=self.source_folder, env="conanbuild")
            self.run(test_command, cwd=self.source_folder, env="conanbuild")

        binary = os.path.join(install_prefix, "bin", "ncdu")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"zig build did not produce the expected binary: {binary}"
            )
        self._sign_ohos_executable(binary)

    def package(self):
        install_prefix = os.path.join(self.build_folder, "zig-out")
        copy(
            self,
            "ncdu",
            src=os.path.join(install_prefix, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "ncdu.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
