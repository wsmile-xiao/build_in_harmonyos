#!/usr/bin/env python3
"""Conan test_package for kinfocenter 6.7.2.

Consumer-side verification for the KCM plugin package:

* Part 1: KPluginFactory::loadFactory(kcm_cpu) — the exact mechanism
  systemsettings uses to instantiate kinfocenter KCMs at runtime
  (exercises the installed plugin .so + json metadata pair).
* Part 2: dlopen(libKInfoCenterInternal.so.1) and resolve the
  CommandOutputContext metaobject — the private library every
  command-output KCM links against.
* Part 3: verify the full expected installed KCM module set (the
  modules surviving the OHOS trim).

The runtime environment mirrors the kcmutils 6.26.0 / audiocd 26.04.3
precedents: relative DT_NEEDED entries baked into the published KF6
packages are resolved through compatibility symlinks and the OHOS
loader gets /system/lib64 for libc++_shared.so.
"""
import glob
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KInfoCenterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # KPluginFactory/KPluginMetaData + the KF6 closure needed to
        # resolve every DT_NEEDED of the loaded KCM plugins at runtime.
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("kcmutils/6.26.0")
        self.requires("kio/6.26.0")
        self.requires("kxmlgui/6.26.0")
        self.requires("kitemviews/6.26.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("solid/6.26.0")
        self.requires("kservice/6.26.0")
        self.requires("kauth/6.26.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
        self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2/kpeople5 precedent).
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        qt_extra = []
        qtdecl = self.dependencies.get("qtdeclarative")
        if qtdecl and qtdecl.package_folder:
            qt_extra.append(qtdecl.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        ecm_share = None
        # KF6CoreAddonsConfig requires nothing beyond what CMakeDeps
        # generates here; still give CMake the package prefixes.
        self._write_cmake_paths()
        tc.generate()

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefixes.extend([os.path.join(dep.package_folder, "lib", "cmake"), dep.package_folder])
                libraries.append(os.path.join(dep.package_folder, "lib"))
                includes.append(os.path.join(dep.package_folder, "include"))
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _build_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def test(self):
        self._bake_needed_path_stubs()
        self._prepare_runtime_links()
        package = None
        for dep in self.dependencies.values():
            if dep.ref.name == "kinfocenter" and dep.package_folder:
                package = dep.package_folder
                break
        if not package:
            raise RuntimeError("kinfocenter package folder not found in graph")

        test_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                test_env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                test_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                test_env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
        test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(package, "lib")
        )
        test_env.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(package, "lib", "plugins")
        )
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("KIC_TEST_PACKAGE_DIR", package)
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        test_env.define("HOME", test_home)
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))

        bindir = self.cpp.build.bindirs[0]
        cmd = os.path.join(bindir, "kinfocenter_consumer_test")
        with test_env.vars(self).apply():
            # cwd pinned to the test binary dir: the published KF6
            # libraries carry build-tree-relative DT_NEEDED entries
            # ("../bin/libKF6*.so", "../../bin/libKF6*.so") that the musl
            # loader resolves relative to the process CWD; the compat
            # dirs prepared below cover both depths from this CWD.
            self.run(f"{shlex.quote(cmd)}", env="conanrun", cwd=bindir)
            self.output.info("consumer test passed")

    def _bake_needed_path_stubs(self):
        """Fix CI-fatal DT_NEEDED absolute paths baked into published
        binary packages (kcmutils/kio 6.26.0 line) — same treatment as
        the main recipe's build().

        The published KF6 libraries record absolute DT_NEEDED entries
        pointing at their build-time conan cache package dirs; on any
        other machine the loader aborts before LD_LIBRARY_PATH is
        consulted.  Scan every dependency .so for absolute DT_NEEDED
        entries; for each whose file does not exist, create the exact
        parent directory and symlink the actually-available same-named
        library from the real dependency package into it.  Paths outside
        the user-writable home or system roots are skipped.
        """
        import struct

        def _needed_entries(so_path):
            try:
                with open(so_path, "rb") as f:
                    data = f.read()
            except OSError:
                return []
            if data[:4] != b"\x7fELF":
                return []
            if data[4] != 2:
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
                elif sh_type == 3:  # SHT_STRTAB
                    if dynstr_off == 0:
                        dynstr_off = struct.unpack_from("<Q", data, sh + 0x18)[0]
            if not dyn_off or not dynstr_off:
                return []
            needed = []
            for i in range(dyn_sz // 16):
                d_tag = struct.unpack_from("<Q", data, dyn_off + i * 16)[0]
                d_val = struct.unpack_from("<Q", data, dyn_off + i * 16 + 8)[0]
                if d_tag == 1:  # DT_NEEDED
                    end = data.index(b"\x00", dynstr_off + d_val)
                    needed.append(
                        data[dynstr_off + d_val : end].decode("utf-8", "replace")
                    )
            return needed

        so_files = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                so_files.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        available = {}
        for path in so_files:
            available[os.path.basename(path)] = path
        stubs = 0
        for so in so_files:
            for needed in _needed_entries(so):
                if not needed.startswith("/"):
                    continue
                if os.path.exists(needed):
                    continue
                base = os.path.basename(needed)
                target = available.get(base)
                if not target:
                    continue
                parent = os.path.dirname(needed)
                home = os.path.expanduser("~")
                if not (parent.startswith(home) or parent.startswith("/data")):
                    continue
                try:
                    os.makedirs(parent, exist_ok=True)
                    if not os.path.lexists(needed):
                        os.symlink(target, needed)
                        stubs += 1
                except OSError:
                    continue
        if stubs:
            self.output.info("baked DT_NEEDED path stubs created: %d" % stubs)

    def _prepare_runtime_links(self):
        """Mirror the KF6 build-tree layout around the consumer test CWD.

        The published KF6 libraries record build-tree-relative DT_NEEDED
        entries ("../bin/libKF6*.so", "../../bin/libKF6*.so"); the musl
        loader resolves pathname-like entries relative to the process
        CWD (= the test binary dir, pinned in test()).  Symlink every
        KF6 shared library into both resolution depths (kcmutils 6.26.0
        precedent, extended for the consumer-test CWD)."""
        import shutil as _shutil
        bindir = self.cpp.build.bindirs[0]
        runtime_dirs = {
            bindir,
            self.build_folder,
            # "../bin" from the CWD:
            os.path.normpath(os.path.join(bindir, os.pardir, "bin")),
            # "../../bin" from the CWD:
            os.path.normpath(os.path.join(bindir, os.pardir, os.pardir, "bin")),
        }
        lib_sources = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        package = None
        for dep in self.dependencies.values():
            if dep.ref.name == "kinfocenter" and dep.package_folder:
                package = dep.package_folder
                break
        if package:
            lib_sources.extend(glob.glob(os.path.join(package, "lib", "lib*.so*")))
        for cdir in runtime_dirs:
            os.makedirs(cdir, exist_ok=True)
        for src in lib_sources:
            for cdir in runtime_dirs:
                dst = os.path.join(cdir, os.path.basename(src))
                if os.path.exists(src) and not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        _shutil.copy2(src, dst)
