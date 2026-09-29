import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        info = self.dependencies["jailkit"].cpp_info
        # R34/L1e：显式校验包内产物路径存在，防止 CI 破坏性负测试 fallback
        # 到系统 jk_* 误判为真测试。
        bindirs = info.bindirs or []
        if not bindirs:
            raise ConanException("jailkit package has no bindirs")
        pkg_root = os.path.dirname(bindirs[0])
        for rel in ("bin/jk_uchroot", "sbin/jk_init", "sbin/jk_socketd",
                    "etc/jailkit/jk_init.ini", "share/jailkit/jk_lib.py"):
            if not os.path.isfile(os.path.join(pkg_root, rel)):
                raise ConanException(
                    f"jailkit package artifact missing: {pkg_root}/{rel}")
        self.pkg_root = pkg_root

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验包内产物存在")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_jailkit.sh")
        # R33：被测产物取自包路径并显式传入，禁止 PATH 撞车系统 jk_*
        self.run(f'{bash} "{script}" "{self.pkg_root}"', env="conanrun")
