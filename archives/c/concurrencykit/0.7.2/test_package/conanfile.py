from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ConcurrencyKitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # CMakeDeps exposes concurrencykit::concurrencykit as an INTERFACE
        # IMPORTED target without IMPORTED_LOCATION, so the test_package
        # binary has no RPATH and the dynamic loader cannot find libck.so.0
        # (SONAME) at ctest runtime. Inject LD_LIBRARY_PATH pointing at the
        # concurrencykit package's lib/ (where libck.so + libck.so.0 symlink
        # ship) so the SONAME lookup resolves. Conan's env arg is a list of
        # env script names (not a dict); augment the conanrun env via
        # environment_append before calling cmake.test().
        import os
        dep = self.dependencies[self.tested_reference_str]
        ck_lib = os.path.join(dep.package_folder, "lib")
        self.runenv_info.append_path("LD_LIBRARY_PATH", ck_lib)
        CMake(self).test(env="conanrun")
