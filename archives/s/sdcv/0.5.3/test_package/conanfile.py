import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class SdcvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # installed binary links glib dynamically with no RUNPATH (OHOS lld);
        # conanrun env carries every dependency libdir in LD_LIBRARY_PATH
        VirtualRunEnv(self).generate()

    def test(self):
        dep = self.dependencies["sdcv"]
        bindir = str(dep.cpp_info.bindirs[0])
        if not os.path.isabs(bindir):
            bindir = os.path.join(str(dep.package_folder), bindir)
        sdcv = os.path.join(bindir, "sdcv")
        script = os.path.join(os.path.dirname(__file__), "test_sdcv.sh")
        self.run('sh "{}" "{}"'.format(script, sdcv), env="conanrun")
