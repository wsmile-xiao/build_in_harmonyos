import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_dir = self.dependencies["python-gssapi"].package_folder
        lib_dir = os.path.join(pkg_dir, "lib")
        os.environ["GSSAPI_PKG_DIR"] = lib_dir
        self.run("python3 test_gssapi.py")
