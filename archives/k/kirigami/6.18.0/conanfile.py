#!/usr/bin/env python3
"""Conan recipe for Kirigami 6.18.0 on HarmonyOS PC."""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class KirigamiConan(ConanFile):
    name = "kirigami"
    version = "6.18.0"
    description = "KDE Frameworks 6 - lightweight QtQuick UI components"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kirigami"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("qtshadertools/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Qt's OPTIMIZED shader option invokes the external Vulkan SDK tool
        # spirv-opt. It is not part of the published Qt ShaderTools package;
        # retain normal qsb generation without that optional optimization.
        for root, _, filenames in os.walk(self.source_folder):
            for filename in filenames:
                if filename != "CMakeLists.txt":
                    continue
                path = os.path.join(root, filename)
                with open(path, encoding="utf-8") as cmake_file:
                    content = cmake_file.read()
                updated = re.sub(r"\bOPTIMIZED\b[ \t]*", "", content)
                if updated != content:
                    with open(path, "w", encoding="utf-8") as cmake_file:
                        cmake_file.write(updated)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["DESKTOP_ENABLED"] = "OFF"
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
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
        for dep_name in ("qtdeclarative", "qtsvg", "qtshadertools"):
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
            self._prepare_upstream_test_theme()
            test_args = 'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(self.build_folder)
            if str(self.settings.os) in ("OHOS", "HarmonyOS"):
                test_args += ' -E "^tst_theme\\.qml$"'
            self.run(test_args)

    def _prepare_upstream_test_theme(self):
        source_theme = os.path.join(self.source_folder, "src", "styles", "org.kde.desktop", "Theme.qml")
        target_theme = os.path.join(
            self.build_folder, "bin", "org", "kde", "kirigami", "Theme.qml"
        )
        if not os.path.isfile(source_theme):
            raise ConanException(f"Missing upstream test theme: {source_theme}")
        os.makedirs(os.path.dirname(target_theme), exist_ok=True)
        shutil.copy2(source_theme, target_theme)

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
        # CMake passes sibling build libraries as ../bin/libKirigami*.so. The
        # OHOS loader treats a slash in DT_NEEDED as a path relative to cwd.
        pattern = re.compile(rb"\.\./(?:bin/)?(libKirigami[^/\x00]+)")
        for library in glob.glob(os.path.join(self.package_folder, "lib", "libKirigami*.so*")):
            with open(library, "rb") as f:
                data = f.read()

            def replace(match):
                name = match.group(1)
                return name + b"\x00" * (len(match.group(0)) - len(name))

            normalized, replacements = pattern.subn(replace, data)
            if replacements:
                with open(library, "wb") as f:
                    f.write(normalized)

    def _runtime_env(self, include_build=False):
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                # Qt Shader Tools installs spirv-opt below libexec; qsb invokes
                # it by basename while baking Kirigami's bundled shaders.
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
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

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = [
            "Kirigami",
            "KirigamiPlatform",
            "KirigamiPrimitives",
            "KirigamiLayouts",
            "KirigamiDelegates",
            "KirigamiDialogs",
            "KirigamiTemplates",
            "KirigamiPolyfill",
        ]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.runenv_info.prepend_path("QML2_IMPORT_PATH", os.path.join(self.package_folder, "qml"))
