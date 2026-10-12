#!/usr/bin/env python3
"""Conan recipe for kuserfeedback 6.28.0 on HarmonyOS PC.

kuserfeedback is a KDE Frameworks 6 library (KF6UserFeedbackCore/Widgets)
providing telemetry/usage-statistics collection and survey delivery for Qt
applications (used by KDE Gear apps and Plasma).

OHOS-specific adaptations (following the kstatusnotifieritem/6.26.0 and
attica/6.28.0 patterns):
  - 0001-lower-ecm-version.patch: upstream find_package(ECM ${KF_DEP_VERSION})
    i.e. 6.28.0, while the ohpcd registry publishes ecm/6.26.0 as the newest
    KF6-generation ECM; lower the gate the same way attica/6.28.0 and
    kdnssd/6.29.0 did.
  - 0002-disable-po-qm-processing.patch + KF_SKIP_PO_PROCESSING=ON: po/qm
    translation processing requires Qt6 LinguistTools (not published to
    ohpcd). The ecm_create_qm_loader call itself only configure_file()s a
    self-contained loader stub (verified in ECM 6.26.0), so it is kept.
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform whitelist detection
    (OHOS is not in the KDE platform list).
  - ENABLE_PHP=OFF / ENABLE_PHP_UNIT=OFF: server-side PHP survey backend is
    entirely disabled (no PHP on OHOS, server/testserver never built).
  - ENABLE_DOCS=OFF: no qdoc (Qt6ToolsTools not published).
  - ENABLE_CONSOLE=OFF: UserFeedbackConsole + CLI need Qt6Charts/Svg
    (not published to ohpcd); provider libs are unaffected.
  - ENABLE_SURVEY_TARGET_EXPRESSIONS=ON: flex 2.6.4 + bison 3.8.2 are
    available on the OHOS SDK toolchain bin dir (FLEX_FOUND/BISON_FOUND).
  - BUILD_TESTING=ON and ctest execution for upstream autotests with
    QT_QPA_PLATFORM=offscreen and an isolated HOME/XDG_RUNTIME_DIR.
  - Dependencies: qtbase/6.11.1 (Core/Network/Gui/Widgets/Test) and
    qtdeclarative/6.11.1 (for the KF6UserFeedbackQml module);
    tool_requires ecm/6.26.0.
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake created manually (qtbase and qtdeclarative
    use cmake_find_mode=none in their own package_info, so CMakeDeps does
    not add their lib/cmake dirs to CMAKE_PREFIX_PATH for us).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KuserfeedbackConan(ConanFile):
    name = "kuserfeedback"
    version = "6.28.0"
    description = "KDE Frameworks 6 - user feedback/telemetry and survey framework"
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/frameworks/kuserfeedback"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")

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
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["ENABLE_PHP"] = "OFF"
        tc.variables["ENABLE_PHP_UNIT"] = "OFF"
        tc.variables["ENABLE_DOCS"] = "OFF"
        tc.variables["ENABLE_CONSOLE"] = "OFF"
        tc.variables["ENABLE_SURVEY_TARGET_EXPRESSIONS"] = "ON"

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

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep_name in ("qtbase", "qtdeclarative", "qtshadertools"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                pkg = dep.package_folder
                lines += [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")',
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")',
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")',
                ]
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        for rel in ("bin", "lib", "tests"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        # Upstream registers 7 autotests via uf_add_test() when the console
        # and PHP paths are disabled (see notes.md for the full N accounting).
        # Run them under ctest with the offscreen QPA platform and an
        # isolated HOME/XDG_RUNTIME_DIR so nothing touches the real user env.
        test_env = self._library_runtime_env()
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("KUSERFEEBACK_SKIP_TESTOPENGLINFOSOURCE", "1")
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run("ctest --output-on-failure", cwd=self.build_folder)

    def _prepare_ctest_runtime_links(self):
        # Materialize a compatibility bin/ dir one level above the build
        # folder so slash-containing DT_NEEDED entries resolve against CWD.
        import shutil

        # CI evidence: feedbackconfigtest failed with
        #   "Error loading shared library ../../../bin/libKF6UserFeedbackCore.so
        #    (needed by ../bin/libKF6UserFeedbackWidgets.so)"
        # musl resolves slash-containing DT_NEEDED entries against the process
        # CWD (= ctest cwd = build folder). The CMake-generated Widgets
        # library references Core THREE levels up, while the old code only
        # materialized one level. Cover ../bin, ../../bin and ../../../bin.
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for level in (1, 2, 3):
            compatibility_bin = os.path.normpath(
                os.path.join(self.build_folder, *([os.pardir] * level + ["bin"]))
            )
            os.makedirs(compatibility_bin, exist_ok=True)
            for src in lib_sources:
                dst = os.path.join(compatibility_bin, os.path.basename(src))
                if os.path.exists(src) and not os.path.exists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6UserFeedbackConfig.cmake with
        # proper dependency tracking. Use cmake_find_mode=none so CMakeDeps
        # doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6UserFeedbackCore", "KF6UserFeedbackWidgets"]
