#!/usr/bin/env python3
"""CMake consumer tests for the Boost 1.91.0.1.3 clang-include-graph component
contract (adds the Boost.Log/JSON runtime consumer boost_log_contract)."""

import inspect
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class BoostCompiledComponentsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executables = [
            os.path.join(self.cpp.build.bindirs[0], target + suffix)
            for target in (
                "boost_component_unit",
                "boost_redex_iostreams",
                "boost_atomic_contract",
                "boost_date_time_contract",
                "boost_graph_contract",
                "boost_multiprecision_contract",
                "boost_graph_upstream_disjoint_set",
                "boost_ohos_portability",
                "boost_log_contract",
            )
        ]
        if self.settings.os == "OHOS":
            self._sign_executables(executables)

        for executable in executables:
            self._run_fail_closed(
                f'"{executable}"',
                env="conanrun",
                cwd=self.build_folder,
            )

    def _run_fail_closed(self, command, **kwargs):
        parameters = inspect.signature(self.run).parameters
        if "ignore_errors" in parameters:
            kwargs["ignore_errors"] = False
        elif "check" in parameters:
            kwargs["check"] = True
        else:
            raise ConanInvalidConfiguration(
                "Unsupported ConanFile.run API: expected ignore_errors or check"
            )
        self.run(command, **kwargs)

    def _sign_executables(self, executables):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and "
                "binary-sign-tool"
            )

        for executable in executables:
            self._sign_elf_atomically(executable, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self._run_fail_closed(
                f'"{objcopy}" --remove-section .codesign "{temporary}"',
            )
            self._run_fail_closed(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1',
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")
