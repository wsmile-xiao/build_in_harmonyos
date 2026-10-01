"""test_package — qconf 2.5（Qt5 控制台工具，qmake 工程）。

R34: 测试实质调用被测包二进制——由 test_qconf.sh 驱动 qconf --version/--help、
用 .qc 生成 configure 并校验产物内容，另含 OHOS aarch64 ELF 断言（鸿蒙特有用例 ≥1）。
工作目录用 tempfile.mkdtemp()（TMPDIR 下）创建，避免污染 test_package/ 配方目录。
"""
import os
import tempfile

from conan import ConanFile


class QconfTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["qconf"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        work_dir = tempfile.mkdtemp(prefix="qconf-test-")
        self.run(
            f'sh "{os.path.join(self.recipe_folder, "test_qconf.sh")}" '
            f'"{bin_dir}" "{work_dir}"',
            env="conanrun",
        )
