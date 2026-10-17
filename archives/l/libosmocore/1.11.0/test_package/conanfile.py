#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_package: 验证已安装的 libosmocore 可被消费者编译并运行（消费者视角验证）。"""

import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibosmocoreTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        # 平台注意：本环境 conan 的 self.run() 在 test_package 中不可用（SIGSEGV），
        # 改用 Python subprocess 直启可执行文件，并显式拼装依赖库搜索路径
        # （subprocess 不经过 conanrun 环境，见 notes.md）。
        libdirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                libdirs.append(libdir)
        env = os.environ.copy()
        old = env.get("LD_LIBRARY_PATH")
        env["LD_LIBRARY_PATH"] = ":".join(libdirs + ([old] if old else []))

        for exe in ("test_smoke", "test_ohos_tls"):
            path = os.path.join(self.build_folder, exe)
            if not os.path.isfile(path):
                found = glob.glob(os.path.join(self.build_folder, "**", exe), recursive=True)
                if not found:
                    raise ConanException("test executable not found: %s" % exe)
                path = found[0]
            self.output.info("running %s" % path)
            proc = subprocess.run([path], cwd=self.build_folder, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.output.info(proc.stdout.decode("utf-8", "replace"))
            if proc.returncode != 0:
                raise ConanException("%s failed (rc=%d)" % (exe, proc.returncode))
