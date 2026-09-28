import os
from conan import ConanFile
from conan.tools.build import cross_building

class LibyuvTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libyuv"].cpp_info
        includes = " ".join("-I" + p for p in dep.includedirs)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "clang")
        self.run(f'{cc} test.c -o libyuv_probe {includes} -L"{libdir}" -lyuv -lm')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile and link check only")
            return
        self.run("./libyuv_probe", env="conanrun")
