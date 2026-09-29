import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class CairoConsumerTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

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
        executable = os.path.join(self.build_folder, "test_cairo")
        import glob

        # The OHOS loader may ignore Conan's LD_LIBRARY_PATH and resolve a
        # system Cairo with an older symbol set. Pin this probe to the
        # installed package and its dependency directories.
        libdirs = []
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                if libdir not in libdirs:
                    libdirs.append(libdir)
        cairo_package = self.dependencies["cairo"].package_folder
        cairo_candidates = sorted(glob.glob(os.path.join(cairo_package, "lib", "libcairo.so*")))
        cairo_library = next((path for path in cairo_candidates if path.endswith(".so.2")), None)
        if cairo_library is None:
            raise RuntimeError("installed libcairo.so.2 was not found in the tested package")
        command = "LD_LIBRARY_PATH='%s' LD_PRELOAD='%s' '%s'" % (
            os.pathsep.join(libdirs), cairo_library, executable
        )
        self.run(command, env="conanrun")
