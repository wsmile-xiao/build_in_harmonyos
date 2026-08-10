import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Qt5QtImageFormatsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.1")

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
        dep = self.dependencies["qt5-qtimageformats"]
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_lib = os.path.join(qt5.package_folder, qt5.cpp_info.libdirs[0])
        plugin_dir = os.path.join(dep.package_folder, "plugins", "imageformats")
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qt5_qtimageformats",
        )
        library_paths = [qt5_lib, os.environ.get("LD_LIBRARY_PATH")]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
            qt5.package_folder, "plugins", "platforms"
        )
        # Point Qt to the image format plugins from this package
        os.environ["QT_PLUGIN_PATH"] = os.path.join(
            dep.package_folder, "plugins"
        )
        self.run(test_bin, ignore_errors=False)
