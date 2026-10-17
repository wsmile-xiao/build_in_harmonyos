import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Qt5QtQuickControls2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("qt5-qtdeclarative/5.15.2")

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
        # Set up QML import path so the test can find QtQuick.Controls 2 plugin
        qqc2_dep = self.dependencies["qt5-qtquickcontrols2"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        qtbase = self.dependencies["qt5-qtbase"]

        qml_import_path = os.path.join(qqc2_dep.package_folder, "qml")
        qtdecl_qml = os.path.join(qtdecl.package_folder, "qml")
        if os.path.isdir(qtdecl_qml):
            qml_import_path = qml_import_path + ":" + qtdecl_qml

        os.environ["OHC_QML_IMPORT_PATH"] = qml_import_path
        os.environ["QML_IMPORT_PATH"] = qml_import_path
        os.environ["QML2_IMPORT_PATH"] = qml_import_path

        # Set up LD_LIBRARY_PATH for Qt5 shared libraries
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        qtdecl_libdir = os.path.join(qtdecl.package_folder, "lib")
        qqc2_libdir = os.path.join(qqc2_dep.package_folder, "lib")
        library_paths = [qqc2_libdir, qtdecl_libdir, qtbase_libdir,
                         os.environ.get("LD_LIBRARY_PATH")]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )

        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qt5_qtquickcontrols2",
        )
        self.run(test_bin, ignore_errors=False)
