import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class AsteriskSpeexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 实质验证：对安装产物 codec_speex.so 执行真实检查
        # （ELF 魔数/aarch64 架构/动态依赖 libc/导出符号 load_module+unload_module/
        #   speex 功能符号——speex 静态链入模块）
        mod = os.path.join(self.dependencies["asterisk-speex"].package_folder,
                           "lib", "asterisk", "modules", "codec_speex.so")
        assert os.path.isfile(mod), f"codec_speex.so not found at {mod}"
        self.output.info(f"codec_speex.so found: {mod}")

        checker = os.path.join(self.source_folder, "check_codec_speex.py")
        env = Environment()
        # checker 内部会再拼接 "codec_speex.so"，故传目录而非完整路径
        env.define("TEST_CODEC_SPEEX_MOD", os.path.dirname(mod))
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')
