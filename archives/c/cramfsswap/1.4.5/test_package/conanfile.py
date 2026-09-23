import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import cmake_layout


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验包存在")
            return
        dep = self.dependencies["cramfsswap"]
        binpath = os.path.join(dep.package_folder, "bin", "cramfsswap")
        work = os.path.join(self.build_folder, "cramfswork")
        os.makedirs(work, exist_ok=True)
        out_file = os.path.join(self.build_folder, "test_cramfsswap.out")
        # python3 走 /bin/sh（conan self.run 为 shell=True），输出重定向到
        # 文件再回读（self.run 不返回子进程输出；N=0 也要判失败）
        self.run(f'python3 "{os.path.join(self.source_folder, "test_cramfsswap.py")}" '
                 f'"{binpath}" "{work}" > "{out_file}" 2>&1 || exit 1',
                 env="conanrun")
        out = open(out_file, encoding="utf-8", errors="replace").read()
        self.output.info(out)
        if "FAIL - " in out:
            raise ConanException("test_package 有断言失败（见上方 FAIL 行）")
