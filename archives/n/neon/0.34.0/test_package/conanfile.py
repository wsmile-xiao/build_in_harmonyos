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
        pkg = self.dependencies["neon"].package_folder
        # L0c + R34 合规：独立测试源文件（test_neon.cpp——真实调用被测
        # 库 API——ne_sock_init + ne_uri_parse——纯用户态）+ self.run
        src = os.path.join(os.path.dirname(__file__), "test_neon.cpp")
        exe = os.path.join(os.path.dirname(__file__), "test_neon")
        self.run(
            f"/data/service/hnp/bin/clang++ '{src}' "
            f"-I'{pkg}/include' -L'{pkg}/lib' -lneon -o '{exe}'",
            env="conanrun",
        )
        self.run(f"'{exe}'", env="conanrun")
