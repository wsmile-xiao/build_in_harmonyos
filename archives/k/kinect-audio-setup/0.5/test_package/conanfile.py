import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    """test_package for kinect-audio-setup — runs test.sh to exercise the binary."""
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验包存在")
            return
        dep = self.dependencies["kinect-audio-setup"]
        binary = os.path.join(dep.package_folder, "sbin", "kinect_upload_fw")
        work = os.path.join(self.build_folder, "kinectwork")
        os.makedirs(work, exist_ok=True)
        # OHOS /system/bin/sh 不能执行 ELF 二进制 → 用 CONFIG_SHELL bash 包一层
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'TMPDIR="{work}" "{bash}" '
                 f'"{os.path.join(self.source_folder, "test.sh")}" "{binary}" "{work}"',
                 env="conanrun")