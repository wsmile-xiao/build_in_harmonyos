import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class YabasicTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # The interpreter links shared libX11/libXt; VirtualRunEnv composes
        # LD_LIBRARY_PATH from the whole dependency graph.
        VirtualRunEnv(self).generate()

    def test(self):
        if can_run(self):
            dep = self.dependencies.get("yabasic")
            bindir = dep.cpp_info.bindirs[0]
            if not os.path.isabs(bindir):
                bindir = os.path.join(dep.package_folder, bindir)
            binary = os.path.join(bindir, "yabasic")
            script = os.path.join(self.source_folder, "smoke.yab")
            # 消费者测试经 run_smoke.sh 驱动（该 .sh 同时满足 L0c 对
            # test_package/ 测试源文件的要求）：脚本校验打包解释器可执行、
            # smoke.yab 全部断言通过（退出码 0）且输出含预期标记。
            driver = os.path.join(self.source_folder, "run_smoke.sh")
            self.run(f'sh "{driver}" "{binary}" "{script}"', env="conanrun")
