#!/usr/bin/env python3
"""Conan recipe for minizign 0.1.13."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MinizignConan(ConanFile):
    name = "minizign"
    version = "0.1.13"
    description = "Zig implementation of Minisign"
    license = "ISC"
    homepage = "https://github.com/jedisct1/zig-minisign"
    url = "https://github.com/jedisct1/zig-minisign"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("zig/0.16.0.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is currently prepared for Linux/OHOS native builds"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        zig_clap = os.path.join(self.source_folder, "deps", "zig-clap")
        os.makedirs(zig_clap, exist_ok=True)
        get(self, **self.conan_data["zig_clap"], destination=zig_clap, strip_root=True)
        apply_conandata_patches(self)

    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    def _sign_elf(self, binary):
        sign_tool = self._find_ohos_tool(
            "OHOS_BINARY_SIGN_TOOL",
            "binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
        )
        objcopy = self._find_ohos_tool(
            "OHOS_LLVM_OBJCOPY",
            "llvm-objcopy",
            "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
        )
        if objcopy:
            self.run(f'"{objcopy}" --remove-section .codesign "{binary}" || true')
        if not sign_tool:
            self.output.warning("binary-sign-tool not found; minizign may require manual signing on OHOS")
            return
        signed = f"{binary}.signed"
        self.run(
            f'"{sign_tool}" sign -inFile "{binary}" -outFile "{signed}" -selfSign 1'
        )
        shutil.move(signed, binary)
        os.chmod(binary, 0o755)

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

    def _zig(self):
        zig_pkg = self.dependencies.build["zig"].package_folder
        zig = os.path.join(zig_pkg, "bin", "zig")
        if os.path.exists(zig):
            return zig
        found = shutil.which("zig")
        if found:
            return found
        raise ConanInvalidConfiguration("zig/0.16.0.1 is required but no zig executable was found")

    def build(self):
        global_cache = os.path.join(self.build_folder, "zig-global-cache")
        local_cache = os.path.join(self.build_folder, "zig-local-cache")
        os.makedirs(global_cache, exist_ok=True)
        os.makedirs(local_cache, exist_ok=True)
        os.environ["ZIG_GLOBAL_CACHE_DIR"] = global_cache
        os.environ["ZIG_LOCAL_CACHE_DIR"] = local_cache
        os.environ["ZIG_OHOS_SIGN_ROOTS"] = " ".join(
            [global_cache, local_cache, os.path.join(self.source_folder, "zig-out")]
        )

        zig = self._zig()
        self.run(f'"{zig}" version', env="conanbuild")
        self.run(f'"{zig}" build -Doptimize=ReleaseSmall', cwd=self.source_folder, env="conanbuild")
        self.run(f'"{zig}" build test -Doptimize=ReleaseSmall', cwd=self.source_folder, env="conanbuild")

        binary = os.path.join(self.source_folder, "zig-out", "bin", "minizign")
        if self._is_ohos() and os.path.exists(binary):
            self._sign_elf(binary)

    def package(self):
        bin_dir = os.path.join(self.source_folder, "zig-out", "bin")
        copy(self, "minizign", src=bin_dir, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        packaged = os.path.join(self.package_folder, "bin", "minizign")
        if os.path.exists(packaged):
            os.chmod(packaged, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
