#!/usr/bin/env python3
"""Conan test_package — librepo 1.20.0 (Conan L1 official test).

Consumer test: links librepo + glib, exercises the public API
(handle/result lifecycle, URL round-trip, SHA256 checksum) and expects
"LIBREPO_CONSUMER_OK" on stdout.

File location: archives/l/librepo/1.20.0/test_package/conanfile.py
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibrepoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: 依赖共享库需与测试运行同 uid/上下文才能被动态加载器
        # exec 映射，故把依赖库解引用拷贝到构建目录后注入 LD_LIBRARY_PATH；
        # 同时显式提供 TEMP/TMPDIR（musl 的 P_tmpdir=/tmp 不可写）。
        stage = os.path.join(self.build_folder, "dep-libs")
        os.makedirs(stage, exist_ok=True)
        dirs = [stage]
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                for src in glob.glob(os.path.join(libdir, "*.so*")):
                    dst = os.path.join(stage, os.path.basename(src))
                    if not os.path.exists(dst):
                        try:
                            shutil.copy2(os.path.realpath(src), dst)
                        except OSError:
                            pass
                dirs.append(libdir)

        # NOTE: conan 2.29 的 ConanFile.run(env=...) 仅接受 env 文件名列表，
        # 不再接受 Environment 对象；改为直接写入 os.environ，由子进程继承。
        tmpdir = os.environ.get("TMPDIR") or "/data/storage/el2/base/cache"
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(dirs)
        os.environ["TEMP"] = os.environ.get("TEMP") or tmpdir
        os.environ["TMPDIR"] = os.environ.get("TMPDIR") or tmpdir

        cmake_prog = self.conf.get("tools.cmake:cmake_program") or shutil.which("cmake")
        ctest_prog = os.path.join(os.path.dirname(cmake_prog), "ctest")
        if not os.path.isfile(ctest_prog):
            ctest_prog = shutil.which("ctest") or "ctest"
        self.run(f'"{ctest_prog}" --test-dir "{self.build_folder}" --output-on-failure')
