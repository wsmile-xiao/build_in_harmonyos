#!/usr/bin/env python3
"""Conan recipe for knewstuff 6.14.0 on HarmonyOS PC.

KNewStuff is the KDE Frameworks 6 content-getting framework (download &
install addons): core jobs/engine (KF6NewStuffCore), widgets API
(KF6NewStuffWidgets), a QML module (KNewStuffQuick) and a demo dialog tool.

OHOS adaptation (pattern aligned with published kxmlgui/ktextwidgets/sonnet):
  - KF_IGNORE_PLATFORM_CHECK=TRUE, KF_SKIP_PO_PROCESSING=ON (lconvert fails)
  - BUILD_DESIGNERPLUGIN=OFF (Qt6UiPlugin not published)
  - BUILD_TESTING=ON: upstream ctest executed offscreen
  - Qt6 Qml/Quick/QuickWidgets come from published qtdeclarative/6.11.1
  - KF6Attica/KF6Package resolved via published 6.18.0 (find_package range
    [6.14.0,7.0) accepts them), same technique as ktextwidgets->sonnet/6.26
  - runtime env + `<build>/../bin` symlink farm for DT_NEEDED quirks of
    published KF6 binaries (kxmlgui pattern)
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KnewstuffConan(ConanFile):
    name = "knewstuff"
    version = "6.14.0"
    description = "KDE Frameworks 6 - Get new content (addons download/install)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/knewstuff"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtbase-gui/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("karchive/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        # [6.14.0, 7.0) find_package ranges accept these published versions;
        # the whole KF6 set is aligned on 6.18.0 (kpackage only ships 6.18).
        self.requires("kpackage/6.18.0")
        self.requires("attica/6.18.0")

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
        # Qt6UiPlugin not published (same guard as sonnet/ktextwidgets)
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"

        # CMakeDeps for our direct deps; the KF6/Qt6 packages ship their own
        # upstream configs, aggregated via conan_cmakedeps_paths.cmake below.
        CMakeDeps(self).generate()

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # Qt6 split-package component discovery: qtbase's top-level
        # lib/cmake/Qt6/Qt6Config.cmake resolves REQUIRED COMPONENTS (Qml,
        # Quick, QuickWidgets from qtdeclarative; Widgets/Gui from
        # qtbase-gui) only against QT_ADDITIONAL_PACKAGES_PREFIX_PATH —
        # CMAKE_PREFIX_PATH alone yields "Could NOT find Qt6Qml (missing:
        # Qt6Qml_DIR)". Verified necessary and sufficient on this device.
        qt_extra = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                if os.path.isdir(
                        os.path.join(dep.package_folder, "lib", "cmake")) and \
                   any(n.startswith("Qt6") for n in os.listdir(
                       os.path.join(dep.package_folder, "lib", "cmake"))):
                    qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables[
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    # package ROOT so that split configs under
                    # <pkg>/lib/cmake/Qt6Qml/ (and Qt6Quick, Qt6QuickWidgets,
                    # KF6* …) resolve; CMake matches find_package(Qt6Qml) as
                    # <prefix>/lib/cmake/Qt6Qml/ only when prefix is the root.
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
                runtime_env.prepend_path(
                    "QML_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
                runtime_env.prepend_path(
                    "QML_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        runtime_env.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.build_folder, "bin")
        )
        for rel in ("bin", "lib", os.path.join("src", "lib"),
                    os.path.join("src", "qtquick")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
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
        self._prepare_ctest_runtime_links()
        self._patch_ctest_qt_plugin_path()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _qt_plugin_path(self):
        plugin_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    plugin_dir = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(plugin_dir):
                        plugin_dirs.append(plugin_dir)
        plugin_dirs.append(os.path.join(self.build_folder, "bin"))
        return os.pathsep.join(plugin_dirs)

    def _patch_ctest_qt_plugin_path(self):
        build_bin = os.path.join(self.build_folder, "bin")
        full_plugin_path = self._qt_plugin_path()
        needle = f"QT_PLUGIN_PATH={build_bin}"
        replacement = f"QT_PLUGIN_PATH={full_plugin_path}"
        for test_file in glob.glob(
            os.path.join(self.build_folder, "**", "CTestTestfile.cmake"),
            recursive=True,
        ):
            with open(test_file) as f:
                content = f.read()
            if needle in content:
                with open(test_file, "w") as f:
                    f.write(content.replace(needle, replacement))

    def _prepare_ctest_runtime_links(self):
        # Published KF6/Qt6 binary packages embed build-tree-relative DT_NEEDED
        # entries ("../../bin/libKF6XXX.so"); mirror the expected layout with a
        # symlink farm next to the build folder (kxmlgui/ktextwidgets pattern).
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.lexists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    pass

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._self_sign_elfs()

    def _self_sign_elfs(self):
        # OHOS enforces ELF code signing at load time (freshly built .so in
        # the package folder -> dlopen EACCES until the .codesign section is
        # filled; cf. gulkan/0.15.1). Fully guarded, best effort: never
        # fails the build, skips when the SDK tool is absent.
        if str(self.settings.os) != "OHOS":
            return
        import glob as _glob
        import shutil
        import subprocess
        tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(tool):
            self.output.info("binary-sign-tool absent; skipping self-sign")
            return
        pkg = self.package_folder
        targets = (_glob.glob(os.path.join(pkg, "lib", "*.so*")) +
                   _glob.glob(os.path.join(pkg, "bin", "*")))
        signed = 0
        for path in targets:
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                out = path + ".signed"
                r = subprocess.run(
                    [tool, "sign", "-selfSign", "1", "-signAlg",
                     "SHA256withECDSA", "-inFile", path, "-outFile", out],
                    capture_output=True, timeout=60)
                if r.returncode == 0 and os.path.isfile(out):
                    shutil.copymode(path, out)
                    os.replace(out, path)
                    signed += 1
                else:
                    if os.path.isfile(out):
                        os.remove(out)
                    self.output.warn(
                        f"self-sign failed for {path} "
                        f"(rc={r.returncode}): {r.stderr.decode('utf-8', 'replace')[:120]}")
            except Exception as e:  # noqa: BLE001 - best effort by design
                self.output.warn(f"self-sign skipped for {path}: {e}")
        self.output.info(f"self-signed {signed} ELF file(s) in package")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6NewStuffCore", "KF6NewStuffWidgets"]
        self.cpp_info.includedirs = [
            os.path.join("include", "KF6", "KNewStuffCore"),
            os.path.join("include", "KF6", "KNewStuff"),
        ]
        # NOTE: bindirs intentionally not declared — the knewstuff-dialog6
        # demo is gated off (KF6::I18nQml guard), so the package ships no
        # executables (declaring bin/ would trip the R38/commands.json gate).
