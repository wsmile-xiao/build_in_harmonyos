from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["absl"].package_folder
        # L0c + R34 合规：独立测试源文件（test_absl.cpp——真实调用被测
        # 库 API——absl::StrCat（header-only）+ absl::SimpleAtoi（strings
        # 库——链接验证））+ self.run 编译链接运行。
        # absl 组件库有内部依赖链（SimpleAtoi→raw_log_internal 等）——
        # 链接全部组件库（start-group 解决循环/链式依赖）
        libdir = os.path.join(pkg, "lib")
        libs = " ".join(
            f"-l:{f}" for f in sorted(os.listdir(libdir))
            if f.startswith("libabsl_") and f.endswith(".a"))
        src = os.path.join(os.path.dirname(__file__), "test_absl.cpp")
        exe = os.path.join(os.path.dirname(__file__), "test_absl")
        self.run(
            f"/data/service/hnp/bin/clang++ '{src}' -std=c++17 "
            f"-I'{pkg}/include' -L'{libdir}' -Wl,--start-group "
            f"{libs} -Wl,--end-group -o '{exe}'",
            env="conanrun",
        )
        self.run(f"'{exe}'", env="conanrun")
