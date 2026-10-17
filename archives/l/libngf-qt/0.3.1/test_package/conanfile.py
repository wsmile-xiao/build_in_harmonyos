import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibngfQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

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
        tested = self.dependencies[self.tested_reference_str]
        tested_libdir = os.path.join(
            tested.package_folder, tested.cpp_info.libdirs[0]
        )
        qtbase = self.dependencies["qt5-qtbase"]
        qtbase_libdir = os.path.join(
            qtbase.package_folder, qtbase.cpp_info.libdirs[0]
        )
        library_paths = [
            tested_libdir,
            qtbase_libdir,
            os.environ.get("LD_LIBRARY_PATH"),
        ]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_libngf_qt",
        )
        self.run(test_bin, ignore_errors=False)
