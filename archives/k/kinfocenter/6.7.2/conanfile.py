#!/usr/bin/env python3
"""Conan recipe for kinfocenter 6.7.2 — KDE Info Center (Plasma 6.7.2).

kinfocenter is the KDE system information center: a set of KCM
(KConfigModule) plugins installed under plasma/kcms/kinfocenter plus the
private KInfoCenterInternal QML helper library (CommandOutputContext).
Upstream's "kinfocenter" executable is a symlink to systemsettings; on
OHOS the package payload is the plugin set — the symlink and its install
rule are removed (systemsettings is not part of the OHOS package set).

Upstream registers two autotest targets (kcms/samba/autotests:
ksambasharemodeltest + smbmountmodeltest via ecm_add_tests) plus one
appium GUI test (appiumtests/: kinfocenter_appiumtests, registered only
on Linux CI with selenium-webdriver-at-spi).  The samba autotests run
on the local arm64 OHOS runner (BUILD_TESTING=ON); the appium test is
exempted (Linux AT-SPI + full GUI session requirement).

OHOS adaptations (patches/0001-ohos-trim-kcms.patch):
* about-distro kcm trimmed: it is the only consumer of libdrm
  (pkg_check_modules), UDev, the vulkan/opengl helper executables and
  KF6::KIOGui — none of which are part of the OHOS package set (kio
  ships a KIOCORE_ONLY baseline, kcmutils 6.26.0 precedent).
* helpers (dmidecode-helper) trimmed: the kauth OHOS package uses the
  FAKE backend and ships no kauth-policy-gen host tool for the
  KAUTH_INSTALL_ACTIONS / KAUTH_INSTALL_HELPER_FILES install macros.
* usbview trimmed: FindUSB1 probes libusb-1.0 through pkg-config, which
  resolves differently across CI workers (an x86_64 host .pc would link
  a foreign-ABI library into an OHOS plugin) — cut for determinism.
* energy stays behind the upstream Linux guard (skipped on OHOS).
* samba kcm rewired: KF6::KIOWidgets -> Qt6::DBus and the
  KPropertiesDialog integration removed (KIOCORE_ONLY baseline); the
  two upstream samba autotests keep running against kcm_samba_static.
* kinfocenter symlink target + install rule removed (see above).
* KInfoCenterInternal gets SOVERSION 1 so the installed KCM plugins
  record a stable soname instead of build-tree DT_NEEDED paths.
* Qt6 find_package gains explicit DBus/Qml/Quick components (samba's
  qt_add_dbus_interface + KCMUtilsQuick's interface targets).

Dependency line: qtbase-sql-dbus/6.11.1 (Qt6 DBus module + qdbusxml2cpp)
+ qtdeclarative/6.11.1 (Qml/Quick components + qml tooling) + KF6 6.26
line (kcmutils/kio/kservice/solid/kauth); the kcmutils 6.26.0 recipe
pins the remaining KF6 closure (kio/kxmlgui/kitemviews +
kconfigwidgets 6.18 with 6.26 overrides) so the whole graph resolves to
published binaries.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class KInfoCenterConan(ConanFile):
    name = "kinfocenter"
    version = "6.7.2"
    description = (
        "KDE Info Center - system information KCM plugin set "
        "(Plasma 6.7.2, Qt6/KF6)"
    )
    license = (
        "GPL-2.0-or-later AND LGPL-2.1-or-later AND BSD-2-Clause "
        "AND BSD-3-Clause AND CC0-1.0"
    )
    homepage = "https://invent.kde.org/plasma/kinfocenter"
    url = "https://download.kde.org/stable/plasma/6.7.2/kinfocenter-6.7.2.tar.xz"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase-sql-dbus: Qt6 Core/Gui/Widgets/DBus/Network/Test plus
        # qdbusxml2cpp (samba's qt_add_dbus_interface); the plain
        # qtbase/6.11.x anchors of the KF6 6.26 binaries coexist in the
        # graph (kwalletmanager 26.04.0 precedent).
        self.requires("qtbase-sql-dbus/6.11.1")
        # Qml/Quick components + qml tooling for ecm_add_qml_module
        # (KInfoCenterInternal is a QML module with GENERATE_PLUGIN_SOURCE).
        self.requires("qtdeclarative/6.11.1")
        # KCM plugin machinery (kcmutils_add_qml_kcm + KCMUtilsQuick);
        # pulls kio/kxmlgui/kitemviews + kconfigwidgets 6.18 with the
        # KF6 6.26 overrides.
        self.requires("kcmutils/6.26.0")
        # KIOCore for the samba kcm (KSambaShare/KSambaShareData ship in
        # the KIOCORE_ONLY baseline).
        self.requires("kio/6.26.0")
        # top-level find_package(KF6 ... Service/Solid/Auth) components.
        self.requires("kservice/6.26.0")
        self.requires("solid/6.26.0")
        self.requires("kauth/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kinfocenter is adapted for Linux and OHOS, not "
                f"{self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # CMakeDeps generates configs for the non-KF6 graph packages
        # (openssl/zstd for KF6ArchiveConfig's find_dependency chain).
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
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_DOC"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Skip translation catalog generation (audiocd 26.04.3 precedent:
        # the CI worker msgfmt fails to load its own libintl).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # The KF6DocTools handbook toolchain is trimmed.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "TRUE"
        # KDEInstallDirs single-prefix layout on conan (kgoldrunner /
        # qqc2-breeze-style precedents): plugins under lib/plugins.
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)
        # ECM's own ECMConfig.cmake sets ECM_MODULE_PATH but the
        # CMakeDeps-generated layout does not propagate the variable the
        # project relies on — set it manually (audiocd/kgoldrunner
        # precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )
        # Qt6Qml/Qt6Quick live in the qtdeclarative package; Qt discovers
        # additional components through the official
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH hook (kdeclarative 6.26.0
        # precedent) — without it find_package(Qt6 ... Qml Quick) fails.
        qt_extra = []
        qtdecl = self.dependencies.get("qtdeclarative")
        if qtdecl and qtdecl.package_folder:
            qt_extra.append(qtdecl.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        # KCMs are trimmed by 0001-ohos-trim-kcms.patch, so skip the module.
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        # The OHOS conan toolchain does not emit -Wl,-soname by itself
        # (the published no-SONAME KF6 binaries are the visible symptom);
        # KInfoCenterInternal needs a soname so the installed KCM plugins
        # reference libKInfoCenterInternal.so.1 instead of build-tree
        # paths (qqc2-breeze-style 6.7.5 precedent).
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
        # Platform guard: the trim patch is OHOS-specific (kcmutils
        # 6.26.0 precedent).
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
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
        binary packages (kcmutils/kio 6.26.0 line).

        The published KF6 libraries record absolute DT_NEEDED entries
        pointing at the *build-time* conan cache package dirs.  On any
        other machine (CI worker or local runner) those paths do not
        exist and the loader aborts with "Error loading shared library"
        before LD_LIBRARY_PATH is even consulted (absolute DT_NEEDED
        bypasses the search path).

        Fix: scan every dependency .so for absolute DT_NEEDED entries;
        for each one whose file does not exist, create the exact parent
        directory and symlink the actually-available same-named library
        from the real dependency package into it.  Paths outside the
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
                elif sh_type == 3:  # SHT_STRTAB
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
        so_files.extend(glob.glob(os.path.join(self.build_folder, "lib", "lib*.so*")))
        so_files.extend(
            glob.glob(
                os.path.join(self.build_folder, "kcms", "**", "*.so"),
                recursive=True,
            )
        )

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
            self.output.info("baked DT_NEEDED path stubs created: %d" % stubs)

    def _prepare_ctest_runtime_links(self):
        """KF6 libraries record build-tree-relative DT_NEEDED entries
        (e.g. ../../bin/libKF6*.so); mirror the expected layout by
        symlinking every KF6 shared library into the build tree
        compatibility locations (kcmutils 6.26.0 precedent)."""
        import shutil as _shutil
        # KF6 libraries record build-tree-relative DT_NEEDED entries
        # (../bin/libKF6*.so, ../../bin/libKF6*.so); the musl loader
        # resolves pathname-like DT_NEEDED entries relative to the test
        # process CWD, which CTest sets to the binary dir of the defining
        # CMakeLists (kcms/samba/autotests). Mirror the expected layout
        # at every plausible resolution depth (kcmutils 6.26.0 precedent,
        # extended for the kcms/samba nesting).
        compatibility_dirs = {
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "lib"),
            os.path.join(self.build_folder, "kcms", "samba", "autotests"),
            os.path.normpath(os.path.join(self.build_folder, "kcms", "samba", "autotests", "bin")),
            # ../bin from the autotests CWD:
            os.path.join(self.build_folder, "kcms", "samba", "bin"),
            os.path.join(self.build_folder, "kcms", "samba"),
            # ../../bin from the autotests CWD:
            os.path.join(self.build_folder, "kcms", "bin"),
            # ../../../bin from the autotests CWD (= build_folder/bin):
            os.path.normpath(os.path.join(self.build_folder, "kcms", "bin", os.pardir, "bin")),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, "bin")),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, os.pardir, "bin")),
        }
        lib_sources = glob.glob(os.path.join(self.build_folder, "lib", "lib*.so*"))
        lib_sources.extend(glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*")))
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
        copy(self, "LICENSES",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._sign_ohos_payload()

    def _sign_ohos_payload(self):
        """Re-sign every packaged ELF for the OHOS loader.

        Freshly linked OHOS ELF files carry an invalid linker stub
        .codesign section; dlopen() validates the code signature and
        rejects the file with EACCES ("Permission denied") before
        LD_LIBRARY_PATH is even consulted — verified locally: after
        remove-section + binary-sign-tool -selfSign 1 the same payload
        loads. Sign the KCM plugins + libKInfoCenterInternal so the
        consumer test (KPluginFactory::loadFactory / QLibrary::load)
        and any downstream consumer can dlopen them (kgoldrunner 26.04.0
        test_package _sign precedent, applied at package() level).
        """
        import fnmatch
        import subprocess

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning(
                "OHOS signing tools not found; skipping payload signing"
            )
            return
        count = 0
        for root, _, files in os.walk(self.package_folder):
            for fn in files:
                path = os.path.join(root, fn)
                if os.path.islink(path) or not fnmatch.fnmatch(fn, "*.so*"):
                    continue
                try:
                    with open(path, "rb") as f:
                        if f.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                # The stub section may or may not exist; either way the
                # signer rewrites a valid one.
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", path],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", path,
                     "-selfSign", "1"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                count += 1
        self.output.info("OHOS payload signed: %d ELF files" % count)

    def _runtime_env(self, include_build=False):
        # Host tools (moc / qmlcachegen / qmltyperegistrar / qtpaths) are
        # OHOS binaries needing libc++_shared from /system/lib64 plus the
        # dependency lib dirs on LD_LIBRARY_PATH (audiocd 26.04.3 /
        # qqc2-breeze-style 6.7.5 precedents).
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml"))
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package_info(self):
        # The package installs no cmake config of its own that consumers
        # should find_package(); the payload is the KCM plugin set under
        # lib/plugins plus the KInfoCenterInternal library.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KInfoCenterInternal"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.package_folder, "lib", "plugins")
        )
        self.runenv_info.prepend_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
