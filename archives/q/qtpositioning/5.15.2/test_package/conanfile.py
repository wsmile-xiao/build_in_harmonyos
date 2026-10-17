import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QtpositioningTestConan(ConanFile):
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
        pkg = self.dependencies["qtpositioning"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        qtbase = self.dependencies["qt5-qtbase"]

        # QML import paths: the package ships qml/QtPositioning (PositionSource,
        # Position, CoordinateAnimation, ...), qtdeclarative ships the QtQml /
        # QtQuick core modules.
        qml_import_path = os.path.join(pkg.package_folder, "qml")
        qtdecl_qml = os.path.join(qtdecl.package_folder, "qml")
        if os.path.isdir(qtdecl_qml):
            qml_import_path = qml_import_path + ":" + qtdecl_qml

        os.environ["OHC_QML_IMPORT_PATH"] = qml_import_path
        os.environ["QML_IMPORT_PATH"] = qml_import_path
        os.environ["QML2_IMPORT_PATH"] = qml_import_path

        # QV4 JIT is blocked by the OHOS W^X policy; force the interpreter
        # and disable the QML disk cache for headless execution.
        os.environ["QV4_FORCE_INTERPRETER"] = "1"
        os.environ["QML_DISABLE_DISK_CACHE"] = "1"

        # Qt plugin search path: the package ships plugins/position
        # (positionpoll), qtbase ships the platform/other plugin trees.
        plugin_paths = [
            os.path.join(pkg.package_folder, "plugins"),
            os.path.join(qtbase.package_folder, "plugins"),
            os.environ.get("QT_PLUGIN_PATH"),
        ]
        os.environ["QT_PLUGIN_PATH"] = ":".join(
            path for path in plugin_paths if path
        )

        # Exact plugin path for the direct QPluginLoader check in test.cpp.
        os.environ["QT_POSITIONING_PLUGIN"] = os.path.join(
            pkg.package_folder, "plugins", "position", "libqtposition_positionpoll.so"
        )

        # Qt5 shared libraries for loader/run time.
        library_paths = [
            os.path.join(pkg.package_folder, "lib"),
            os.path.join(qtdecl.package_folder, "lib"),
            os.path.join(qtbase.package_folder, "lib"),
            os.environ.get("LD_LIBRARY_PATH"),
        ]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )

        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qtpositioning",
        )
        self.run(test_bin, ignore_errors=False)
