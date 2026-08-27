import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["jellyfin-ffmpeg"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs if os.path.isabs(p)]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "/data/service/hnp/bin/clang")
        self.run(
            f"{cc} test.c -o test_probe {inc} -L{libdir} "
            f"-lavfilter -lavformat -lavcodec -lswscale -lswresample -lavutil -lm"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
