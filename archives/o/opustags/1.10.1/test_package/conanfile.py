import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if cross_building(self):
            return
        pkg_bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_opustags_cli.sh")
        env_sh = os.path.join(self.generators_folder, "conanrun.sh")
        # 显式 source 运行时环境(conan 依赖库 LD 路径),比 env 参数更确定
        self.run(f'. "{env_sh}" && /bin/sh "{script}" "{pkg_bindir}/opustags"')
