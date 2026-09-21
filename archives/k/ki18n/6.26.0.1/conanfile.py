#!/usr/bin/env python3
"""Conan recipe for ki18n 6.26.0.1 on HarmonyOS PC.

ki18n is the KDE Frameworks 6 gettext-based UI internationalization library
(libKF6I18n, libKF6I18nLocaleData) and, since KF 6.21, the QML module
``org.kde.ki18n`` (libKF6I18nQml + the ``KI18n`` QML singleton), used by
Kirigami/QtQuick applications (kirigami-app 1.0.1).

Adaptation history:
  - 6.18.0.1 : enabled the QML i18n add-on (BUILD_WITH_QML=ON) but upstream
               6.18 has no ``org.kde.ki18n`` QML module yet (it was introduced
               in 6.21), so it shipped only libKF6I18nQml.so. Its QML plugin
               also recorded the build-tree relative path
               ``../../bin/libKF6I18n.so`` in DT_NEEDED, which the OHOS loader
               treats as a cwd-relative path and cannot resolve.
  - 6.26.0.1 : re-bases on the published ki18n/6.26.0 and applies the same
               hardening as kitemmodels/6.18.0.1 (PR #10520) and
               kirigami/6.26.0 (PR #10787): restore SONAME/rpath emission so
               the QML plugin records the bare SONAME instead of a relative
               build path, and re-sign every packaged ELF after CMake rewrote
               its RUNPATH. This revision ships the QML module tree
               ``lib/qml/org/kde/ki18n`` (qmldir + plugin .so + .qmltypes).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE: HarmonyOS is not in the KDE platform list.
  - BUILD_WITH_QML=ON: qtdeclarative/6.11.1 (Qt6::Qml) is published and is a
    hard requirement here so src/i18n-qml and src/localedata-qml are built.
  - KF_SKIP_PO_PROCESSING=ON: skips ki18n's own translation catalog build.
  - BUILD_TESTING=ON and ctest execution of the upstream autotests (R51).
  - FOUR locale-data autotests (kcatalogtest/kcountrytest/
    kcountrysubdivisiontest/ktimezonetest) are excluded: they require the
    optional runtime IsoCodes JSON data set (iso-codes), which is not part of
    the published OHOS packages; every other upstream test runs.
  - ECM_MODULE_PATH is set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project relies on.
  - qtbase and qtdeclarative both ship complete relocatable Qt6*Config.cmake
    files with cmake_find_mode=none, so their lib/cmake dirs are PREPENDed to
    CMAKE_PREFIX_PATH through a hand-written conan_cmakedeps_paths.cmake.
  - The Qt host tools (qmltyperegistrar/qmlcachegen from qtdeclarative, moc/rcc
    from qtbase) have a RUNPATH pointing only at their own package and still
    NEED libQt6Core.so.6 from qtbase; the dependency lib/bin/libexec dirs are
    therefore put on LD_LIBRARY_PATH/PATH while configure/build/install run.
  - OHOS CMake emits no SONAME by default, so a QML plugin linked against a
    sibling build-tree library records ``../../bin/libKF6I18n.so`` in
    DT_NEEDED. Restore the SONAME/rpath flags via
    CMAKE_USER_MAKE_RULES_OVERRIDE (kitemmodels 6.18.0.1 precedent).
  - CMake rewrites the RUNPATH of installed shared libraries, which invalidates
    the OHOS build-time ``.codesign`` section; every packaged ELF is re-signed
    with llvm-objcopy + binary-sign-tool (kitemmodels 6.18.0.1 / kirigami
    6.26.0 precedent).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


class Ki18nConan(ConanFile):
    name = "ki18n"
    version = "6.26.0.1"
    description = "KDE Frameworks 6 - gettext-based UI internationalization + QML module org.kde.ki18n"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/ki18n"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6Core (+ Qt6Widgets used by the optional spinbox test tool).
        self.requires("qtbase/6.11.1")
        # Qt6Qml/Qt6Quick: required to build the org.kde.ki18n QML module.
        self.requires("qtdeclarative/6.11.1")
        # libintl is part of gettext; msgfmt is also needed by the
        # ki18n_install upstream autotest.
        self.requires("gettext/0.22.5.1")

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
        # Qt6 Qml is available via qtdeclarative/6.11.1: build and ship the
        # QML module org.kde.ki18n needed by kirigami-app.
        tc.variables["BUILD_WITH_QML"] = "ON"
        # ki18n's own translated catalog payload is not needed for the build.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        qt_prefixes = []
        for name in ("qtbase", "qtdeclarative"):
            dep = self.dependencies.get(name)
            if dep and dep.package_folder:
                qt_prefixes.append(dep.package_folder)
        if qt_prefixes:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_prefixes)

        self._write_cmake_paths()
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        """OHOS CMake does not emit a SONAME for shared libraries by default.
        Without a SONAME a QML plugin records the build-tree relative path
        (../../bin/libKF6I18n.so) in DT_NEEDED, which the OHOS loader treats as
        a cwd-relative path and fails to resolve. Restore the soname/rpath flags
        (kitemmodels 6.18.0.1 / kirigami 6.18.0 precedent)."""
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
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _dependency_runtime_env(self, include_build=False):
        """Runtime env for the split Qt packages. The Qt host tools and the
        freshly built QML plugins need every dependency lib dir on
        LD_LIBRARY_PATH, and gettext's msgfmt must be on PATH for the
        ki18n_install upstream autotest."""
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                prefix = dep.package_folder
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "bin"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "libexec"))
                env.prepend_path("PATH", os.path.join(prefix, "bin"))
                env.prepend_path("PATH", os.path.join(prefix, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(prefix, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(prefix, "lib", "plugins"))
                for rel in ("qml", "lib/qml", "share/qml"):
                    env.prepend_path("QML2_IMPORT_PATH", os.path.join(prefix, rel))
                    env.prepend_path("QML_IMPORT_PATH", os.path.join(prefix, rel))
        return env

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._dependency_runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_env = self._dependency_runtime_env(include_build=False)
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

        for rel in ("bin", "lib", os.path.join("src", "lib")):
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))

        # QML modules built in the build tree (org.kde.ki18n, the
        # org.kde.i18n.declarativetest helper module) are only reachable if
        # their import root is on the QML import path.
        seen_roots = set()
        for base in (self.build_folder, self.source_folder):
            for root, _dirs, files in os.walk(base):
                if "qmldir" in files:
                    import_root = os.path.dirname(root)
                    if import_root not in seen_roots:
                        seen_roots.add(import_root)
                        test_env.prepend_path("QML2_IMPORT_PATH", import_root)
                        test_env.prepend_path("QML_IMPORT_PATH", import_root)

        # These four need the optional runtime IsoCodes JSON data set
        # (iso-codes), which is not published for OHOS.
        excluded_tests = (
            "kcatalogtest",
            "kcountrytest",
            "kcountrysubdivisiontest",
            "ktimezonetest",
        )
        self.output.info(
            "Excluding upstream tests requiring unavailable OHOS iso-codes data: "
            + ", ".join(excluded_tests)
        )
        exclude_re = "^({})$".format("|".join(excluded_tests))
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -E "{}"'.format(
                    self.build_folder, exclude_re
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
        """CMake rewrites the RUNPATH of installed shared libraries, which
        invalidates the OHOS build-time .codesign section. The OHOS loader then
        refuses to load the library ("Permission denied"). Re-sign every
        packaged ELF (kitemmodels 6.18.0.1 / kirigami 6.26.0 precedent)."""
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
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        cmake = CMake(self)
        with self._dependency_runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        # The project installs its own KF6I18nConfig.cmake with proper
        # dependency tracking (find_dependency(Qt6Core)). Use
        # cmake_find_mode=none so CMakeDeps does not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6I18n", "KF6I18nLocaleData", "KF6I18nQml"]
        # QML module org.kde.ki18n: consumers need the import root on their QML
        # import path (kirigami-app / akonadi consumers).
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
        self.runenv_info.prepend_path(
            "QML_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
