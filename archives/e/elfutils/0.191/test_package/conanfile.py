from conan import ConanFile


class ElfutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["elfutils"]
        incdirs = " ".join(f'-I"{path}"' for path in dep.cpp_info.includedirs)
        libdirs = " ".join(f'-L"{path}"' for path in dep.cpp_info.libdirs)
        compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c", "cc")
        self.run(f'{compiler} test_elf.c {incdirs} {libdirs} -lelf -o test_elf')
        self.run("./test_elf")
