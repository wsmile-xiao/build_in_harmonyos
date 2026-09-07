import os

from conan import ConanFile
from conan.tools.build import can_run


class PicocTestConan(ConanFile):
    """picoc 是 application 包（单可执行文件，无库可链接）。
    L1 测试：运行包内 picoc 解释真实 picoc 程序 smoke.c 并断言输出。
    注意 picoc 无 stdin 读取模式——`echo '...' | picoc -` 中 '-' 只是
    程序参数分隔符，会因 "main() is not defined" 失败（见 notes.md）。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bin_path = os.path.join(
                self.dependencies["picoc"].package_folder, "bin", "picoc")
            smoke = os.path.join(self.source_folder, "smoke.c")
            # grep -q 断言解释器真实输出；shell 管道退出码取自 grep，
            # 不匹配/无输出均以非零失败被 conan 拦截
            self.run(f'"{bin_path}" "{smoke}" | grep -q "picoc-test-ok 42"',
                     env="conanrun")
