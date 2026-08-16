#!/usr/bin/env python3
"""Conan test_package — libwebsockets 4.3.5.1 consumer test.

L1: verify the installed package can be consumed: header include, link,
compile-time LWS_WITH_LIBUV macro, real libuv-integration API call, and
libuv transitive dependency resolution (offline, no external network).
"""
import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibwebsocketsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libwebsockets.h 会直接 #include <openssl/ssl.h>，libuv 集成 API
        # 需要 <uv.h>；把 openssl 与 libuv 作为 test_package 的直接依赖，
        # 让 CMakeDeps 为消费者生成完整的 config（与 4.3.5 test_package 一致）。
        self.requires("openssl/3.5.6")
        self.requires("libuv/1.52.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built libwebsockets consumers cannot run here.")
            return
        if self.settings.os == "OHOS":
            self._sign_executables()
        lws_lib_dir = os.path.join(
            self.dependencies["libwebsockets"].package_folder, "lib"
        )
        uv_lib_dir = os.path.join(self.dependencies["libuv"].package_folder, "lib")
        cmd = os.path.join(self.cpp.build.bindirs[0], "lws_consumer")
        self.run(
            "LD_LIBRARY_PATH={}:{}:$LD_LIBRARY_PATH {}".format(
                lws_lib_dir, uv_lib_dir, cmd
            )
        )

    def _sign_executables(self):
        paths = glob.glob(os.path.join(self.cpp.build.bindirs[0], "lws_consumer"))
        paths = [path for path in paths if os.path.isfile(path)]
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not paths or not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires built consumer, llvm-objcopy, and binary-sign-tool"
            )
        for path in paths:
            temporary = f"{path}.signing"
            original_mode = os.stat(path).st_mode
            try:
                shutil.copy2(path, temporary)
                self.run(self._shell_join([objcopy, "--remove-section", ".codesign", temporary]))
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
