from conan import ConanFile
from conan.tools.build import can_run
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # 元包依赖的 7 个工具二进制经 conanrun 注入 PATH/LD_LIBRARY_PATH，
        # test_astromatic.py 逐一真实执行 --version / -v / --help
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_astromatic.py")
        self.run(f"python3 {test_script}", env="conanrun")
