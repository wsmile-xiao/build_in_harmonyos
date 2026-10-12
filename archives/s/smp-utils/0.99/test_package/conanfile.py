import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class SmpUtilsTestConan(ConanFile):
    """test_package for smp-utils.

    Two-part consumer test (R34: really exercise the installed package):
      1. A C consumer built with CMake links smp-utils::smp-utils and
         asserts library API values (SMP function length table, numeric
         suffix parser, page size) plus OHOS-specific ELF checks.
      2. A shell smoke test discovers every installed bin/smp_* binary
         (no hardcoded list), runs --version on each, --help on two
         representatives, and verifies graceful missing-device failure
         (exit 92 = SMP_LIB_FILE_ERROR).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Part 1: C consumer assertions against libsmputils1.
        self.run("./smp_consumer_test", env="conanrun")
        # Part 2: shell smoke test over the installed binaries.
        dep = self.dependencies[self.tested_reference_str]
        pkg_bin = os.path.join(dep.package_folder, "bin")
        sh = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cmd = f"PATH='{pkg_bin}:'\"$PATH\" {sh} test.sh"
        self.run(cmd, env="conanrun")
