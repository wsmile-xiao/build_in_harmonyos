import os

from conan import ConanFile
from conan.tools.build import cross_building


class SwtpmTestConan(ConanFile):
    """test_package — swtpm 0.10.1。

    swtpm 是命令行工具（`package_type = "application"`），不是库，故不链接任何
    符号，而是**实际执行交付产物**并断言其行为：

      - `swtpm --version` / `swtpm_setup --version` / `swtpm_ioctl --version`
        必须真实运行并输出版本号（R34 反空壳：断言运行时可用性，而非文件存在）
      - `swtpm socket --help` 必须可用 —— 这是 gnupg `tests/tpm2dtests/
        start_sw_tpm.sh` 消费本包的确切子命令
      - 功能验证：以 gnupg 相同的方式在 TCP 上拉起模拟器（`--server type=tcp`
        `--ctrl type=tcp`），确认进程存活且控制通道端口可连接后正常退出
    """

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        self.output.info(
            "swtpm 为 CLI 工具，无需编译；test() 内直接执行交付产物。")

    def test(self):
        if cross_building(self):
            self.output.info(
                "cross-building：跳过目标机执行（交付产物在目标机上运行）。")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_swtpm.sh")
        self.run(f'{bash} {script}', env="conanrun")
