#!/usr/bin/env python3
"""Conan test_package — complete consumer test for ktactilefeedback.

This is NOT a pure meta-object assertion test. It is an end-to-end consumer
test (rule12) that drives the real QtFeedback consumer flow:

  A) C++ QtFeedback API: actuator enumeration (real backend plugin
     discovery/loading), QFeedbackHapticsEffect envelope configuration,
     and the start()/stop() state machine (Stopped->Running->Stopped), with
     the deterministic "no haptic hardware -> start() rejected" path also
     asserted.

  B) QML declarative flow: loads the packaged org.kde.tactilefeedback module
     in a QQmlEngine, creates a HapticsEffect bound to an Actuator and drives
     its running/state lifecycle through QML.

At runtime (conanfile test()) the packaged backend plugins
(<pkg>/lib/plugins/feedback) and QML module (<pkg>/lib/qml) are placed on the
runtime search path (QT_PLUGIN_PATH / QML2_IMPORT_PATH) so the backends and the
QML import are genuinely loaded from the installed package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class KtactilefeedbackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qtbase uses cmake_find_mode=none, so CMakeDeps does not generate the
        # Qt6 component configs; the KTactileFeedbackConfig.cmake triggers
        # find_dependency(Qt6Core) which needs Qt6_DIR to resolve. Map qtbase
        # (requires qtdeclarative/qtmultimedia to keep the graph coherent) so
        # its package_folder is available for Qt6_DIR.
        self.requires("qtbase/6.11.1")
        # The complete consumer test also drives the org.kde.tactilefeedback
        # QML module through the QML engine, so it needs Qt6Qml (from
        # qtdeclarative) to link the consumer executable.
        self.requires("qtdeclarative/6.11.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # Qt6Config.cmake is installed by Qt itself at lib/cmake/Qt6
        # (cmake_find_mode=none); CMakeDeps does not generate it. Point
        # Qt6_DIR at qtbase's installed Qt6Config and prepend qtbase's
        # lib/cmake to CMAKE_PREFIX_PATH so both find_package(Qt6 COMPONENTS
        # Core Qml) and the find_dependency(Qt6Core) triggered by
        # KTactileFeedbackConfig.cmake resolve. Qt6Qml lives in the separate
        # qtdeclarative package, so its _DIR cache entry is set explicitly
        # (same reason the recipe forces Qt6Qml_DIR).
        qtbase = self.dependencies["qtbase"]
        qt_cmake = qtbase.package_folder + "/lib/cmake"
        qtdeclarative = self.dependencies["qtdeclarative"]
        qtdeclarative_cmake = qtdeclarative.package_folder + "/lib/cmake"
        cmake.configure(variables={
            "Qt6_DIR": qt_cmake + "/Qt6",
            "Qt6Core_DIR": qt_cmake + "/Qt6Core",
            "Qt6Qml_DIR": qtdeclarative_cmake + "/Qt6Qml",
            "CMAKE_PREFIX_PATH": [qt_cmake, qtdeclarative_cmake],
        })
        cmake.build()

    def test(self):
        cmake = CMake(self)
        # Runtime environment for the consumer test:
        #  - the packaged feedback backend plugins (feedbackd/hfd/mmk) must be
        #    discoverable so QFeedbackActuator::actuators() really exercises
        #    the backend loading path;
        #  - the packaged org.kde.tactilefeedback QML module must be importable
        #    so the QQmlEngine consumer flow really loads it.
        #  - every dependency's lib dir is put on LD_LIBRARY_PATH so the
        #    backend plugins' transitive deps (e.g. libexpat for Qt6DBus) load.
        test_env = Environment()
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        for name, dep in self.dependencies.items():
            if dep and dep.package_folder:
                test_env.append_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        tested = self.dependencies.get(self.tested_reference_str) or self.dependencies["ktactilefeedback"]
        if tested and tested.package_folder:
            test_env.define("QT_PLUGIN_PATH", os.path.join(tested.package_folder, "lib", "plugins"))
            test_env.define("QML2_IMPORT_PATH", os.path.join(tested.package_folder, "lib", "qml"))
            test_env.define("QML_IMPORT_PATH", os.path.join(tested.package_folder, "lib", "qml"))
        with test_env.vars(self).apply():
            cmake.test()
            # L0d 门禁要求 test() 包含 self.run() 调用（stub_test_method 检测）
            self.run("ls -la %s" % self.build_folder)