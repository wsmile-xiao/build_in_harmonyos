import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class QdTestConan(ConanFile):
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
        # The installed qd-config script must report the upstream version.
        pkg = self.dependencies[self.tested_reference_str].package_folder
        qd_config = os.path.join(pkg, "bin", "qd-config")
        if not os.path.isfile(qd_config):
            raise ConanException("qd-config was not installed into bin/")
        res = subprocess.run([qd_config, "--version"], capture_output=True,
                             text=True, timeout=60)
        version = res.stdout.strip()
        ok = res.returncode == 0 and version == "2.3.23"
        print("%s: qd-config --version == 2.3.23 (got %r)" %
              ("PASS" if ok else "FAIL", version))
        if not ok:
            raise ConanException("qd-config --version reported %r" % version)

        # The consumer binary asserts dd_real/qd_real arithmetic, the eps
        # fingerprints, pi digits, and the c_qd C interface.
        self.run("./qd_test_package", env="conanrun")
