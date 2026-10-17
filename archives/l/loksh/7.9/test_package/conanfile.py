import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        info = self.dependencies["loksh"].cpp_info
        # R34/L1e：显式校验包内产物路径存在，防止 CI 破坏性负测试 fallback
        # 到系统 ksh 误判为真测试。
        bindir = info.bindirs[0] if info.bindirs else ""
        if not bindir or not os.path.isdir(bindir):
            raise ConanException(f"loksh package bin dir missing: {bindir}")
        ksh = os.path.join(bindir, "ksh")
        if not os.path.isfile(ksh):
            raise ConanException(f"ksh binary missing in package: {ksh}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验包内产物存在")
            return
        info = self.dependencies["loksh"].cpp_info
        bindir = info.bindirs[0]
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_loksh.sh")
        # R33：被测二进制取自包路径并显式传入，禁止 PATH 撞车系统 ksh
        self.run(f'{bash} "{script}" "{bindir}/ksh"', env="conanrun")
