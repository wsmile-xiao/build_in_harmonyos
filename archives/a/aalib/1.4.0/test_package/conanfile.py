import os

from conan import ConanFile


class AAlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["aalib"].cpp_info
        includes = " ".join(f"-I{p}" for p in dep.includedirs)
        libs = " ".join(f"-L{p}" for p in dep.libdirs)
        self.run(f"{os.environ.get('CXX', 'c++')} test.cpp -o aalib_test {includes} {libs} -laa")

    def test(self):
        self.run("./aalib_test", env="conanrun")
