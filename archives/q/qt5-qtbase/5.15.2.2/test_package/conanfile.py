import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Qt5QtbaseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        variables = {}
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = compilers.get("cpp") or compilers.get("cxx")
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                variables["OHOS_CXX_RUNTIME_DIR"] = os.path.join(
                    compiler_dir, "..", "lib", "aarch64-linux-ohos"
                )
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        # Run test binary directly with LD_LIBRARY_PATH set to the
        # package's lib dir (OHOS conanrun env doesn't set it)
        dep = self.dependencies["qt5-qtbase"]
        zlib = self.dependencies["zlib"]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        zlib_libdir = os.path.join(zlib.package_folder, "lib")
        test_bin = os.path.join(self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".", "test_qt5_qtbase")
        library_paths = [libdir, zlib_libdir, os.environ.get("LD_LIBRARY_PATH")]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
            dep.package_folder, "plugins", "platforms"
        )
        self.run(test_bin, ignore_errors=False)
