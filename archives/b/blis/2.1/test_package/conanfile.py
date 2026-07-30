from conan import ConanFile
from conan.tools.build import cross_building


class BlisTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["blis"].cpp_info
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        includes = " ".join(f'-I"{path}"' for path in dep.includedirs)
        libdirs = " ".join(f'-L"{path}"' for path in dep.libdirs)
        self.run(f'{cc} test.c -o test_blis {includes} {libdirs} -lblis -lm -lpthread')

    def test(self):
        if not cross_building(self):
            self.run("./test_blis", env="conanrun")
