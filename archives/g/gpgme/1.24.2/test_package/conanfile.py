import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
class GpgmeTest(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    requires = "gpgme/1.24.2"
    def requirements(self):
        self.requires("qtbase/6.11.1")
    def layout(self): cmake_layout(self)
    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["GPGME_PACKAGE_FOLDER"] = self.dependencies["gpgme"].package_folder
        tc.variables["Gpgmepp_DIR"] = os.path.join(
            self.dependencies["gpgme"].package_folder, "lib", "cmake", "Gpgmepp"
        )
        tc.variables["QGpgmeQt6_DIR"] = os.path.join(
            self.dependencies["gpgme"].package_folder, "lib", "cmake", "QGpgmeQt6"
        )
        tc.variables["Qt6_DIR"] = os.path.join(
            self.dependencies["qtbase"].package_folder, "lib", "cmake", "Qt6"
        )
        tc.variables["libgpg-error_DIR"] = self.generators_folder
        prefixes = [self.generators_folder]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefixes.extend([os.path.join(dep.package_folder, "lib", "cmake"), dep.package_folder])
        tc.variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)
        tc.generate()
        VirtualRunEnv(self).generate()
    def build(self):
        cmake=CMake(self); cmake.configure(); cmake.build()
    def test(self):
        if not self.conf.get("tools.build:skip_test", default=False):
            self.run("./gpgme_c_consumer", env="conanrun")
            self.run("./gpgme_consumer", env="conanrun")
