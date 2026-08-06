#!/usr/bin/env python3
import os

from conan import ConanFile


class AcccheckTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 调用独立测试脚本 test.sh（产物存在性检查 + perl 执行验证）。
        # acccheck 是纯 Perl 脚本，架构无关；逻辑测试在构建机（CI runner）
        # 上运行，无条件执行——用 can_run() 守卫会在 OHOS 交叉编译时跳过
        # 测试并触发 CI 破坏性负向测试（L1e）误判为空壳测试（gsan/fcheck 先例）。
        acccheck_bin = os.path.join(
            self.dependencies["acccheck"].package_folder, "bin", "acccheck.pl")
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_sh}" "{acccheck_bin}"')