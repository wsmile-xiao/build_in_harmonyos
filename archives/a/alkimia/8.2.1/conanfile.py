#!/usr/bin/env python3
"""Conan recipe for alkimia 8.2.1 on HarmonyOS PC.

Alkimia is the KDE financial library shared by financial applications such
as KMyMoney: online quote retrieval (AlkOnlineQuote), arbitrary precision
monetary values on top of GMP (AlkValue), NewStuff-powered quote source
store and the onlinequoteseditor tool.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation for the
    baseline package
  - BUILD_APPLETS=OFF because Plasma is not published on ohpcd
  - BUILD_TESTING=ON and ctest execution for upstream autotests
  - 0001-ohos-remove-ktextwidgets-dep.patch downgrades the debug dialog's
    KTextEdit log window to QTextEdit (only setVisible/clear/append are used,
    all native QTextEdit API) because ktextwidgets is not published in a
    version compatible with the KF6 6.18/6.29 dependency line (its only
    published 6.14.0 locks the KF 6.14 series which conflicts with knewstuff)
  - 0001 also patches cmake/modules/FindGMP.cmake to locate the C++ bindings
    (gmpxx.h/libgmpxx) shipped by gmp/6.3.0.1 (--enable-cxx)
  - Dependencies: qtbase/6.11.1, qtdeclarative/6.11.1 (Qt6 Qml for the qml
    plugin), gmp/6.3.0.1, knewstuff/6.29.0.1 (pulls KNSCore/KNSWidgets +
    attica/karchive/kpackage), kcompletion/6.18.0, kiconthemes/6.18.0,
    kxmlgui/6.18.0 (tools), kconfig/6.18.0, kcoreaddons/6.18.0, ki18n/6.18.0,
    kcodecs/6.18.0, kwidgetsaddons/6.18.0, ecm/6.26.0 (ECM, build tool)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase and the KF6
    packages use cmake_find_mode=none, so CMakeDeps does not add their
    lib/cmake builddirs to CMAKE_PREFIX_PATH
"""
import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class AlkimiaConan(ConanFile):
    name = "alkimia"
    version = "8.2.1"
    description = "KDE financial library - common financial data services for applications like KMyMoney"
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/office/alkimia"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase-sql-dbus variant provides Qt6::DBus (and Qt6::Sql), which the
        # baseline qtbase/6.11.1 package lacks (akonadi 25.12.3 precedent)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("gmp/6.3.0.1")
        # KF6 6.18/6.29 dependency line (knewstuff pulls attica/karchive/
        # kpackage transitively); ktextwidgets dropped via patch, see header
        self.requires("knewstuff/6.29.0.1")
        self.requires("kcompletion/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("kxmlgui/6.18.0")
        # kxmlgui's exported KF6XmlGuiConfig.cmake find_dependency()s
        # KF6ConfigWidgets; conan does not propagate non-CMakeDeps deps, so
        # list it explicitly (akonadi precedent)
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kitemviews/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kcodecs/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        # QtVersionOption: select the Qt6 code path (KF6 + Qt6:: targets)
        tc.variables["BUILD_WITH_QT6"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # Plasma applets need libplasma, which is not published on ohpcd
        tc.variables["BUILD_APPLETS"] = "OFF"
        # finance quote support requires perl at build/run time; baseline OFF
        tc.variables["ENABLE_FINANCEQUOTE"] = "OFF"
        # GMP from conan cache: help the classic FindGMP module locate it
        gmp = self.dependencies.get("gmp")
        if gmp and gmp.package_folder:
            gmp_pkg = gmp.package_folder
            tc.variables["GMP_INCLUDE_DIR"] = os.path.join(gmp_pkg, "include")
            gmpxx = None
            gmp_lib = None
            for cand in (
                os.path.join(gmp_pkg, "lib", "libgmpxx.so"),
                os.path.join(gmp_pkg, "lib", "libgmpxx.a"),
            ):
                if os.path.exists(cand):
                    gmpxx = cand
                    break
            for cand in (
                os.path.join(gmp_pkg, "lib", "libgmp.so"),
                os.path.join(gmp_pkg, "lib", "libgmp.a"),
            ):
                if os.path.exists(cand):
                    gmp_lib = cand
                    break
            if gmpxx and gmp_lib:
                tc.variables["GMPXX_LIBRARIES"] = gmpxx
                tc.variables["GMP_LIBRARIES"] = gmp_lib
        # MPIR must not be picked (we use GMP)
        tc.variables["MPIR_DIR"] = "MPIR_DIR-NOTFOUND"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        # R05 relocatable linkage: the KF6 deps are published without a
        # DT_SONAME, so linking them by their absolute cache path makes the
        # linker record that machine-private path in DT_NEEDED (knewstuff
        # 6.29.0.1 precedent). Expose their lib dirs so deps are linked by
        # basename (-lKF6CoreAddons...) and DT_NEEDED stays relocatable.
        kf6_dep_lib_dirs = []
        kf6_dep_include_dirs = []
        for dep_name in (
            "knewstuff",
            "kcompletion",
            "kiconthemes",
            "kxmlgui",
            "kconfigwidgets",
            "kguiaddons",
            "kcolorscheme",
            "kitemviews",
            "kconfig",
            "kcoreaddons",
            "ki18n",
            "kcodecs",
            "kwidgetsaddons",
            "karchive",
            "kpackage",
            "attica",
        ):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                kf6_dep_lib_dirs.append(os.path.join(dep.package_folder, "lib"))
                inc = os.path.join(dep.package_folder, "include")
                kf6_dep_include_dirs.append(inc)
                # KF6 headers live under include/KF6/<Module>
                kf6_root = os.path.join(inc, "KF6")
                if os.path.isdir(kf6_root):
                    for module in sorted(os.listdir(kf6_root)):
                        mod_dir = os.path.join(kf6_root, module)
                        if os.path.isdir(mod_dir):
                            kf6_dep_include_dirs.append(mod_dir)
        if kf6_dep_lib_dirs:
            tc.variables["ALKIMIA_DEP_LIB_DIRS"] = ";".join(kf6_dep_lib_dirs)
        if kf6_dep_include_dirs:
            tc.variables["CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES"] = ";".join(
                kf6_dep_include_dirs
            )
            tc.variables["CMAKE_C_STANDARD_INCLUDE_DIRECTORIES"] = ";".join(
                kf6_dep_include_dirs
            )

        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if qtbase:
            # qtbase-sql-dbus uses cmake_find_mode=none -> CMakeDeps does not
            # generate conan_cmakedeps_paths.cmake. Create it manually so the
            # toolchain adds its cmake dirs to CMAKE_PREFIX_PATH.
            lines = []
            self._append_dependency_paths(lines, qtbase.package_folder)
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            qtdeclarative = self.dependencies.get("qtdeclarative")
            if qtdeclarative:
                # Qt6Config lives in the qtbase package; Qt6Qml configs live
                # in the qtdeclarative package (knewstuff precedent).
                lines.append(
                    "set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH "
                    f'"{qtdeclarative.package_folder}")'
                )
                self._append_dependency_paths(lines, qtdeclarative.package_folder)

            gmp_dep = self.dependencies.get("gmp")
            if gmp_dep and gmp_dep.package_folder:
                self._append_dependency_paths(lines, gmp_dep.package_folder)

            for dep_name in (
                "knewstuff",
                "kcompletion",
                "kiconthemes",
                "kxmlgui",
                "kconfigwidgets",
                "kguiaddons",
                "kcolorscheme",
                "kitemviews",
                "kconfig",
                "kcoreaddons",
                "ki18n",
                "kcodecs",
                "kwidgetsaddons",
                "karchive",
                "kpackage",
                "attica",
            ):
                dep = self.dependencies.get(dep_name)
                if dep and dep.package_folder:
                    self._append_dependency_paths(lines, dep.package_folder)

            # karchive transitive deps (zlib/openssl/zstd) must resolve
            # against the Conan packages (knewstuff/kiconthemes precedent).
            for dep_name in ("zlib", "openssl", "zstd"):
                zdep = self.dependencies.get(dep_name)
                if zdep and zdep.package_folder:
                    self._append_dependency_paths(lines, zdep.package_folder)

            lines.append(
                "list(PREPEND CMAKE_MODULE_PATH "
                '"${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append(
                "list(PREPEND CMAKE_PREFIX_PATH "
                '"${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    @staticmethod
    def _append_dependency_paths(lines, pkg_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg_folder}")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg_folder}/lib/cmake")')
        for libdir in ("lib", "lib64"):
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg_folder}/{libdir}")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg_folder}/include")')
        bindir = os.path.join(pkg_folder, "bin")
        if os.path.isdir(bindir):
            lines.append(
                f'list(PREPEND CMAKE_PROGRAM_PATH "{bindir}")'
            )

    def build(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
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
            # ECM KDEInstallDirs runs the qtbase qtpaths host tool during
            # configure; /system/lib64 hosts the compatible libc++_shared.so
            # (kconfig 6.26.0 / bluez-qt 6.28.0 precedent).
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
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        self._prepare_ctest_runtime_links()
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
        # testParseQuoteJson inside alkonlinequoteprivatetest feeds UTC-day
        # boundary timestamps; on a non-UTC local timezone both samples land
        # on the same local date and the map degenerates to 1 entry (upstream
        # timezone-dependent test defect, verified: TZ=UTC -> 9/9 passed).
        test_env.define("TZ", "UTC")
        # Network-dependent upstream tests are excluded from the offline CI
        # sandbox run: alkonlinequotestest / alkdownloadengine-qt-test fetch
        # https://kmymoney.org/onlinequotestest.php, alknewstuffenginetest
        # contacts https://autoconfig.kde.org/ocs/providers.xml (KNS engine
        # segfaults on unreachable providers). These are recorded in notes.md
        # as offline exemptions, not adaptation regressions.
        exclude = "^(alkonlinequotestest|alkdownloadengine-qt-test|alknewstuffenginetest)$"
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -E "{}"'.format(
                    self.build_folder, exclude
                )
            )

    def _prepare_ctest_runtime_links(self):
        # The published KF6 packages (kconfig/knewstuff) carry relative
        # DT_NEEDED entries like `../../bin/libKF6ConfigCore.so` (from their
        # own build tree layout). The OHOS musl loader resolves path-style
        # NEEDED entries relative to the process cwd, not through
        # LD_LIBRARY_PATH, so the test run needs a compatible directory
        # shim (knewstuff 6.29.0.1 precedent).
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
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS":
            self._make_relocatable(self.package_folder)

    def _make_relocatable(self, root):
        # R05 post-build sweep: any DT_NEEDED entry that is an absolute cache
        # path (machine-private, e.g. /storage/Users/currentUser/.conan2/p/...)
        # or a build-tree-relative path (e.g. ../bin/...) is rewritten to its
        # bare basename so the packaged artifact resolves via the consumer
        # runtime library path and stays consumable on any cache layout
        # (knewstuff 6.29.0.1 precedent).
        def _tool(candidates):
            for cand in candidates:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            return shutil.which(candidates[0])

        readelf = _tool(
            ["/data/service/hnp/bin/readelf", "/usr/bin/readelf", "/bin/readelf", "readelf"]
        )
        patchelf = _tool(
            ["/data/service/hnp/bin/patchelf", "/usr/bin/patchelf", "/bin/patchelf", "patchelf"]
        )
        if not readelf or not patchelf:
            self.output.warning(
                "R05: readelf/patchelf not found (readelf={}, patchelf={}); "
                "skipping relocatable NEEDED sweep".format(readelf, patchelf)
            )
            return

        artifacts = []
        for subdir in ("bin", "lib"):
            base = os.path.join(root, subdir)
            if not os.path.isdir(base):
                continue
            for name in os.listdir(base):
                p = os.path.join(base, name)
                if os.path.isfile(p) and (name.endswith(".so") or os.access(p, os.X_OK)):
                    artifacts.append(p)
        for p in artifacts:
            try:
                dump = subprocess.run(
                    [readelf, "-d", p], capture_output=True, text=True, timeout=30
                ).stdout
            except Exception:
                continue
            for line in dump.splitlines():
                m = re.search(r"\(NEEDED\)\s+Shared library: \[(.*)\]", line)
                if not m:
                    continue
                needed = m.group(1)
                if "/" not in needed:
                    continue
                basename = os.path.basename(needed)
                try:
                    subprocess.run(
                        [patchelf, "--replace-needed", needed, basename, p],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    self.output.info(
                        "R05 relocatable: {} -> {} in {}".format(needed, basename, p)
                    )
                except subprocess.CalledProcessError as e:
                    self.output.warning(
                        "R05 patchelf failed on {} ({}): {}".format(
                            p, needed, e.stderr.strip()
                        )
                    )

    def package_info(self):
        # The project installs its own LibAlkimia6Config.cmake with proper
        # dependency tracking. Use cmake_find_mode=none so CMakeDeps doesn't
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["alkimia6"]
