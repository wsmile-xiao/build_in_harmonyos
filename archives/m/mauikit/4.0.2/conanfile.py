#!/usr/bin/env python3
"""Conan recipe for MauiKit 4.0.2 on HarmonyOS PC."""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class MauikitConan(ConanFile):
    name = "mauikit"
    version = "4.0.2"
    description = "Maui convergent QML controls library (org.mauikit.controls)"
    # The shipped LICENSES/ tree contains LGPL-3.0.txt for the library and QML
    # sources; the root CMakeLists SPDX header (GPL-3.0-or-later) covers the
    # build scripts. See notes.md for the license discussion.
    license = "LGPL-3.0-or-later"
    homepage = "https://invent.kde.org/maui/mauikit"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtmultimedia/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("knotifications/6.14.0")

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
        # BUILD_DEMO stays at the upstream default (OFF). BUNDLE_LUV_ICONS
        # would git clone the icon theme at configure time; it defaults to OFF
        # on platforms that are neither ANDROID, WIN32 nor APPLE, and HarmonyOS
        # is none of them - pin it anyway so the build never touches the net.
        tc.variables["BUILD_DEMO"] = "OFF"
        tc.variables["BUNDLE_LUV_ICONS"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        # ki18n_install(po) compiles the shipped .po files with msgfmt at
        # build time. Resolve the tool up front so the po processing does not
        # depend on the worker shell PATH.
        msgfmt = shutil.which("msgfmt")
        if not msgfmt and os.path.isfile("/data/service/hnp/bin/msgfmt"):
            msgfmt = "/data/service/hnp/bin/msgfmt"
        if msgfmt:
            tc.variables["GETTEXT_MSGFMT_EXECUTABLE"] = msgfmt

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        qt_extra = []
        for dep_name in ("qtdeclarative", "qtmultimedia", "qtsvg"):
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
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        # NOTE: mauikit 4.0.2 ships no upstream test suite (no autotests/ or
        # tests/ directory and no BUILD_TESTING switch in any CMakeLists), so
        # there is no upstream ctest to run here. The OHOS-specific
        # test_package below is the authoritative verification and must
        # actually execute during `conan create`.

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
        return '"' + str(value).replace('"', '\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
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
        if str(self.settings.os) == "OHOS":
            self._normalize_ohos_needed_names()
        self._sign_ohos_elf_tree(self.package_folder)

    def _normalize_ohos_needed_names(self):
        # CMake records the sibling build libraries of the QML plugins
        # (libMauiKit4plugin, libMauiStyleplugin -> libMauiKit4.so.4) as
        # ../bin/lib*.so. The OHOS loader treats a slash inside DT_NEEDED as a
        # path relative to the current working directory, so rewrite those
        # entries to bare sonames.
        #
        # The published kcoreaddons/ki18n/knotifications/qtmultimedia packages
        # ship libKF6*.so/libQt6Multimedia.so WITHOUT a DT_SONAME, so the
        # linker records their absolute build-time package path instead
        # (the same published-package gap the kio test_package bridges).
        # Rewrite those entries to bare basenames too; they then resolve
        # through the consumer LD_LIBRARY_PATH / DT_RPATH closure like every
        # other bare dependency soname.
        patterns = (
            re.compile(rb"\.\./(?:bin/)?(lib(?:MauiKit4|MauiStyle)[^/\x00]+)"),
            re.compile(rb"/[^\x00]*/(lib(?:KF6|Qt6)[A-Za-z0-9_.+-]*\.so(?:\.[0-9]+)*)"),
        )
        for library in glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True):
            with open(library, "rb") as f:
                data = f.read()

            def replace(match):
                name = match.group(1)
                return name + b"\x00" * (len(match.group(0)) - len(name))

            normalized = data
            replacements = 0
            for pattern in patterns:
                normalized, count = pattern.subn(replace, normalized)
                replacements += count
            if replacements:
                with open(library, "wb") as f:
                    f.write(normalized)
                self.output.info(
                    f"Normalized {replacements} DT_NEEDED entr(y/ies) in {os.path.basename(library)}"
                )

    def _runtime_env(self, include_build=False):
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
                env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml")
                )
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def _qml_dirs(self):
        dirs = []
        for rel in ("qml", os.path.join("lib", "qml"), os.path.join("lib", "qt6", "qml")):
            path = os.path.join(self.package_folder, rel)
            if os.path.isdir(path):
                dirs.append(path)
        return dirs

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        # Three shared objects ship: the core library plus the two QML plugin
        # libraries. Only the core library is a linkable CMake target
        # (MauiKit4::Controls); the plugins are consumed through the QML
        # import path.
        self.cpp_info.libs = ["MauiKit4"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        for qml_dir in self._qml_dirs():
            self.runenv_info.prepend_path("QML2_IMPORT_PATH", qml_dir)
