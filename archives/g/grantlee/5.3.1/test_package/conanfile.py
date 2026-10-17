#!/usr/bin/env python3
"""test_package —— grantlee 消费者测试（Conan L1 / R34）。

真实调用被测包公开 API：Grantlee::Engine/Template/Context 渲染链路
（变量插值/autoescape 转义/for 标签/内建过滤器/错误处理五个用例）。
断言失败时进程返回非零，conan create 的 test() 即失败。

运行环境说明（HarmonyOS 平台特性）：
  musl 加载器拒绝加载 HMDFS 路径（conan 缓存）上构建的 .so——
  test() 先运行 setup-el2-runtime.sh 把运行库/插件布置到 el2 应用数据
  目录（拷贝+SONAME 实体化+重签），再以 el2 前置的 LD_LIBRARY_PATH
  运行测试二进制（详见脚本头注释与知识草稿
  DRAFT-libkysdk-system-3.0.1.1-hmdfs-el2-runtime-copy）。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class GrantleeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        qt = None
        for _ref, dep in self.dependencies.items():
            if "qt5-qtbase" in str(_ref):
                qt = dep
                break
        # qt5-qtbase cmake_find_mode=none：find_package(Qt5Core) 需要包内
        # 官方 config；被测包 grantlee 同为 cmake_find_mode=none（包内上游
        # 官方 Grantlee5Config.cmake）——两个包的 lib/cmake 都前置
        # CMAKE_PREFIX_PATH（先例 kimageformats5；本文件由 conan_toolchain
        # 自动 include）
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if qt:
            qt_pkg = os.fspath(qt.package_folder).replace("\\", "/")
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            # AUTOMOC 工具（aarch64 本机二进制，随包分发）
            lines.append(f'set(CMAKE_AUTOMOC_EXECUTABLE '
                         f'"{qt_pkg}/bin/moc")')
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0])
        if pkg is not None and pkg.package_folder:
            gp = os.fspath(pkg.package_folder).replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{gp}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{gp}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{gp}/include")')
        paths_file = os.path.join(self.generators_folder,
                                  "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        qt = None
        for _ref, dep in self.dependencies.items():
            if "qt5-qtbase" in str(_ref):
                qt = dep
                break
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        el2 = "/data/storage/el2/base/files/.conan-runlibs/grantlee"
        # ① 布置 el2 运行时（幂等：库集合指纹未变则跳过）
        setup = os.path.join(self.source_folder, "setup-el2-runtime.sh")
        if os.path.isfile(setup) and pkg is not None and qt is not None:
            try:
                subprocess.run(
                    ["/data/service/hnp/bin/bash", setup,
                     os.fspath(pkg.package_folder),
                     os.fspath(qt.package_folder)],
                    check=True, timeout=600, capture_output=True)
            except Exception as exc:  # noqa: BLE001
                self.output.warning(f"el2 setup failed: {exc}")
        # ② 组装运行环境：el2 前置 + Qt 平台插件 + grantlee 插件根
        extra = []
        if os.path.isdir(el2):
            extra.append(el2)
        if qt is not None and qt.package_folder:
            extra.append(os.path.join(qt.package_folder, "plugins"))
        plugin_root = os.path.join(el2, "grantlee-plugins")
        env_script = os.path.join(self.generators_folder,
                                  "conanrunextra-grantlee.sh")
        with open(env_script, "w", encoding="utf-8") as f:
            if qt is not None and qt.package_folder:
                f.write('export QT_PLUGIN_PATH="%s"\n'
                        % os.path.join(qt.package_folder, "plugins"))
            # 引擎按 <pluginDir>/grantlee/<major>.<minor>/ 布局查找标签
            # 插件（EnginePrivate::loadCppLibrary），测试程序读该变量调
            # engine->addPluginPath 注入（GRANTLEE_PLUGIN_PATH 宏是编译
            # 期烧录的构建机路径，交叉产物不可达）
            f.write('export GRANTLEE_TEST_PLUGIN_DIR="%s"\n' % plugin_root)
            f.write('export LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH"\n'
                    % ":".join(extra))
        bindirs = self.cpp.build.bindirs
        self.run(os.path.join(bindirs[0], "test_grantlee"),
                 env=["conanrun", env_script])
