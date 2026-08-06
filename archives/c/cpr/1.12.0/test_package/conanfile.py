#!/usr/bin/env python3
"""Conan test_package for cpr 1.12.0 — substantively exercises the cpr API.

The test program starts a minimal HTTP server on a localhost port and performs
a real cpr::Get request against it, asserting the HTTP status code and body.
This satisfies R34 (no empty-shell tests): the cpr library and libcurl backend
are actually exercised.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import save


class CprTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # cpr headers include <curl/curl.h> directly; make curl a direct test
        # requirement so CMakeDeps emits a full CURL config for the consumer.
        self.requires("curl/8.15.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            rules = os.path.join(
                self.generators_folder, "ohos-cmake-rules.cmake"
            )
            save(
                self,
                rules,
                "\n".join(
                    (
                        'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG '
                        '"-Wl,-rpath-link,")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                    )
                )
                + "\n",
            )
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
            tc.cache_variables["CMAKE_BUILD_RPATH"] = ";".join(
                self.dependencies["cpr"].cpp_info.libdirs
            )
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "cross-building: cpr consumer linked but cannot run on this host"
            )
            return
        if self.settings.os == "OHOS":
            self._sign_test_binary()
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_cpr"),
            env="conanrun",
        )

    def _sign_test_binary(self):
        """OHOS refuses to execute unsigned ELF. Sign test_cpr (and any
        libcpr.so in its build tree) before running the consumer test."""
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        paths = [
            os.path.join(self.cpp.build.bindirs[0], "test_cpr" + suffix),
        ]
        paths.extend(
            os.path.join(self.cpp.build.bindirs[0], name)
            for name in ("libcpr.so.1", "libcpr.so", "libcpr.so.1.12.0")
            if os.path.isfile(
                os.path.join(self.cpp.build.bindirs[0], name)
            )
        )
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and "
                "binary-sign-tool"
            )
        for path in paths:
            if os.path.isfile(path):
                self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(
                shlex.join(
                    [objcopy, "--remove-section", ".codesign", temporary]
                )
            )
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        temporary,
                        "-outFile",
                        temporary,
                        "-selfSign",
                        "1",
                    ]
                )
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
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")
