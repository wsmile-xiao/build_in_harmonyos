import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Qt3dOpenSourceSrcTestConan(ConanFile):
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
        qt3d_dep = self.dependencies[self.tested_reference_str]
        qtbase = self.dependencies["qt5-qtbase"]
        qt3d_libdir = os.path.join(qt3d_dep.package_folder, qt3d_dep.cpp_info.libdirs[0])
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        library_paths = [qt3d_libdir, qtbase_libdir, os.environ.get("LD_LIBRARY_PATH")]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )
        qml_dir = os.path.join(qt3d_dep.package_folder, "qml")
        if os.path.isdir(qml_dir):
            os.environ["QML_IMPORT_PATH"] = qml_dir
            os.environ["QML2_IMPORT_PATH"] = qml_dir
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qt3d_opensource_src",
        )
        self.run(test_bin, ignore_errors=False)
