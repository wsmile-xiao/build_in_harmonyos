import os

from conan import ConanFile
from conan.tools.build import can_run


class ObjFWTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        if can_run(self):
            pkg = self.dependencies[self.tested_reference_str]
            includedir = pkg.cpp_info.includedirs[0] if pkg.cpp_info.includedirs else os.path.join(pkg.package_folder, "include")
            libdir = os.path.join(pkg.package_folder, "lib")
            env_cmd = "OBJFW_INCLUDE_DIR={0} OBJFW_LIB_DIR={1}".format(includedir, libdir)
            # The CI test stage does not inherit the build environment PATH,
            # so resolve the compiler from the profile conf (absolute path)
            # and hand it to the driver via CC.
            cc = "clang"
            compilers = self.conf.get("tools.build:compiler_executables", check_type=dict)
            if compilers:
                cc = compilers.get("c") or compilers.get("cpp") or cc
            env_cmd += " CC={}".format(cc)
            driver = os.path.join(self.source_folder, "run_test.py")
            # run_test.py compiles test_package.m with the ObjFW ObjC flags
            # (see cpp_info.objcflags) and executes the binary; its exit code
            # propagates as the conan test result.
            self.run("{} python3 {}".format(env_cmd, driver))
