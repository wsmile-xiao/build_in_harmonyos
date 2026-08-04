#!/usr/bin/env python3
"""Consumer tests for libevent 2.1.13."""

import glob
import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibeventTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        self._test_rpcgen()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built libevent consumers cannot run here.")
            return
        if self.settings.os == "OHOS":
            self._sign_executables()
        self.run(
            self._shell_join(
                ["ctest", "--output-on-failure", "--no-tests=error"]
            ),
            cwd=self.build_folder,
            env="conanrun",
        )

    def _sign_executables(self):
        paths = glob.glob(os.path.join(self.cpp.build.bindirs[0], "libevent_*"))
        paths = [path for path in paths if os.path.isfile(path)]
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not paths or not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires built consumers, llvm-objcopy, and binary-sign-tool"
            )
        for path in paths:
            temporary = f"{path}.signing"
            original_mode = os.stat(path).st_mode
            try:
                shutil.copy2(path, temporary)
                self.run(
                    self._shell_join(
                        [objcopy, "--remove-section", ".codesign", temporary]
                    )
                )
                self.run(
                    self._shell_join(
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
        compiler = compilers.get("c", "") or compilers.get("cpp", "")
        compiler_dir = os.path.dirname(compiler)
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _shell_join(self, arguments):
        arguments = [str(argument) for argument in arguments]
        if self.settings.os == "Windows":
            return subprocess.list2cmdline(arguments)
        return shlex.join(arguments)

    def _test_rpcgen(self):
        rpcgen = os.path.join(
            self.dependencies["libevent"].package_folder,
            "bin",
            "event_rpcgen.py",
        )
        rpc_input = os.path.join(self.source_folder, "rpcgen.rpc")
        generated_header = os.path.join(self.build_folder, "rpcgen.gen.h")
        generated_source = os.path.join(self.build_folder, "rpcgen.gen.c")
        os.makedirs(self.build_folder, exist_ok=True)
        process = subprocess.run(
            [
                sys.executable,
                rpcgen,
                "--quiet",
                rpc_input,
                generated_header,
                generated_source,
            ],
            cwd=self.build_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        generated = (generated_header, generated_source)
        if process.returncode or any(
            not os.path.isfile(path) or os.path.getsize(path) == 0
            for path in generated
        ):
            raise ConanException(
                f"event_rpcgen.py failed ({process.returncode}): {process.stderr}"
            )
        with open(generated_header, encoding="utf-8") as stream:
            header = stream.read()
        with open(generated_source, encoding="utf-8") as stream:
            source = stream.read()
        expected_header = (
            "struct ping *ping_new(void);",
            "int ping_payload_assign(struct ping *, const char *);",
        )
        expected_source = ('#include "rpcgen.gen.h"', "ping_new(void)")
        if any(value not in header for value in expected_header) or any(
            value not in source for value in expected_source
        ):
            raise ConanException("event_rpcgen.py generated unexpected output")
        self.output.info("event_rpcgen.py generated non-empty C and header outputs")
