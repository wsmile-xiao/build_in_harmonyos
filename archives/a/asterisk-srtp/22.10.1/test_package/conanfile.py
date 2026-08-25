import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class AsteriskSrtpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 实质验证：对安装产物 res_srtp.so 执行真实检查
        # （ELF 魔数/aarch64 架构/动态依赖 libsrtp2+openssl/导出符号）
        mod = os.path.join(self.dependencies["asterisk-srtp"].package_folder,
                           "lib", "asterisk", "modules", "res_srtp.so")
        assert os.path.isfile(mod), f"res_srtp.so not found at {mod}"
        self.output.info(f"res_srtp.so found: {mod}")

        checker = os.path.join(self.source_folder, "check_res_srtp.py")
        env = Environment()
        # check_res_srtp.py 内部会再拼接 "res_srtp.so"，故传目录而非完整路径
        env.define("TEST_SRTP_MOD", os.path.dirname(mod))
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')
