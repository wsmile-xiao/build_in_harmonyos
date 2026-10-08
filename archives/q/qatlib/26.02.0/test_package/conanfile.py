import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMakeToolchain


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["qatlib"].package_folder
        # 复发构建期 marker
        marker = os.path.join(pkg, "res", "upstream_test_result.json")
        if os.path.isfile(marker):
            with open(marker, encoding="utf-8") as fh:
                self.output.info("HMBS_UPSTREAM_TEST_RESULT=%s"
                                 % fh.read().strip())
        # C 语言消费者测试：编译并链接真实使用 libqat 的 API
        src = os.path.join(os.path.dirname(__file__), "test_qatlib.c")
        import sys
        cc = "/data/service/hnp/bin/clang" if os.path.isfile(
            "/data/service/hnp/bin/clang") else "cc"
        out = os.path.join(self.build_folder, "test_qatlib")
        libdir = os.path.join(pkg, "lib")
        incdir = os.path.join(pkg, "include")
        # 依赖库路径（numactl / openssl 为 requires，由 conanrun 注入）
        env = dict(os.environ)
        # 沙箱 PATH 无 cc——绝对路径（同 packaging 教训）
        self.run('%s -I"%s" "%s" -L"%s" -lqat -lusdm -o "%s"'
                 % (cc, incdir, src, libdir, out), env="conanrun")
        self.run('"%s"' % out, env="conanrun")
