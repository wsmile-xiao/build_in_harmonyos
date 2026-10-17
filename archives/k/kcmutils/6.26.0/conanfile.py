#!/usr/bin/env python3
"""Conan recipe for kcmutils 6.26.0 on HarmonyOS PC.

kcmutils is a KDE Frameworks 6 library providing utilities for
configuration modules (libKF6KCMUtils.so, libKF6KCMUtilsCore.so,
libKF6KCMUtilsQuick.so + the kcmshell6 runner).

OHOS-specific adaptations (6.26.0):
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS not in the KDE platform list)
  - KCMUTILS_BUILD_QML_PLUGIN left off: the declarative kcmutilsqmlplugin
    is not built because it links KF6::KIOGui and kio/6.26.0 on ohpcd ships
    a KIOCORE_ONLY baseline (no KIOGui target). The QML KCM test fixture and
    the QML-plugin loader autotest row are guarded behind the same switch
    (patch 0001).
  - KF6ConfigWidgets dependency floor lowered 6.26.0 -> 6.18.0 (patch 0001):
    kconfigwidgets is only published at 6.18.0 on ohpcd; the rest of the KF6
    chain uses the 6.26.0 line with conan override entries (kxmlgui 6.26.0
    precedent, task #13725).
  - USE_DBUS=OFF (Qt6 DBus only used by optional kcmshell6 integration)
  - BUILD_TESTING=ON: upstream autotests run on the local arm64 OHOS runner
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KCMUtilsConan(ConanFile):
    name = "kcmutils"
    version = "6.26.0"
    description = "KDE Frameworks 6 - utilities for configuration modules"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kcmutils"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase-sql-dbus provides Core/Gui/Widgets/Test/Sql/DBus; the
        # declarative stack (Qml/Quick/QuickWidgets) comes from
        # qtdeclarative (alkimia #9350 / alligator #9578 precedent).
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        # KF6 6.26 line. override=True entries are single declarations: they
        # pin the whole graph to this version and add it as a direct
        # requirement (a duplicated plain requires is rejected by conan).
        # The overrides redirect kconfigwidgets/6.18.0's transitive 6.18
        # pins to the 6.26 line (kxmlgui 6.26.0 precedent).
        self.requires("kio/6.26.0")
        self.requires("kxmlgui/6.26.0")
        self.requires("kitemviews/6.26.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        # kio -> karchive/kservice chain: KF6ArchiveConfig activates
        # find_dependency(OpenSSL)/PkgConfig::LibZstd; libxml2 is needed by
        # the OHOS SDK lld at link time (kio 6.26.0 precedent).
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
        self.requires("libxml2/2.15.3")

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
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        # Qt6Qml/Qt6Quick/Qt6QuickWidgets live in the qtdeclarative package;
        # Qt discovers additional components through the official
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH hook (kdeclarative 6.26.0
        # precedent). Without it find_package(Qt6 ... Qml) resolves the
        # qtbase Qt6Config.cmake first and fails on the missing component.
        qt_extra = []
        qtdecl = self.dependencies.get("qtdeclarative")
        if qtdecl and qtdecl.package_folder:
            qt_extra.append(qtdecl.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )
        self._write_cmake_paths()
        tc.generate()

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
        # Platform guard: apply OHOS-specific patches only on OHOS.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        self._bake_needed_path_stubs()
        self._prepare_ctest_runtime_links()
        test_env = self._runtime_env(include_build=True)
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
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _bake_needed_path_stubs(self):
        """Fix CI-fatal DT_NEEDED absolute paths baked into published
        binary packages (kio/kxmlgui 6.26.0 line).

        The published libKF6XmlGui.so (and siblings) record absolute
        DT_NEEDED entries pointing at the *build-time* conan cache
        package dirs (e.g. /root/.cache/conan2/p/b/kconfXXXX/p/lib/
        libKF6ConfigWidgets.so). On any other machine (CI worker or
        local runner) those paths do not exist and the loader aborts
        with "Error loading shared library" before LD_LIBRARY_PATH is
        even consulted (absolute DT_NEEDED bypasses the search path).

        Fix: scan every dependency .so for absolute DT_NEEDED entries;
        for each one whose file does not exist, create the exact parent
        directory and symlink the actually-available same-named library
        from the real dependency package into it. Paths outside the
        user-writable home or system roots are skipped.
        """
        import re
        import struct

        def _needed_entries(so_path):
            """Parse DT_NEEDED from the .dynamic section (readelf-free)."""
            try:
                with open(so_path, "rb") as f:
                    data = f.read()
            except OSError:
                return []
            if data[:4] != b"\x7fELF":
                return []
            is64 = data[4] == 2
            if not is64:
                return []
            e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
            e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
            dyn_off = dyn_sz = 0
            dynstr_off = 0
            for i in range(e_shnum):
                sh = e_shoff + i * e_shentsize
                sh_type = struct.unpack_from("<I", data, sh + 4)[0]
                if sh_type == 6:  # SHT_DYNAMIC
                    dyn_off = struct.unpack_from("<Q", data, sh + 0x18)[0]
                    dyn_sz = struct.unpack_from("<Q", data, sh + 0x20)[0]
                elif sh_type == 3:  # SHT_STRTAB (first one is .dynstr in practice)
                    if dynstr_off == 0:
                        dynstr_off = struct.unpack_from("<Q", data, sh + 0x18)[0]
            if not dyn_off or not dynstr_off:
                return []
            needed = []
            count = dyn_sz // 16
            for i in range(count):
                d_tag = struct.unpack_from("<Q", data, dyn_off + i * 16)[0]
                d_val = struct.unpack_from("<Q", data, dyn_off + i * 16 + 8)[0]
                if d_tag == 1:  # DT_NEEDED
                    end = data.index(b"\x00", dynstr_off + d_val)
                    name = data[dynstr_off + d_val : end].decode("utf-8", "replace")
                    needed.append(name)
            return needed

        # Collect every .so we can see (dependency packages + our build).
        so_files = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                so_files.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        so_files.extend(glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*")))

        # Index available libraries by basename for symlink targets.
        available = {}
        for path in so_files:
            available[os.path.basename(path)] = path

        stubs = 0
        for so in so_files:
            for needed in _needed_entries(so):
                if not needed.startswith("/"):
                    continue  # relative NEEDED goes through the search path
                if os.path.exists(needed):
                    continue  # already resolvable
                base = os.path.basename(needed)
                target = available.get(base)
                if not target:
                    continue
                parent = os.path.dirname(needed)
                home = os.path.expanduser("~")
                if not (parent.startswith(home) or parent.startswith("/data")):
                    continue  # outside writable roots; skip
                try:
                    os.makedirs(parent, exist_ok=True)
                    dst = needed
                    if not os.path.lexists(dst):
                        os.symlink(target, dst)
                        stubs += 1
                except OSError:
                    continue
        if stubs:
            self.output.info(
                "baked DT_NEEDED path stubs created: %d" % stubs
            )

    def _prepare_ctest_runtime_links(self):
        """KF6 libraries record build-tree-relative DT_NEEDED entries
        (../../bin/libKF6*.so); mirror the expected layout by symlinking
        every KF6 shared library into the build tree compatibility
        locations (kxmlgui 6.26.0 precedent)."""
        import glob
        import shutil as _shutil
        # Test executables live at different depths (autotests/,
        # autotests/module_data_codegen/); their DT_NEEDED entries use
        # build-tree-relative paths (../bin, ../../bin). Symlink the KF6
        # libraries into every plausible resolution point.
        compatibility_dirs = {
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "lib"),
            os.path.normpath(os.path.join(self.build_folder, "autotests", "bin")),
            os.path.normpath(os.path.join(self.build_folder, "autotests", "module_data_codegen", "bin")),
            os.path.normpath(os.path.join(self.build_folder, "autotests", "module_data_codegen", "..", "..", "bin")),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, "bin")),
        }
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for cdir in compatibility_dirs:
            os.makedirs(cdir, exist_ok=True)
        for src in lib_sources:
            for cdir in compatibility_dirs:
                dst = os.path.join(cdir, os.path.basename(src))
                if os.path.exists(src) and not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        _shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()

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
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        # The kcmutilsqmlplugin is not part of the OHOS baseline (KIOGui not
        # published); only the three libraries are shipped.
        self.cpp_info.libs = ["KF6KCMUtils", "KF6KCMUtilsCore", "KF6KCMUtilsQuick"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
