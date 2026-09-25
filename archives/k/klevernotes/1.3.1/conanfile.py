#!/usr/bin/env python3
"""Conan recipe for klevernotes 1.3.1 on HarmonyOS PC.

klevernotes is the KDE note-taking application (Kirigami QML app, QML built
fully statically via ecm_add_qml_module(klevernotes_static ... GENERATE_PLUGIN_SOURCE)).

OHOS-specific adaptations (see patches/ for details):
  - KLEVER_WITH_WEBENGINE (default OFF): the upstream markdown preview and the
    PDF printing pipeline are hard-wired to QtWebEngine (WebEngineView +
    printToPdf + QtQuick.Pdf + Qt::WebChannel + Qt::PrintSupport/QPrinter).
    QtWebEngine is neither published to ohpcd nor portable there, so the
    WebEngine-based QML/sources are gated out and the preview degrades to a
    pure QML rich-text renderer (TextDisplayNative.qml); PrintingPage.qml and
    printingHelper.cpp (PrintingUtility) drop out of the OFF build.
  - KF_IGNORE_PLATFORM_CHECK=TRUE: OHOS is not in the KDE platform list.
  - KF_SKIP_PO_PROCESSING=ON: no gettext msgfmt on the OHOS workers.
  - The kirigami-addons/1.13.0 recipe pins the KF6 6.18.0 family while
    kio/6.26.0 pins the KF6 6.26.0 family; the root recipe resolves the
    expected version conflict with force=True overrides to the newer
    published generation (KF6 6.x is source- and binary-compatible within
    the major series, and the published 6.18 libraries the addons link
    against remain resolvable on the device cache).
  - BUILD_TESTING=ON: the three upstream QtTest suites (extendedSyntax,
    noteLinking, emoji) run for real via ctest inside conan create.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class KlevernotesConan(ConanFile):
    name = "klevernotes"
    version = "1.3.1"
    description = "KDE note-taking application (Kirigami QML application)"
    license = ("GPL-2.0-or-later", "GPL-3.0-or-later", "BSD-3-Clause", "CC-BY-4.0")
    homepage = "https://invent.kde.org/office/klevernotes"
    url = "https://download.kde.org/stable/klevernotes/1.3.1/klevernotes-1.3.1.tar.xz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # QML application package: the QML runtime (qtdeclarative) and the KF6 QML
    # modules (kirigami, kirigami-addons, kitemmodels) are required at runtime
    # and resolved through the consumers' runenv (QML2_IMPORT_PATH), so no
    # library exports.
    options = {}
    default_options = {}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 stack: qtbase-sql-dbus provides Core/Gui/Widgets/Test/Sql/DBus
        # (qtbase/6.11.1 does NOT ship PrintSupport — verified in the ohpcd
        # package; the PrintSupport consumer printingHelper.cpp is gated off
        # together with WebEngine). qtdeclarative provides
        # Qml/Quick/QuickControls2/Qt.labs.* QML modules.
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        # KF6 frameworks. klevernotes' CMake requires Kirigami, CoreAddons,
        # Config, I18n, ColorScheme, IconThemes, KIO; kirigami-addons and
        # kitemmodels are QML runtime deps the CMake never declares.
        self.requires("kirigami/6.18.0")
        self.requires("kirigami-addons/1.13.0")
        self.requires("kitemmodels/6.18.0.1")
        self.requires("kio/6.26.0")
        # force=True: kirigami-addons/1.13.0 pins these to the 6.18.0 family
        # while kio/6.26.0 pulls the 6.26.0 family; the root override keeps
        # one version per package in the graph (KF6 6.x intra-major compat).
        self.requires("kcoreaddons/6.26.0", force=True)
        self.requires("kconfig/6.26.0", force=True)
        self.requires("ki18n/6.26.0", force=True)
        self.requires("kcolorscheme/6.26.0", force=True)
        self.requires("kiconthemes/6.26.0", force=True)
        self.requires("kcrash/6.26.0", force=True)
        self.requires("kguiaddons/6.26.0", force=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Upstream tests: three QtTest parser suites (extendedSyntax,
        # noteLinking, emoji) registered by src/autotests/CMakeLists.txt.
        tc.variables["BUILD_TESTING"] = "ON"
        # OHOS: no QtWebEngine -> degraded preview, no QtQuick.Pdf print page.
        tc.variables["KLEVER_WITH_WEBENGINE"] = "OFF"
        # OHOS: qqc2-desktop-style (org.kde.desktop QQC2 style) is not
        # published to ohpcd; use the built-in Basic style instead.
        tc.variables["KLEVER_QQC2_DESKTOP_STYLE"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        qt_extra = []
        for dep_name in ("qtdeclarative", "qtsvg"):
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

    def _configure_ohos_shared_library_rules(self, toolchain):
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
            )) + "\n",
        )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
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
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os in ("OHOS", "HarmonyOS"):
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _test_env(self):
        """Environment for the upstream QtTest suites (ctest).

        The test binaries link klevernotes_static, so they carry the whole
        Qt6/KF6 link closure as DT_NEEDED and need
          * the OHOS Qt host runtime on LD_LIBRARY_PATH (KF6 packages
            install under bin/, Qt under lib/),
          * a link farm for build-tree-relative DT_NEEDED entries (E537),
          * writable HOME/XDG dirs for KConfig/KSycoca side effects.
        The parser suites themselves are QML-free.
        """
        test_env = self._runtime_env(include_build=False)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                # KF6 packages (kirigami, ki18n, ...) install shared libs under bin/.
                test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin"))
        for rel in ("bin", "lib"):
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        test_env.prepend_path("QML2_IMPORT_PATH", os.path.join(self.build_folder, "bin"))
        self._make_link_farm()
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
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        return test_env

    def _make_link_farm(self):
        # E537: published KF6 libraries can carry build-tree-relative
        # DT_NEEDED entries ("../bin/libKF6*.so", "../../bin/libKF6*.so")
        # which the OHOS loader resolves against the process CWD. ctest runs
        # from <build>/Release, so "../bin" reaches <build>/bin and
        # "../../bin" reaches <build>/../bin; mirror the expected layout with
        # farms of every dependency shared library at every reachable level
        # (accessibility 26.04.3 / calligra 24.12.3 precedent).
        build = self.build_folder.rstrip(os.sep)
        farm_roots = [
            os.path.join(build, "bin"),
            os.path.join(os.path.dirname(build), "bin"),
        ]
        farms = []
        for farm in farm_roots:
            try:
                os.makedirs(farm, exist_ok=True)
                farms.append(farm)
            except OSError as exc:
                self.output.warning(f"link farm mkdir failed ({farm}): {exc}")
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for layout_dir in ("lib", "bin"):
                src_dir = os.path.join(dep.package_folder, layout_dir)
                if not os.path.isdir(src_dir):
                    continue
                for name in os.listdir(src_dir):
                    if not name.endswith(".so"):
                        continue
                    for farm in farms:
                        link = os.path.join(farm, name)
                        if not os.path.lexists(link):
                            try:
                                os.symlink(os.path.join(src_dir, name), link)
                            except OSError as exc:
                                self.output.warning(f"link farm entry {name} failed: {exc}")

    def _run_upstream_tests(self):
        # The three upstream QtTest suites (klevernotes-extendedSyntax,
        # klevernotes-noteLinking, klevernotes-emoji) run for real here.
        with self._test_env().vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        # E077: the OHOS HMDFS W^X policy refuses to load ELF files that were
        # written after build unless they are (re)signed; remove the stale
        # .codesign section and self-sign every packaged ELF.
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}", ignore_errors=True)
                self.run(f"{self._quote(signer)} sign -inFile {self._quote(path)} -outFile {self._quote(path)} -selfSign 1")
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

    def _runtime_env(self, include_build=False):
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                # Qt host tools (qmltyperegistrar/qmlcachegen/qsb) live in
                # libexec/ next to the Qt libraries they need at runtime.
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml"))
        # The host shell LD_LIBRARY_PATH carries whitespace-padded entries
        # (".../chipset-pub-sdk:         /system/lib64") which the OHOS loader
        # cannot resolve. Provide clean system library dirs explicitly so Qt
        # host tools keep working inside the build env.
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"):
            env.append_path("LD_LIBRARY_PATH", system_lib)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package_info(self):
        # QML application package: the binary is resolved through bindirs and
        # the QML runtime through the runenv (QML2_IMPORT_PATH), so no library
        # exports are needed here.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, "bin"))
