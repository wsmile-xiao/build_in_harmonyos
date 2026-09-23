#!/usr/bin/env python3
"""Consumer tests for drogon 1.9.12."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class DrogonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OHOS: prepend the toolchain libc++ dir to the runtime library path
        # (loader must not resolve libc++_shared.so from unrelated paths).
        if self.settings.os == "OHOS":
            env = Environment()
            env.prepend_path("LD_LIBRARY_PATH", self._toolchain_libcxx_dir())
            env.vars(self, scope="run").save_script("drogon_test_libcxx_runenv")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Cross-built drogon consumers cannot run on this build host."
            )
            return

        if self.settings.os == "OHOS":
            self._sign_executables()
            # OHOS: /system/bin/sh (mksh) cannot load dynamically linked test
            # binaries; run ctest through CONFIG_SHELL bash.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            cmd = (
                f"cd {shlex.quote(self.build_folder)} && "
                "ctest --output-on-failure --no-tests=error"
            )
            self.run(shlex.join([bash, "-c", cmd]), env="conanrun")
        else:
            self.run(
                shlex.join(
                    [
                        "ctest",
                        "--test-dir",
                        self.build_folder,
                        "--output-on-failure",
                        "--no-tests=error",
                    ]
                ),
                env="conanrun",
            )

    def _toolchain_libcxx_dir(self):
        """Directory containing the toolchain-matching libc++_shared.so."""
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("cpp", "")
        compiler = os.path.realpath(compiler) if compiler else ""
        compiler_dir = os.path.dirname(compiler) if compiler else ""
        llvm_root = os.path.dirname(compiler_dir) if compiler_dir else ""
        candidates = []
        if llvm_root:
            candidates.extend(
                [
                    os.path.join(llvm_root, "lib", "aarch64-linux-ohos"),
                    os.path.join(llvm_root, "aarch64-linux-ohos", "lib"),
                    os.path.join(llvm_root, "lib"),
                ]
            )
        for cand in candidates:
            if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                return os.path.normpath(cand)
        return compiler_dir or "/data/service/hnp/bin"

    def _sign_executables(self):
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        paths = [
            os.path.join(self.cpp.build.bindirs[0], name + suffix)
            for name in ("test_drogon",)
        ]
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool"
            )
        for path in paths:
            self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(shlex.join([objcopy, "--remove-section", ".codesign", temporary]))
            self.run(shlex.join([signer, "sign", "-inFile", temporary, "-outFile", temporary, "-selfSign", "1"]))
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("cpp", "")
        compiler_dir = os.path.dirname(compiler)
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        # binary-sign-tool ships in <sdk>/toolchains/lib while the compiler is
        # in <sdk>/native/llvm/bin, so walk up from the resolved compiler path.
        probe = os.path.dirname(os.path.realpath(compiler)) if compiler else ""
        for _ in range(5):
            if not probe:
                break
            candidates.append(os.path.join(probe, "toolchains", "lib", name))
            candidates.append(os.path.join(probe, "toolchains", name))
            probe = os.path.dirname(probe)
        return next((path for path in candidates if path and os.path.isfile(path)), "")
