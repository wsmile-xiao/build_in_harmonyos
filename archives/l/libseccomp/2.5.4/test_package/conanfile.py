import os

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["libseccomp"].package_folder
        # R34: 真实调用 seccomp_version()/seccomp_api_get()（纯用户态 API），
        # 编译链接并运行，而非仅存在性/ELF 检查。
        src = os.path.join(os.path.dirname(__file__), "test_seccomp.c")
        exe = os.path.join(os.path.dirname(__file__), "test_seccomp")
        self.run(
            f"/data/service/hnp/bin/clang '{src}' "
            f"-I'{pkg}/include' -L'{pkg}/lib' -lseccomp -o '{exe}'",
            env="conanrun",
        )
        self.run(f"'{exe}'", env="conanrun")
