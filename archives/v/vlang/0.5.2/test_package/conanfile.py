#!/usr/bin/env python3
"""Conan test package for vlang/0.5.2."""
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy

class VTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # The SDK lld on some CI workers cannot load its libxml2 runtime.
            # Keep CMake's compiler probes and test executable links on GNU ld.
            linker_flag = f"-fuse-ld={self._ohos_tool_path('ld.bfd')}"
            toolchain.extra_exelinkflags.append(linker_flag)
        toolchain.generate()

    def export_sources(self):
        copy(self, "test_v_language.v", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "test_v_metadata.cpp", src=self.recipe_folder, dst=self.export_sources_folder)

    def build(self):
        package_folder = self.dependencies["vlang"].package_folder
        is_windows = str(self.settings.os) == "Windows"
        v_exe = os.path.join(package_folder, "bin", "v.bat" if is_windows else "v")
        cmake = CMake(self)
        variables = {"VLANG_EXECUTABLE": v_exe}
        if str(self.settings.os) == "OHOS":
            variables["VLANG_LAUNCHER"] = "/system/bin/sh"
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        if can_run(self):
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_binary(Path(self.build_folder) / "test_v_metadata")
            self.run("ctest --output-on-failure", cwd=self.build_folder)

        if not can_run(self):
            self.output.info("Skipping runtime test because target binaries cannot run here")
            return

        package_folder = self.dependencies["vlang"].package_folder
        is_windows = str(self.settings.os) == "Windows"
        v_exe = os.path.join(package_folder, "bin", "v.bat" if is_windows else "v")
        vmodules = os.path.join(self.build_folder, "vmodules")
        os.makedirs(vmodules, exist_ok=True)
        os.environ["VMODULES"] = vmodules
        test_src = os.path.join(self.source_folder, "test_v_language.v")
        test_bin = os.path.join(self.build_folder, "test_v_language")
        test_cmd = f"{test_bin}.exe" if is_windows else test_bin
        v_cmd = f'"/system/bin/sh" "{v_exe}"' if str(self.settings.os) == "OHOS" else f'"{v_exe}"'
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "cc")

        self.run(f"{v_cmd} version", env="conanrun")
        self.run(f'{v_cmd} -gc none -cc "{cc}" -o "{test_bin}" "{test_src}"', env="conanrun")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_binary(Path(test_cmd))
        self.run(f'"{test_cmd}"', env="conanrun")

    def _sign_ohos_binary(self, binary_path):
        sign_tool = self._ohos_sign_tool()
        binary_path = Path(binary_path)
        if not binary_path.is_file():
            raise ConanException(f"OHOS test binary not found: {binary_path}")
        signed_path = binary_path.with_name(f"{binary_path.name}.signed")
        self.run(
            f'{sign_tool} sign -inFile "{binary_path}" '
            f'-outFile "{signed_path}" -selfSign 1 -signAlg SHA256withECDSA',
            quiet=True,
        )
        if not signed_path.is_file():
            raise ConanException(f"OHOS binary signing did not create {signed_path}")
        os.replace(signed_path, binary_path)
        os.chmod(binary_path, 0o755)

    def _ohos_sign_tool(self):
        sign_tool = self._ohos_tool_path("binary-sign-tool")
        if not os.path.isfile(sign_tool):
            raise ConanException(f"OHOS binary sign tool not found: {sign_tool}")
        return sign_tool

    def _ohos_tool_path(self, filename):
        tool_dir = self.conf.get("user.ohos:tool_dir", default=None)
        if tool_dir:
            return os.path.join(str(tool_dir), filename)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        if cc and os.path.isabs(str(cc)):
            return os.path.join(os.path.dirname(str(cc)), filename)

        raise ConanException(
            "OHOS tool directory not configured; set user.ohos:tool_dir or "
            "tools.build:compiler_executables['c'] to an absolute OHOS compiler path"
        )
