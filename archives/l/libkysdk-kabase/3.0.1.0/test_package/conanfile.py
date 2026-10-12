#!/usr/bin/env python3
"""Conan test_package — libkysdk-kabase 3.0.1.0 (single_application 组件).

R34：测试真实依赖被测包——test_single_application.cpp 包含被测包安装的
上游头文件 <single_application/single_application.hpp>，链接被测包产出的
libkysdk-kabase.so，并真实调用其 API（QtSingleApplication 构造 / id() /
activationWindow() / isRunning()）；断言失败 → 非零退出 → conan test 失败。

环境：QT_QPA_PLATFORM=offscreen + 可写 TMPDIR（OHOS /tmp 只读，QtLocalPeer
的 .lockfile 需要可写临时目录）。
"""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class LibkysdkKabaseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qmake 与 Qt5 Core/Network/Widgets（直接依赖以获取 qmake 与头文件路径）
        self.requires("qt5-qtbase/5.15.2.2")

    def _qtbase(self):
        qtbase = self.dependencies["qt5-qtbase"]
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise SystemExit(f"FAIL: qt5-qtbase does not provide bin/qmake: {qmake}")
        return qtbase, qmake

    def build(self):
        if not can_run(self):
            self.output.warning("skipped (cannot run on this platform)")
            return
        qtbase, qmake = self._qtbase()
        dep = self.dependencies["libkysdk-kabase"]
        inc_dir = os.path.join(dep.package_folder, "include")
        lib_dir = os.path.join(dep.package_folder, "lib")
        env = Environment()
        env.define("QTDIR", qtbase.package_folder)
        env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        with env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} -spec linux-clang '
                f'"INCLUDEPATH+={inc_dir}" "LIBS+=-L{lib_dir} -lkysdk-kabase" '
                f"test_single_application.pro"
            )
            self.run(f'cd "{self.source_folder}" && make -j4')
        exe = os.path.join(self.source_folder, "test_single_application")
        if not os.path.isfile(exe):
            raise SystemExit(f"FAIL: consumer test executable not built: {exe}")
        self.output.info(f"built consumer test: {exe}")

    def test(self):
        if not can_run(self):
            self.output.warning("skipped (cannot run on this platform)")
            return
        exe = os.path.join(self.source_folder, "test_single_application")
        if not os.path.isfile(exe):
            raise SystemExit(f"FAIL: consumer test executable missing: {exe}")
        # 组装运行时环境：所有依赖的 lib 目录 + 可写 TMPDIR + offscreen QPA
        env = Environment()
        for d in self.dependencies.values():
            if not d.package_folder:
                continue
            for libdir in (list(d.cpp_info.libdirs) or ["lib"]):
                full = os.path.join(d.package_folder, libdir)
                if os.path.isdir(full):
                    env.prepend_path("LD_LIBRARY_PATH", full)
        tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define("TMPDIR", tmp)          # OHOS /tmp 只读，QtLocalPeer lockfile 需可写
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            self.run(exe, cwd=self.source_folder)
        self.output.info("PASS: libkysdk-kabase 消费者测试（真实 API 调用）通过")
