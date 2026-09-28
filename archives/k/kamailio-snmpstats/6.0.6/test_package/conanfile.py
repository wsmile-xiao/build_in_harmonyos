import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioSnmpstatsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 实质验证：对打包产物 snmpstats.so 做真实检查
        # （ELF 架构 / AgentX 依赖 / 模块符号 / MIB 数据文件）
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        module = os.path.join(package_folder, "lib", "kamailio", "modules", "snmpstats.so")
        assert os.path.isfile(module), f"snmpstats.so not found at {module}"
        self.output.info(f"snmpstats.so found: {module}")

        checker = os.path.join(self.source_folder, "check_snmpstats.py")
        env = Environment()
        env.define("SNMPSTATS_MODULE", module)
        env.define("SNMPSTATS_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')
