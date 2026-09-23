#!/usr/bin/env python3
"""Conan recipe for kdeclarative 6.26.0 on HarmonyOS PC.

KDeclarative is the KDE Frameworks 6 declarative bindings framework (QML
integration layer): C++ helpers backing QML components (quickaddons),
kquickcontrols QML plugins (keysequence, coloredtextarea, ...),
kquickcontrolsaddons items (QImageItem, QPixmapItem, Clipboard,
MouseEventListener), draganddrop + graphicaleffects QML plugins and the
CalendarEvents C++ library.

OHOS-specific adaptations (recipe layer):
  - 0001-ohos-disable-kglobalaccel.patch: kglobalaccel is not published in
    the ohpcd registry; OHOS has no desktop global-shortcut registry so
    HAVE_KGLOBALACCEL is forced FALSE (same semantics as the upstream
    ANDROID/IOS branches; the guard compiles to a no-op).
  - 0002-lower-ecm-and-kf-dep-version.patch lowers KF_DEP_VERSION from
    6.26.0 to 6.19.0; kconfig/kcoreaddons/ki18n/kguiaddons/kwidgetsaddons
    are consumed at their published 6.26.0 versions (>= the 6.19.0 floor).
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS not in the KDE platform list),
    KF_SKIP_PO_PROCESSING=ON, CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON,
    BUILD_TESTING=ON with the upstream qimageitemtest executed offscreen.
  - Dependencies: qtbase/6.11.1, qtdeclarative/6.11.1 (Qt6 Qml/Quick),
    kconfig/kcoreaddons/ki18n/kguiaddons/kwidgetsaddons 6.26.0,
    ecm/6.26.0 (tool_requires).
  - ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool during
    configure (ecm_query_qt); /system/lib64 + SDK llvm lib are prepended to
    LD_LIBRARY_PATH so the compatible libc++_shared.so wins over the sandbox
    bundle copy (kconfig 6.26.0 / kpackage 6.26.0 precedent).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KdeclarativeConan(ConanFile):
    name = "kdeclarative"
    version = "6.26.0"
    description = "KDE Frameworks 6 - declarative bindings framework (QML integration layer)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kdeclarative"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # Qt6Qml / Qt6Quick components come from the qtdeclarative package
        # (R35 verified: ships libQt6Qml.so + the qml/ import tree).
        self.requires("qtdeclarative/6.11.1")
        # Qt6Quick pulls Qt6ShaderTools (qtdeclarative's QtQuick module
        # links Qt6::ShaderTools); the qtbase package does not ship that
        # component, so qtshadertools must be in the graph.
        self.requires("qtshadertools/6.11.1")
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("ki18n/6.26.0")
        self.requires("kguiaddons/6.26.0")
        self.requires("kwidgetsaddons/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        # OHOS HMDFS cache filesystem refuses make jobserver fifo creation
        # (EPERM); serial make keeps the pipeline deterministic.
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "ON"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        qt_extra = []
        for dep_name in ("qtdeclarative", "qtshadertools"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _write_cmake_paths(self):
        """CMake path layer: qtbase/qtdeclarative/KF6 packages are published
        with cmake_find_mode=none, so their Config files are discovered via
        CMAKE_PREFIX_PATH entries built from the declared dependencies."""
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            'set(CMAKE_PREFIX_PATH "{};${{CMAKE_PREFIX_PATH}}")'.format(";".join(prefixes)),
            'set(CMAKE_LIBRARY_PATH "{};${{CMAKE_LIBRARY_PATH}}")'.format(";".join(libraries)),
            'set(CMAKE_INCLUDE_PATH "{};${{CMAKE_INCLUDE_PATH}}")'.format(";".join(includes)),
            'set(CMAKE_MODULE_PATH "{};${{CMAKE_MODULE_PATH}}")'.format(";".join(modules)),
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _system_lib_env(self, env):
        """Prepend the system library dirs so the compatible libc++_shared.so
        wins over the sandbox bundle copy (ECM qtpaths host tool needs it
        during configure; kconfig/kpackage 6.26.0 precedent)."""
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        self._system_lib_env(build_env)
        return build_env

    def _library_runtime_env(self, include_build=False):
        runtime_env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                # KF6 packages install some shared libraries under bin/ as
                # well; both layouts are collected.
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin")
                )
                runtime_env.prepend_path(
                    "PATH", os.path.join(dep.package_folder, "bin")
                )
                runtime_env.prepend_path(
                    "PATH", os.path.join(dep.package_folder, "libexec")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml")
                )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        """Upstream autotest handling (rule4 verification).

        Upstream `tests/CMakeLists.txt` registers exactly ONE test target:
        the `qimageitemtest` executable (built via add_executable +
        ecm_mark_as_test). It is an interactive manual GUI test, not a
        CTest-registered automated case: `main()` does `view.show()` +
        `app.exec()` and the accompanying qimageitemtest.qml states "this
        file should be used via qimageitemtest executable" (human-driven
        fillMode/isNull inspection). There is no add_test() call anywhere in
        the upstream build system, so CTest N=0 is the true upstream
        registration count.

        Verification performed here:
          1. The test target is BUILT with BUILD_TESTING=ON (build success
             proves the Qt6Quick/Qt6Test-linked test compiles and links
             against the freshly built QML module).
          2. The executable is launched offscreen under a timeout: a
             graceful startup (no crash/abort before the event loop) is
             observed; the GUI event loop then runs until the timeout
             kills it (expected for an interactive test on a headless
             builder). A crash before the event loop would surface as a
             non-124 exit code.
        """
        test_env = self._library_runtime_env(include_build=False)
        self._system_lib_env(test_env)
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        # The freshly built QML plugin (org.kde.kquickcontrolsaddons) lives in
        # <build>/bin per ECM KDEInstallDirs; QML2_IMPORT_PATH covers it.
        test_env.prepend_path("QML2_IMPORT_PATH", os.path.join(self.build_folder, "bin"))
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        test_bin = os.path.join(self.build_folder, "bin", "qimageitemtest")
        if not os.path.isfile(test_bin):
            raise Exception(
                "upstream test executable qimageitemtest was not built: %s" % test_bin
            )
        self.output.info(
            "Upstream test registration count (rule4): 1 test target built "
            "(qimageitemtest, interactive manual GUI test, no add_test -> "
            "CTest N=0); launching it offscreen to verify startup."
        )
        with test_env.vars(self).apply():
            # timeout(1) exits 124 when it had to kill the still-running GUI
            # event loop; that is the expected healthy outcome for an
            # interactive test on a headless builder. Any other non-zero code
            # means the test crashed before entering the event loop.
            result = self.run(
                'timeout 10 "%s"' % test_bin, ignore_errors=True
            )
        self.output.info("qimageitemtest offscreen launch result: %s" % result)
        # The executable linked and started; the interactive event loop runs
        # until the timeout (recorded above). Only a hard failure before the
        # event loop (segfault, abort, missing plugin) would be fatal here;
        # self.run reports non-zero only when the command itself failed to
        # execute. A missing QML module import aborts the process before the
        # event loop with a non-zero exit that we still treat as fatal
        # because it means the shipped QML plugin tree is unusable.
        if result != 0 and result != 124:
            raise Exception(
                "qimageitemtest failed before entering the GUI event loop "
                "(exit %s); see the log above" % result
            )

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env(include_build=True).vars(self).apply():
            cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6CalendarEvents"]
        # The QML plugin libraries (kquickcontrolsprivate etc.) are installed
        # as private QML module plugins; they are dlopen'ed by the QML engine
        # through QML2_IMPORT_PATH rather than linked directly. No bindirs
        # declaration: bin/ only holds QML module artifacts, not CLI tools
        # (R38 commands.json is not applicable to this library package).
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, "qml"))
        self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml"))
