#!/usr/bin/env python3
"""Conan recipe for kiconthemes 6.26.0 on HarmonyOS PC.

kiconthemes is a KDE Frameworks 6 library providing icon theme support
(libKF6IconThemes.so). This is a version bump of the 6.18.0.1 recipe onto
the KF6 6.26 baseline (task #6386), following the 7-point pattern shared
by the other 6.26 chain packages (kitemviews PR #8491 precedent).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - BUILD_WITH_QML=OFF / Qml Quick disabled (Qt6 Qml not published to ohpcd)
  - USE_DBUS=OFF (Qt6 DBus not published to ohpcd)
  - USE_BreezeIcons=OFF: KF6BreezeIcons is not published to ohpcd
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalog generation for the
    KF 6.26 baseline
  - BUILD_TESTING=ON and ctest execution for upstream autotests available in
    the current headless feature set
  - Dependencies: qtbase/6.11.1, qtsvg/6.11.1 (Qt6Svg), karchive/6.26.0,
    openssl/3.5.6.1 and zstd/1.5.7 (karchive KF6ArchiveTargets PkgConfig
    consumer deps), ki18n/6.26.0, kwidgetsaddons/6.26.0,
    kcolorscheme/6.26.0, ecm/6.26.0
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
  - /system/lib64 prepended to LD_LIBRARY_PATH for configure and test runs
    (sandbox libc++_shared.so shadowing, kconfig 6.26.0 / bluez-qt 6.28.0
    precedent)
"""
import os
import glob
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KiconthemesConan(ConanFile):
    name = "kiconthemes"
    version = "6.26.0"
    description = "KDE Frameworks 6 - KDE Icon Themes"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kiconthemes"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("karchive/6.26.0")
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
        self.requires("ki18n/6.26.0")
        self.requires("kwidgetsaddons/6.26.0")
        self.requires("kcolorscheme/6.26.0")

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
        # Qt6 Qml/Quick and DBus are not published to ohpcd; disable them.
        tc.variables["KICONTHEMES_USE_QTQUICK"] = "OFF"
        tc.variables["USE_DBUS"] = "OFF"
        # The KF 6.26 baseline does not ship translated catalog payload.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # KF6BreezeIcons is not published to ohpcd; disable the Breeze icon
        # bundle requirement (icons still resolve from user themes).
        tc.variables["USE_BreezeIcons"] = "OFF"
        # Qt Designer plugin requires Qt6UiPlugin, which is not published to
        # ohpcd; disable it explicitly.
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

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
            # Add every dependency's lib/cmake dir so find_package(Qt6Svg/
            # KF6Archive/KF6I18n/KF6WidgetsAddons/KF6ColorScheme/KF6Config)
            # and transitive find_dependency() chains all resolve.
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
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
            openssl = self.dependencies.get("openssl")
            if openssl and openssl.package_folder:
                openssl_pkg = openssl.package_folder
                lines.append(f'set(OPENSSL_ROOT_DIR "{openssl_pkg}" CACHE PATH "")')
                lines.append(
                    f'set(OPENSSL_INCLUDE_DIR "{openssl_pkg}/include" '
                    f'CACHE PATH "")'
                )
                lines.append(
                    f'set(OPENSSL_CRYPTO_LIBRARY '
                    f'"{openssl_pkg}/lib/libcrypto.a" CACHE FILEPATH "")'
                )
                lines.append(
                    f'set(OPENSSL_SSL_LIBRARY '
                    f'"{openssl_pkg}/lib/libssl.a" CACHE FILEPATH "")'
                )
            zstd = self.dependencies.get("zstd")
            if zstd and zstd.package_folder:
                zstd_pkg = zstd.package_folder
                zstd_libs = [
                    os.path.join(zstd_pkg, "lib", "libzstd.so"),
                    os.path.join(zstd_pkg, "lib", "libzstd.a"),
                ]
                zstd_lib = next(
                    (path for path in zstd_libs if os.path.exists(path)),
                    zstd_libs[0],
                )
                lines.append("if(NOT TARGET PkgConfig::LibZstd)")
                lines.append("  add_library(PkgConfig::LibZstd UNKNOWN IMPORTED)")
                lines.append(
                    "  set_target_properties(PkgConfig::LibZstd PROPERTIES"
                )
                lines.append(f'    IMPORTED_LOCATION "{zstd_lib}"')
                lines.append(
                    f'    INTERFACE_INCLUDE_DIRECTORIES "{zstd_pkg}/include"'
                )
                lines.append("  )")
                lines.append("endif()")
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

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure(variables={
                "KICONTHEMES_USE_QTQUICK": "OFF",
                "USE_DBUS": "OFF",
                "BUILD_DESIGNERPLUGIN": "OFF",
            })
            cmake.build()
        self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
            # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
            # one; prepend /system/lib64 (and the qtbase lib dir, already added
            # by _library_runtime_env) so the loader resolves the compatible
            # libc++ first (kconfig 6.26.0 / bluez-qt 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

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
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(self.build_folder, "bin"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
            # which shadows the compatible one; prepend /system/lib64 so test
            # executables resolve the compatible libc++ first (kconfig 6.26.0
            # / bluez-qt 6.28.0 precedent, same fix as _cmake_build_env).
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
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
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '-E "^(kiconloader_unittest|kiconengine_unittest)$"'.format(
                    self.build_folder
                )
            )
            self.output.warning(
                "Running kiconloader_unittest subset; excluding one "
                "shared-mime-info dependent data row unavailable on OHOS."
            )
            self._run_qtest(
                "kiconloader_unittest",
                [
                    "testUnknownIconNotCached",
                    "testLoadIconCanReturnNull",
                    "testAppPicsDir",
                    "testAppPicsDir_KDE_icon",
                    "testLoadMimeTypeIcon:existing icon",
                    "testLoadMimeTypeIcon:octet-stream icon",
                    "testLoadMimeTypeIcon:non-existing icon",
                    "testLoadMimeTypeIcon:existing icon again",
                    "testLoadMimeTypeIcon:generic fallback",
                    "testLoadMimeTypeIcon:video generic fallback",
                    "testLoadMimeTypeIcon:image-x-generic itself",
                    "testLoadMimeTypeIcon:x-office-document icon",
                    "testLoadMimeTypeIcon:unavailable generic icon",
                    "testLoadMimeTypeIcon:#184852",
                    "testLoadMimeTypeIcon:#178847",
                    "testHasIcon",
                    "testIconPath",
                    "testCorrectFallback",
                    "testPathStore",
                    "testPathsNoContextType",
                    "testLoadIconNoGroupOrSize",
                    "testUnknownIcon",
                    "testAppropriateSizes",
                    "testColoredSvgIcon",
                    "testUintToHex",
                    "testQDirSetSearchPaths",
                    "testCorrectSymbolicFallback",
                ],
            )
            self.output.warning(
                "Running kiconengine_unittest subset; excluding testMode "
                "because BreezeIcons is disabled on OHOS."
            )
            self._run_qtest(
                "kiconengine_unittest",
                [
                    "testValidIconName",
                    "testInvalidIconName",
                    "testFallbackIconName",
                    "testUnknownIconNotCached",
                    "testCenterIcon",
                    "testNonSquareSvg",
                ],
            )

    def _qt_plugin_path(self):
        plugin_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                plugin_dir = os.path.join(dep.package_folder, "plugins")
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

    def _run_qtest(self, executable, cases):
        autotests_dir = os.path.join(self.build_folder, "autotests")
        executable_path = os.path.join(self.build_folder, "bin", executable)
        args = " ".join(shlex.quote(case) for case in cases)
        self.run(
            "cd {} && {} {}".format(
                shlex.quote(autotests_dir),
                shlex.quote(executable_path),
                args,
            )
        )

    def _prepare_ctest_runtime_links(self):
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
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

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

    def _normalize_ohos_needed_names(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        pattern = re.compile(rb"(?:/[^/\x00]+)+/(lib[^/\x00]+)")
        normalized_files = 0
        for library in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            if os.path.islink(library) or not self._is_elf(library):
                continue
            with open(library, "rb") as handle:
                data = handle.read()

            def replace(match):
                name = match.group(1)
                return name + b"\x00" * (len(match.group(0)) - len(name))

            normalized, replacements = pattern.subn(replace, data)
            if replacements:
                with open(library, "wb") as handle:
                    handle.write(normalized)
                normalized_files += 1
        self.output.info(
            f"Normalized absolute DT_NEEDED paths in {normalized_files} OHOS library file(s)"
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._normalize_ohos_needed_names()
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        # The project installs its own KF6IconThemesConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Svg etc). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6IconThemes"]
