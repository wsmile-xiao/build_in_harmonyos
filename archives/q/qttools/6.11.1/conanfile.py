#!/usr/bin/env python3
"""Conan recipe for qttools 6.11.1 — Qt Linguist tools for HarmonyOS PC."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get


class QttoolsConan(ConanFile):
    name = "qttools"
    version = "6.11.1"
    description = "Qt Tools — provides lrelease, lupdate, lconvert for Qt translations"
    license = "BSD-3-Clause"
    homepage = "https://doc.qt.io/qt-6/qttools-index.html"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # 上游 qttools 测试：仅保留能在无 qtdeclarative 环境下真实运行的用例。
    # - tst_lrelease/tst_lcheck/tst_qtattributionsscanner 使用 QTEST_MAIN
    #   （先创建 QCoreApplication），可配合 qt.conf 定位工具，通过。
    # - tst_lconvert/tst_ltext2id 使用 QTEST_APPLESS_MAIN（无 QCoreApplication），
    #   QLibraryInfo 无法读取 qt.conf（Qt 6.11 findConfiguration 无环境变量兜底），
    #   工具路径解析失败 —— 上游测试框架限制，排除。
    # - tst_lupdate 的 parsejs/parseqml 用例依赖 qtdeclarative 的 QML 解析能力，
    #   而 qtdeclarative 尚未发布到制品仓，排除。
    _upstream_test_targets = (
        "tst_lrelease",
        "tst_lcheck",
        "tst_qtattributionsscanner",
    )

    # 依赖 qtbase（制品仓已发布 6.11.1，PR #5111 合并）
    # 使用 requirements() 方法形式，以便 CI 脚本 build_and_test.sh 的 L0i 正则匹配
    def requirements(self):
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        tc = CMakeToolchain(self)
        # Qt's native config exports BuildInternals and component targets that a
        # generic CMakeDeps-generated Qt6Config.cmake cannot reproduce.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_prefix
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6"
        )
        tc.cache_variables["Qt6BuildInternals_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6BuildInternals"
        )
        # qtbase's Conan package ships the upstream mkspecs directory; OHOS
        # is not a separate mkspec there, so use linux-clang (matches the
        # qtbase recipe's own QT_QMAKE_TARGET_MKSPEC).
        tc.cache_variables["QT_QMAKE_TARGET_MKSPEC"] = "linux-clang"
        # 构建并运行上游 Linguist 测试（对齐 qtbase 先例）：
        # QT_BUILD_TESTS=ON 让 tests/auto 进入构建，BY_DEFAULT=OFF 避免全量
        # 测试目标被默认构建，仅构建 _upstream_test_targets 中列出的目标。
        tc.cache_variables["QT_BUILD_TESTS"] = "ON"
        tc.cache_variables["QT_BUILD_TESTS_BY_DEFAULT"] = "OFF"
        tc.cache_variables["QT_FEATURE_assistant"] = "OFF"
        tc.cache_variables["QT_FEATURE_designer"] = "OFF"
        tc.cache_variables["QT_FEATURE_pixeltool"] = "OFF"
        tc.cache_variables["QT_FEATURE_qdbus"] = "OFF"
        tc.cache_variables["QT_FEATURE_qdiag"] = "OFF"
        tc.cache_variables["QT_FEATURE_qplugininfo"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 构建上游 Linguist 测试目标（对齐 qtbase 先例）
        for target in self._upstream_test_targets:
            cmake.build(target=target)
        # 运行上游测试（offscreen QPA，无需真实显示环境）
        if can_run(self):
            qtbase_prefix = self.dependencies["qtbase"].package_folder
            test_env = Environment()
            test_env.define("QT_QPA_PLATFORM", "offscreen")
            test_env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
            # 测试二进制链接 qtbase 包中的 libQt6Core/libQt6Test，
            # 显式将 qtbase 包 lib 加入 LD_LIBRARY_PATH 供加载器查找。
            test_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(qtbase_prefix, "lib")
            )
            # 上游测试通过 QLibraryInfo::BinariesPath / LibraryExecutablesPath
            # 定位 lrelease/lconvert/qtattributionsscanner 等工具，而该路径
            # 默认指向 qtbase 包（测试链接 qtbase 的 libQt6Core）。因此在每个
            # 测试二进制所在目录放置 qt.conf 覆盖工具路径到 qttools build 目录。
            # 同时把 qttools build bin/libexec 加入 PATH，让被 QProcess 启动的
            # 子进程（lrelease/lcheck/qtattributionsscanner）也能找到工具自身。
            qt_conf = "[Paths]\nBinaries={}\nLibraryExecutables={}\nPlugins={}\n".format(
                os.path.join(self.build_folder, "bin"),
                os.path.join(self.build_folder, "libexec"),
                os.path.join(self.build_folder, "plugins"),
            )
            test_env.prepend_path(
                "PATH", os.path.join(self.build_folder, "bin")
            )
            test_env.prepend_path(
                "PATH", os.path.join(self.build_folder, "libexec")
            )
            test_env.prepend_path(
                "PATH", os.path.join(qtbase_prefix, "libexec")
            )
            test_dirs = set()
            for root, _, filenames in os.walk(self.build_folder):
                if "/tests/" not in root:
                    continue
                for fn in filenames:
                    if fn in self._upstream_test_targets:
                        test_dirs.add(root)
            written = []
            for d in test_dirs:
                p = os.path.join(d, "qt.conf")
                with open(p, "w", encoding="utf-8") as f:
                    f.write(qt_conf)
                written.append(p)
            try:
                pattern = "^({})$".format("|".join(self._upstream_test_targets))
                with test_env.vars(self).apply():
                    self.run(
                        f'ctest --output-on-failure -R "{pattern}"',
                        cwd=self.build_folder,
                    )
            finally:
                for p in written:
                    if os.path.exists(p):
                        os.unlink(p)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.builddirs = ["lib/cmake/Qt6LinguistTools"]
        # Preserve Qt's installed config and qt_add_lrelease macros instead of
        # replacing them with an empty generic CMakeDeps config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.buildenv_info.prepend_path("CMAKE_PREFIX_PATH", self.package_folder)
