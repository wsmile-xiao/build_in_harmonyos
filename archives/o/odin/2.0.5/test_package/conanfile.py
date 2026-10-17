import os
import shlex

from conan import ConanFile


class OdinTestConan(ConanFile):
    """test_package for odin — 用包内 odin 编译器真实编译并运行 Odin 源程序。

    两个互补的驱动脚本，均在目标平台真实执行（非静态断言）：
      - run_tests.sh   3 项冒烟：version 断言 / hello 编译运行 / 自举（core:math）编译运行
      - consum_e2e.sh  rule12 消费者端到端：单文件编译→运行输出、os.exit(3) 退出码透传、
                       跨模块 import 编译与调用、随包运行时目录（base/ + core/）完整性
    """
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["odin"].package_folder
        odin = os.path.join(pkg, "bin", "odin")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        q = shlex.quote
        for script_name in ("run_tests.sh", "consum_e2e.sh"):
            script = os.path.join(self.source_folder, script_name)
            # 每个脚本使用独立工作目录，避免编译产物互相覆盖
            work = os.path.join(self.build_folder, script_name.replace(".sh", ""))
            cmd = " ".join([q(bash), q(script), q(odin), q(pkg), q(work)])
            self.run(cmd, env="conanrun")
