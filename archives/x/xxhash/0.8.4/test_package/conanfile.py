import os
import shlex

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["xxhash"].cpp_info
        includes = " ".join("-I{}".format(shlex.quote(path)) for path in dep.includedirs)
        libdirs = " ".join("-L{}".format(shlex.quote(path)) for path in dep.libdirs)
        rpaths = " ".join("-Wl,-rpath,{}".format(shlex.quote(path)) for path in dep.libdirs)
        libraries = " ".join("-l{}".format(name) for name in dep.libs)
        compiler = " ".join(shlex.quote(part) for part in shlex.split(os.environ.get("CC", "clang")))
        command = "{} -std=gnu99 -Wall -Wextra -Werror test.c -o test_probe {} {} {} {}".format(
            compiler, includes, libdirs, libraries, rpaths
        )
        self.run(command, env="conanbuild")

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: consumer test compiled and linked; execution skipped")
            return
        self.run("./test_probe", env="conanrun")
