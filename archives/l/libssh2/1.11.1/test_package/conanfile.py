import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libssh2"].cpp_info
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        cc = compiler_executables.get("c") or shutil.which("clang") or "clang"
        cmd = [cc, os.path.join(self.source_folder, "test.c"), "-o", "test_probe"]
        for include_dir in dep.includedirs:
            cmd.extend(["-I", include_dir])
        for lib_dir in dep.libdirs:
            cmd.extend(["-L", lib_dir])
        cmd.append("-lssh2")
        self.run(shlex.join(cmd))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link verification completed")
            return
        self.run("./test_probe", env="conanrun")
