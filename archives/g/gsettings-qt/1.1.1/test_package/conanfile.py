#!/usr/bin/env python3
"""Conan test_package — gsettings-qt 1.1.1.

验证内容（实质性调用被测包 API，R34）：
  1. 链接 libgsettings-qt6.so 并调用 QGSettings 静态/成员 API；
  2. 用包内 glib 工具 glib-compile-schemas 编译测试 schema，
     在 GSETTINGS_BACKEND=memory 下完成 get/set/reset/keys/defaultValue/
     choices/changed 信号的真实读写验证；
  3. 校验包安装的 pkg-config 元数据（gsettings-qt6.pc）存在且声明
     Requires: gio-2.0（该库对外的主消费路径）。
"""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

SCHEMA_FILE = "com.ubports.gsettings.adt.gschema.xml"


class GsettingsQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # 测试 schema 编译工具（OHOS 侧系统无 glib-compile-schemas）。
        self.tool_requires("glib/2.88.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        pkg = self.dependencies[self.tested_reference_str].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase
        tc.cache_variables["GSETTINGS_QT_INCLUDEDIR"] = self._qt_include_dir(pkg)
        tc.cache_variables["GSETTINGS_QT_LIBRARY"] = os.path.join(
            pkg, "lib", "libgsettings-qt6.so"
        )
        tc.generate()

    @staticmethod
    def _qt_include_dir(package_folder):
        # 转发头文件 QGSettings 与 qgsettings.h 同目录；#include <QGSettings>
        # 要求 include 目录正是该 QGSettings 目录（与包内 .pc 的 Cflags 一致）。
        for root, _, files in os.walk(os.path.join(package_folder, "include")):
            if "qgsettings.h" in files:
                return root
        raise ConanInvalidConfiguration("QGSettings headers not found in package")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._compile_test_schema()
        if str(self.settings.os) == "OHOS":
            self._sign(self._test_binary())

    def _test_binary(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanInvalidConfiguration("no bindir produced for the test binary")
        return os.path.join(bindirs[0], "test_gsettings_qt")

    def _compile_test_schema(self):
        target = os.path.join(self.build_folder, SCHEMA_FILE)
        shutil.copy(os.path.join(self.recipe_folder, SCHEMA_FILE), target)
        self.run(
            "glib-compile-schemas {}".format(self.build_folder),
            env="conanbuild",
            ignore_errors=False,
        )

    def _sign(self, path):
        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; required to execute OHOS ELF binaries"
            )
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                 "-selfSign", "1"],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            os.replace(signed, path)
            os.chmod(path, original_mode)

    def test(self):
        self._check_pkg_config_metadata()
        if not can_run(self):
            self.output.info("Skipping execution: cross-build without emulator")
            return
        os.environ["GSETTINGS_SCHEMA_DIR"] = self.build_folder
        os.environ["GSETTINGS_BACKEND"] = "memory"
        self.run(self._test_binary(), env="conanrun", ignore_errors=False)

    def _check_pkg_config_metadata(self):
        pc_file = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "lib", "pkgconfig", "gsettings-qt6.pc",
        )
        if not os.path.isfile(pc_file):
            raise ConanInvalidConfiguration(f"pkg-config file missing: {pc_file}")
        with open(pc_file, encoding="utf-8") as handle:
            content = handle.read()
        if "Requires: gio-2.0" not in content:
            raise ConanInvalidConfiguration(
                "gsettings-qt6.pc does not declare 'Requires: gio-2.0'"
            )
        self.output.info("pkg-config metadata verified: {}".format(pc_file))
