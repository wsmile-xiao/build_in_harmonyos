#!/usr/bin/env python3
"""Conan recipe for libkomparediff2 26.04.0 on HarmonyOS PC.

libkomparediff2 is the KDE diff/patch modeling library behind Kompare
(libkomparediff2.so, SOVERSION 6): it parses unified/context/normal/RCS
diff output and compares files programmatically.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalog generation (the
    tarball ships po/<lang>/libkomparediff2.po sources; kxmlgui 6.18.0
    precedent, ki18n_install() honors this switch)
  - BUILD_TESTING=ON and full ctest execution: upstream registers 2 CTest
    entries (libkomparediff2-interactiveDiffTest,
    libkomparediff2-levenshteintest); both are self-contained (embedded
    patch strings, QTEST_GUILESS_MAIN) and run headless with
    QT_QPA_PLATFORM=offscreen, no external diff binary needed
  - Patches 0001-0005 remove the upstream KF6KIO dependency (KIO is not
    published to ohpcd): KIO::upUrl in src/kompareprocess.cpp is
    reimplemented on plain QUrl, and the KIO stat/mkdir/file_copy save-path
    jobs in src/modellist.cpp are replaced with QFile/QDir operations; the
    KIO component and KF6::KIOCore link references are dropped (same
    dependency-trimming approach as the kxmlgui
    FORCE_DISABLE_KGLOBALACCEL=ON precedent)
  - Dependencies: qtbase/6.11.1 (Qt6Core/Qt6Widgets, Qt6Test for tests),
    kcoreaddons/6.18.0, kconfig/6.18.0, ki18n/6.18.0, kxmlgui/6.18.0
    (upstream find_package(KF6 COMPONENTS CoreAddons Config XmlGui I18n)
    after removing the KIO component), ecm/6.26.0 (ECM; the ohpcd baseline
    has no 6.18.0 ecm, and the kxmlgui 6.18.0 / kconfig 6.26.0 recipes use
    ecm/6.26.0 for this KF 6.18-generation graph)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
  - Prebuilt KF6 binaries from ohpcd embed ABSOLUTE DT_NEEDED paths of their
    build machine's ~/.cache/conan2 conan home; musl resolves
    slash-containing DT_NEEDED entries literally (no LD_LIBRARY_PATH
    fallback, E607 trap class). The recipe mirrors every host dependency's
    lib dir under the legacy cache root (package folder names are content
    hashes, <home>/p/<pkg_id>/p) so the stale paths resolve
  - SOVERSION restored: with no Platform/HarmonyOS CMake module the soname
    flag is undefined and upstream's SOVERSION 6 would be dropped; the
    recipe re-arms CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG so
    libkomparediff2.so.6 + DT_SONAME ship as upstream intends. The absolute
    DT_NEEDED entries inherited from the soname-less ohpcd KF6 prebuilts
    are a registry-wide trait and resolve at runtime via the mirrors above
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibKompareDiff2Conan(ConanFile):
    name = "libkomparediff2"
    version = "26.04.0"
    description = "KDE diff/patch parsing and modeling library behind Kompare"
    # GPL-2.0-or-later for most files; some (tests, parts of src) are
    # LGPL-2.0-or-later. Reported per the dominant upstream license.
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/libraries/libkomparediff2"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kxmlgui/6.18.0")

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
        # ki18n_install(po) honors KF_SKIP_PO_PROCESSING; skip catalog
        # generation for the initial OHOS baseline (kxmlgui 6.18.0 precedent).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # CMake has no Platform/HarmonyOS module on OHOS, so the platform's
        # shared-library soname flag is undefined and upstream's
        # VERSION/SOVERSION (6) are silently dropped: DT_SONAME goes missing
        # and install(EXPORT) records IMPORTED_NO_SONAME. Re-arm the flag so
        # libkomparediff2.so.6 (+ DT_SONAME) is produced as upstream intends.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

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
            # Add every dependency's lib/cmake dir so find_package(KF6*)
            # (via ECM's FindKF6 umbrella) and transitive find_dependency()
            # chains all resolve.
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

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._prepare_stale_cache_compat_links()
        self._run_upstream_tests()

    def _prepare_stale_cache_compat_links(self):
        # Prebuilt KF6 binaries from the ohpcd registry embed ABSOLUTE
        # DT_NEEDED paths recorded on their build machine, whose conan home
        # was ~/.cache/conan2. musl resolves DT_NEEDED entries containing a
        # slash literally, with no LD_LIBRARY_PATH fallback (same trap class
        # as the musl relative-soname CWD issue, E607). Package folder names
        # are content hashes (<home>/p/<pkg_id>/p), so mirroring every host
        # dependency's lib dir under the legacy cache root makes the stale
        # absolute paths resolve to the live cache.
        if self.settings.os != "OHOS":
            return
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            folder = dep.package_folder.replace("\\", "/").rstrip("/")
            if not folder.endswith("/p"):
                continue
            pkg_id = os.path.basename(os.path.dirname(folder))
            legacy_pkg_dir = os.path.join(
                os.path.expanduser("~"), ".cache", "conan2", "p", pkg_id, "p"
            )
            legacy_lib = os.path.join(legacy_pkg_dir, "lib")
            if os.path.exists(legacy_lib):
                continue
            live_lib = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(live_lib):
                continue
            os.makedirs(legacy_pkg_dir, exist_ok=True)
            try:
                os.symlink(live_lib, legacy_lib)
            except OSError:
                shutil.copytree(live_lib, legacy_lib, dirs_exist_ok=True)

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
            # libc++ first (kconfig 6.26.0 / kcalendarcore 6.26.0 precedent).
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
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
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
            # executables resolve the compatible libc++ first (kconfig
            # 6.26.0 / kcalendarcore 6.26.0 precedent, same fix as
            # _cmake_build_env).
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # Both upstream tests use QTEST_GUILESS_MAIN and embedded patch
        # strings; offscreen + a writable HOME/XDG tree keep them headless.
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
        # KDE install rpath is stripped on OHOS and some DT_NEEDED entries
        # only resolve from the process CWD; mirror the kxmlgui 6.18.0
        # precedent by linking every built and dependency library into
        # <build>/../bin so CTest entries can load them.
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

    def package(self):
        # Also run here so the compat links exist for the test_package phase.
        self._prepare_stale_cache_compat_links()
        cmake = CMake(self)
        cmake.install()
        # NOTE: do NOT post-process the installed ELF here. HarmonyOS enforces
        # file-integrity marks on app-sandbox storage: any later modification
        # of the installed .so (python open() write, patchelf, ...) makes the
        # loader reject it with EACCES on PROT_EXEC mmap. The absolute
        # DT_NEEDED entries inherited from the soname-less ohpcd KF6
        # prebuilts are a registry-wide platform trait (the published
        # kxmlgui/kconfig artifacts carry them too) and are resolved at
        # runtime by _prepare_stale_cache_compat_links / the consumer-side
        # compat bin mirrors.

    def package_info(self):
        # The project installs its own KompareDiff2Config.cmake with proper
        # dependency tracking (find_dependency on Qt6Core/Qt6Widgets and
        # KF6Config/KF6XmlGui). Use cmake_find_mode=none so CMakeDeps doesn't
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["komparediff2"]
