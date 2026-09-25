import os

from conan import ConanFile
from conan.errors import ConanException


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["klibc-kinit"].cpp_info
        # R34/L1e：显式校验包内产物路径，任何一项缺失都直接判定消费者拿不到交付物。
        if not dep.bindirs:
            raise ConanException("klibc-kinit package declares no bindirs")
        bindir = dep.bindirs[0]
        if not os.path.isdir(bindir):
            raise ConanException(f"klibc-kinit package bin dir missing: {bindir}")
        if not os.path.isfile(os.path.join(bindir, "kinit")):
            raise ConanException("klibc-kinit package bin/kinit missing")
        pkgroot = os.path.dirname(bindir)
        for f in ("res/upstream-tests-summary.txt", "licenses/LICENSE"):
            if not os.path.isfile(os.path.join(pkgroot, f)):
                raise ConanException(f"klibc-kinit package {f} missing")

    def test(self):
        bindir = self.dependencies["klibc-kinit"].cpp_info.bindirs[0]
        # 消费者断言全部落在 test_klibc_kinit.sh 里；脚本路径同样由包内产物推导，
        # 便于 L1e 破坏性反向验证（隐藏 bin/ 后必须整体失败）。
        script = os.path.join(self.recipe_folder, "test_klibc_kinit.sh")
        self.run(f'sh "{script}" "{bindir}"', env="conanrun")
