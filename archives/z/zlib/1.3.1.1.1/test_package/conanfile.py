from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.build import can_run
import os


class ZlibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["zlib"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_zlib.c -o test_zlib {inc} -L{libdir} -lz")

    def test(self):
        if can_run(self):
            self.run("./test_zlib", env="conanrun")
