import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibkolabxmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Public headers of libkolabxml include boost/scoped_ptr.hpp, so
        # the consumer needs the transitive requirement too.
        self.requires("boost/1.90.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        # CMAKE_POLICY_VERSION_MINIMUM for CMake 4.x vs the 3.15-era
        # cmake_minimum_required in the test CMakeLists is injected via the
        # environment to avoid double-instantiating CMakeToolchain.
        cmake = CMake(self)
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def test(self):
        # L0d/R34: actually execute the test binary (real round-trip through
        # the library API). The executable links ../lib/libkolabxml.so via
        # its RPATH in the conan test layout; resolve the deps explicitly.
        exe = os.path.join(self.cpp.build.bindirs[0], "test_package")
        libdirs = []
        for _, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            for sub in ("lib", "lib64"):
                d = os.path.join(dep.package_folder, sub)
                if os.path.isdir(d) and any(
                    f.endswith(".so") or ".so." in f for f in os.listdir(d)
                ):
                    libdirs.append(d)
        ld = ":".join(dict.fromkeys(libdirs))
        self.run(f'export LD_LIBRARY_PATH="{ld}" && "{exe}"')
        print("test_package: PASS")
