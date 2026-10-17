from conan import ConanFile
from conan.tools.build import cross_building


class LibxsmmTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libxsmm"].cpp_info
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        includes = " ".join(f'-I"{path}"' for path in dep.includedirs)
        libdirs = " ".join(f'-L"{path}"' for path in dep.libdirs)
        self.run(
            f'{cc} -DLIBXSMM_PLATFORM_FORCE test.c -o test_libxsmm {includes} {libdirs} '
            "-lxsmm -lxsmmnoblas -ldl -lm -lpthread"
        )

    def test(self):
        if not cross_building(self):
            self.run("./test_libxsmm", env="conanrun")
