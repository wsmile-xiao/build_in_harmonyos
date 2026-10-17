# test_package/conanfile.py — Qt6LinguistTools 6.11.1 消费者验证
# 验证：find_package(Qt6 COMPONENTS LinguistTools) 可解析 Qt6::LinguistTools；
# 实际调用 lrelease 将 TS 转换为 QM（真实消费者路径，非空壳测试，R34）。

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Qt6LinguistToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qttools/6.11.1.1")
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        tc = CMakeToolchain(self)
        # E225: 从生成源头阻止 preset 写回 source。
        tc.user_presets_path = False
        qtbase = self.dependencies["qtbase"].package_folder
        qttools = self.dependencies["qttools"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["Qt6LinguistTools_DIR"] = os.path.join(
            qttools, "lib", "cmake", "Qt6LinguistTools"
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 实际调用被测包 qt6linguisttools 自身的 lrelease，将 TS 编译为 QM
        # （R34/L1e：破坏性反向验证会移走被测包 bin，本测试必须依赖被测包
        # 自身产物，而非其传递依赖 qttools；否则被判为假测试）。
        pkg = self.dependencies["qt6linguisttools"].package_folder
        lrelease = os.path.join(pkg, "bin", "lrelease")
        if not os.access(lrelease, os.X_OK):
            raise ConanInvalidConfiguration(
                "lrelease not found/executable in tested package: %s" % lrelease
            )
        work_dir = os.path.join(self.build_folder, "qmtest")
        os.makedirs(work_dir, exist_ok=True)
        ts_file = os.path.join(work_dir, "test_qt6linguist.ts")
        qm_file = os.path.join(work_dir, "test_qt6linguist.qm")
        with open(ts_file, "w", encoding="utf-8") as f:
            f.write(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<TS version="2.1" language="zh_CN">\n'
                "  <context>\n"
                "    <name>TestCtx</name>\n"
                "    <message>\n"
                "      <source>Hello</source>\n"
                "      <translation>你好</translation>\n"
                "    </message>\n"
                "  </context>\n"
                "</TS>\n"
            )
        self.run(
            '"%s" -silent "%s" -qm "%s"' % (lrelease, ts_file, qm_file),
            env="conanrun",
            ignore_errors=False,
        )
        if not os.path.isfile(qm_file) or os.path.getsize(qm_file) == 0:
            raise ConanInvalidConfiguration(
                "lrelease did not produce a non-empty .qm file"
            )