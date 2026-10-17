#!/usr/bin/env python3
"""Conan recipe for libkgapi 26.04.0 on HarmonyOS PC (aarch64-linux-ohos).

libkgapi (KPim6GAPI) is the KDE PIM Google API client library. It builds
five shared libraries (KPim6GAPICore, GAPICalendar, GAPIDrive, GAPILatitude,
GAPIPeople, GAPIBlogger, GAPIStaticMaps, GAPITasks) plus an optional SASL
plugin (disabled: co-installability only, cyrus-sasl plugin surface is not
consumed on this platform).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE bypasses the KDE platform allowlist
    (OHOS is not in KDE's platform list)
  - KF_MIN_VERSION lowered 6.22.0 -> 6.18.0 via patch: the published ohpcd
    KF6 stack is 6.18/6.26 (kwallet 6.18.0, kcontacts 6.18.0) and only the
    minimum version plate differs, no API gap is consumed by libkgapi
  - BUILD_SASL_PLUGIN=OFF: cyrus-sasl plugin is optional upstream
  - BUILD_TESTING=ON and full ctest execution: upstream registers 48 CTest
    entries (QtTest executables driven by ECMAddTests, offline fake network
    layer, no live Google access needed)
  - Dependencies: qtbase/6.11.1.2 (Qt6Core/Network/Gui/Widgets/Xml/Test),
    kwallet/6.18.0 (KF6::Wallet account secret storage),
    kcalendarcore/6.26.0 (KF6CalendarCore), kcontacts/6.18.0 (KF6Contacts),
    ecm/6.26.0 (ECM tool_requires)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibkgapiConan(ConanFile):
    name = "libkgapi"
    version = "26.04.0"
    description = "KDE PIM Google API client library (KPim6GAPI: Calendar/Drive/Tasks/People/Latitude/Blogger/StaticMaps)"
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/pim/libkgapi"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # force: transitive kconfig/kwallet require qtbase/6.11.1 (no binary
        # on the remote), align the whole graph onto the published 6.11.1.2
        self.requires("qtbase/6.11.1.2", force=True)
        self.requires("kwallet/6.18.0")
        self.requires("kcalendarcore/6.26.0")
        self.requires("kcontacts/6.18.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_SASL_PLUGIN"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        """qtbase/kwallet/kcalendarcore/kcontacts use cmake_find_mode=none:
        CMakeDeps does not add their lib/cmake dirs to CMAKE_PREFIX_PATH, so
        wire them up manually (kcalendarcore 6.26.0 precedent)."""
        prefixes = []
        libraries = []
        includes = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            add_unique(prefixes, ecm_cmake)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _build_env(self):
        build_env = self._runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # Sandbox LD_LIBRARY_PATH carries an incompatible libc++_shared.so
            # which shadows the compatible one; prepend /system/lib64 so the
            # loader resolves the compatible libc++ first (kcalendarcore
            # 6.26.0 / kconfig 6.26.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _runtime_env(self):
        runtime_env = Environment()
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        for rel in ("bin", "lib", "src", "autotests"):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._build_env()
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        # OHOS runtime has no /usr/share/zoneinfo; QTimeZone("Europe/Prague")
        # would fall back to a UTC-offset string and fail 3 upstream tests.
        # Point TZDIR at the zoneinfo database shipped by qtbase (its unix
        # QTimeZone backend honours TZDIR).
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.ref.name == "qtbase":
                zoneinfo = os.path.join(dep.package_folder, "share", "zoneinfo")
                if os.path.isdir(zoneinfo):
                    test_env.define("TZDIR", zoneinfo)
                break
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
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
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        # 1. Test executables live in <build>/bin and record the KGAPI
        #    libraries through relative sonames like ../bin/libKPim6GAPICore.so
        #    (KDE install rpath is stripped on OHOS); make that path resolvable
        #    from the CTest CWD (<build>/autotests) by linking into
        #    <build>/../bin (kcalendarcore 6.26.0 precedent).
        # 2. Dependency libraries ship relative sonames on OHOS
        #    ("./libical.so" from libical, "../../bin/libKF6I18n.so" from
        #    ki18n's libKF6I18nLocaleData): the musl loader resolves
        #    DT_NEEDED entries containing a slash from the process CWD, not
        #    from LD_LIBRARY_PATH. The CTest CWD is <build>/autotests, so
        #    drop copies of every dependency library into <build>/autotests,
        #    <build> and <build>/../bin to cover ./, ../ and ../../ relative
        #    sonames (kcalendarcore 6.26.0 precedent).
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        target_dirs = [
            os.path.join(self.build_folder, "autotests"),
            self.build_folder,
            compatibility_bin,
        ]
        for target_dir in target_dirs:
            os.makedirs(target_dir, exist_ok=True)
        lib_names = [
            "libKPim6GAPICore.so",
            "libKPim6GAPICalendar.so",
            "libKPim6GAPIDrive.so",
            "libKPim6GAPILatitude.so",
            "libKPim6GAPIPeople.so",
            "libKPim6GAPIBlogger.so",
            "libKPim6GAPIStaticMaps.so",
            "libKPim6GAPITasks.so",
        ]
        lib_sources = [os.path.join(self.build_folder, "bin", name) for name in lib_names]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            if not os.path.isfile(src) or os.path.islink(src):
                continue
            for target_dir in target_dirs:
                dst = os.path.join(target_dir, os.path.basename(src))
                if os.path.exists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder, "package")

    # ---- OHOS ELF signing (kwallet 6.18.0 precedent) ----

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
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder, label):
        if str(self.settings.os) != "OHOS":
            return
        if not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "Cannot locate OHOS llvm-objcopy/binary-sign-tool for ELF signing"
            )
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
                try:
                    os.chmod(path, 0o755)
                except OSError as exc:
                    self.output.warning(f"chmod signed ELF skipped for {path}: {exc}")
                signed += 1
        self.output.info(f"Signed {signed} OHOS {label} ELF file(s)")

    def package_info(self):
        # The project installs its own KPim6GAPIConfig.cmake with proper
        # dependency tracking; use cmake_find_mode=none so CMakeDeps does not
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = [
            "KPim6GAPICore",
            "KPim6GAPICalendar",
            "KPim6GAPIDrive",
            "KPim6GAPILatitude",
            "KPim6GAPIPeople",
            "KPim6GAPIBlogger",
            "KPim6GAPIStaticMaps",
            "KPim6GAPITasks",
        ]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
