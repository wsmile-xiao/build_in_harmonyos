import os

from conan import ConanFile
from conan.tools.build import cross_building


class SocatTestConan(ConanFile):
    """test_package — socat 1.7.4.4.1（基于上游 1.7.4.4 的适配轮次）。

    socat 是命令行工具（`package_type = "application"`），不链接任何符号，
    因此本测试**实际执行交付产物**并断言其行为（R34 反空壳）：

      - `socat -V` 输出版本号（构建通过 ≠ 产物可用，必须真的能跑）
      - `socat -h` 帮助可用
      - 基本中继：`socat -u exec:... -` 把子进程输出经 socat 转发到 stdout
      - **TCP 中继**：起一个 socat 监听 + 一个 socat 客户端，验证真正的
        socket 转发（这是 socat 的用途，也是 swtpm 测试消费它的方式）
      - 同包交付的 `filan` / `procan` 可执行

    注：swtpm 的测试以 `socat -x -t50 "FILE:...,rdonly" "UNIX-CONNECT:..."`
    形式消费本包，依赖的是 socket/文件地址转发能力；OHOS 上 AF_UNIX 路径名
    socket 受域限制，故此处以 **TCP** 作为确定性的转发判据。
    """

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        self.output.info(
            "socat 为 CLI 工具，无需编译；test() 内直接执行交付产物。")

    def test(self):
        if cross_building(self):
            self.output.info(
                "cross-building：跳过目标机执行（交付产物在目标机上运行）。")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_socat.sh")
        self.run(f'{bash} {script}', env="conanrun")
