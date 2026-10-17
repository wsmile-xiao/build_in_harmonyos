#!/usr/bin/env python3
import os
import shutil

from conan import ConanFile


class QmlrunnerTestConan(ConanFile):
    """test_package for the qmlrunner executable (Qt5 GUI application).

    OHOS PC has no guaranteed X11/Wayland platform plugin runtime;
    qt5-qtbase ships the offscreen platform plugin. The consumer test
    loads a real QML window application through the runner with
    QT_QPA_PLATFORM=offscreen + QT_QUICK_BACKEND=software (software
    scene graph, no GPU), verifying the full CLI contract:
    positive runs, exit codes and error paths (negative controls).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        qtbase = self.dependencies["qt5-qtbase"]
        qml = self.dependencies["qt5-qtdeclarative"]

        # offscreen QPA + software render backend: no display / GPU needed
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_QUICK_BACKEND"] = "software"
        os.environ["QT_PLUGIN_PATH"] = os.path.join(qtbase.package_folder, "plugins")
        qml_dir = os.path.join(qml.package_folder, "qml")
        os.environ["QML_IMPORT_PATH"] = qml_dir
        os.environ["QML2_IMPORT_PATH"] = qml_dir

        lib_paths = [
            os.path.join(qtbase.package_folder, "lib"),
            os.path.join(qml.package_folder, "lib"),
            os.environ.get("LD_LIBRARY_PATH"),
        ]
        os.environ["LD_LIBRARY_PATH"] = ":".join(p for p in lib_paths if p)

        # OHOS: /system/bin/sh (mksh) is not a reliable ELF wrapper; use
        # bash when available (CONFIG_SHELL from the conan profile/env).
        shell = (os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash")
                 or "sh")
        self.run(f"{shell} test.sh", env="conanrun")
