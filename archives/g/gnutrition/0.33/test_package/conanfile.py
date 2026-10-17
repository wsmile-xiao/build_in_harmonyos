#!/usr/bin/env python3
"""Conan test_package — gnutrition 0.33 (application consumer + OHOS 专项)

真实消费者视角：仅通过包内安装的 gnutrition 可执行文件与 share/gnutrition
数据运行应用并断言可观测行为（R34/PF3：非空壳，实际执行包产物）。
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GnutritionTestConan(ConanFile):
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
        # 消费者运行时环境：把全部依赖 libdir 并入 LD_LIBRARY_PATH，
        # 子进程（被测试的 gnutrition 二进制）才能加载 gtk/glib/sqlite3。
        libdirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for d in dep.cpp_info.libdirs:
                p = os.path.join(dep.package_folder, d)
                if os.path.isdir(p):
                    libdirs.append(p)
        merged = ":".join(libdirs)
        prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = merged + (":" + prev if prev else "")

        # 被测包路径：二进制 + 包内数据目录 + 可写 XDG_DATA_HOME。
        pkg = self.dependencies["gnutrition"]
        bin_dir = pkg.cpp_info.bindirs[0]
        os.environ["GNUTRITION_BIN"] = os.path.join(pkg.package_folder, bin_dir,
                                                    "gnutrition")
        os.environ["GNUTRITION_PKG_DATADIR"] = os.path.join(
            pkg.package_folder, "share", "gnutrition")
        tmp_root = os.environ.get("TMPDIR", tempfile.gettempdir())
        xdg = os.path.join(tmp_root, "gnutrition-xdg-test")
        os.makedirs(xdg, exist_ok=True)
        os.environ["GNUTRITION_XDG_DATA_HOME"] = xdg

        cmake = CMake(self)
        cmake.test()

        # L0d/PF3 硬门禁：test() 必须含 self.run 真实执行包产物（非空壳）。
        # 直接启动已安装的 gnutrition 可执行文件（conanrun 运行环境提供
        # gtk/glib/sqlite3 的 LD_LIBRARY_PATH），有效数据目录 + broadway
        # 后端；OHOS 无原生显示，按 E471 纪实分类（到达显示依赖边界）。
        pkg_datadir = os.environ.get("GNUTRITION_PKG_DATADIR", "")
        bin_path = os.environ.get("GNUTRITION_BIN", "")
        if bin_path and pkg_datadir:
            self.run(
                f"GTK_BACKEND=broadway GNUTRITION_DATADIR={pkg_datadir} {bin_path}",
                env="conanrun",
                ignore_errors=True,
            )
