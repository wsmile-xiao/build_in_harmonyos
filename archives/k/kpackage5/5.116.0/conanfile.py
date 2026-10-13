#!/usr/bin/env python3
"""Conan recipe for kpackage5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

KPackage is the KDE Frameworks 5 library and tool for loading and installing
non-binary package content. The KF5 branch targets Qt5 and must not be confused
with the Qt6-based `kpackage` 6.x recipe in this repository.

OHOS-specific adaptations:
  - QT_MAJOR_VERSION=5 so the project finds Qt5. qt5-qtbase ships only
    per-module cmake configs, so CMakeDeps regenerates an aggregated Qt5Config
    via set_property("qt5-qtbase", "cmake_file_name", "Qt5").
  - KF_IGNORE_PLATFORM_CHECK=TRUE: OHOS is not in the KDE platform allowlist,
    KDEFrameworkCompilerSettings would otherwise error out.
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalogue generation.
  - CMAKE_DISABLE_FIND_PACKAGE_KF5DocTools=ON: keep optional documentation and
    kdoctools_install(po) out of the baseline package.
  - Qt5DBus is a hard requirement of kpackage 5.116.0 (there is no USE_DBUS
    switch in this release), satisfied by qt5-qtbase/5.15.2.2 which is built
    with -dbus. qt5-qtbase/5.15.2 (the older revision) is NOT usable here: it
    is configured -no-dbus and ships no Qt5DBus component.
  - ECM_MODULE_PATH is set explicitly because the project does
    set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH}) and ecm is a tool_requires
    (build context), so CMakeDeps does not wire share/ECM into the host paths.
  - CMAKE_AUTOMOC_EXECUTABLE / CMAKE_AUTORCC_EXECUTABLE point at the
    qt5-qtbase bin/moc and bin/rcc (CMakeDeps does not export Qt5::moc/rcc).
  - BUILD_TESTING=ON and the upstream CTest suite is executed from build();
    only `plasma-plasmoidpackagetest` is excluded (it hangs on the OHOS runner
    in the package install/update/uninstall flow, the same defect already
    recorded for the KF6 recipe). All other entries stay enabled.
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Kpackage5Conan(ConanFile):
    name = "kpackage5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - package content library and tool (Qt5)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kpackage"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # override=True: kcoreaddons5/5.116.0 and ki18n5/5.116.0 were built
        # against qt5-qtbase/5.15.2, and Conan refuses a graph that pulls both
        # 5.15.2 and 5.15.2.2 ("Version conflict ... originates from
        # kcoreaddons5/5.116.0"). 5.15.2 cannot be used here because it is
        # configured -no-dbus and ships no Qt5DBus component, which
        # kpackage 5.116.0 requires unconditionally (CMakeLists.txt:45), so the
        # graph is forced onto 5.15.2.2 for every consumer - the same remedy
        # baka/2.0.4 and neovim-qt/0.2.19 use in this repository.
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("karchive5/5.116.0")
        self.requires("kcoreaddons5/5.116.0")
        self.requires("ki18n5/5.116.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)

    def generate(self):
        # Stop CMakeDeps generating a Qt5 config at all. The qt5-qtbase recipe
        # itself declares cmake_file_name=Qt5, so CMakeDeps kept emitting
        # <generators>/Qt5Config.cmake and it won the lookup (Qt5_DIR pointed
        # into the generators folder). Its component targets are incomplete -
        # the link line for libKF5Package.so carried -L<qt5>/lib and
        # libQt5Core.so but no -lQt5DBus at all, giving
        # 'undefined symbol: QDBusConnection::sessionBus()', and Qt5::Test
        # failed the same way with QTest::qExec. The package ships a complete
        # aggregated lib/cmake/Qt5/Qt5Config.cmake plus per-module configs
        # (already on CMAKE_PREFIX_PATH via conan_cmakedeps_paths.cmake), so
        # with cmake_find_mode=none those correct configs are used instead.
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # ECM's KDEInstallDirs5 always runs ecm_query_qt(), which does a
        # find_package(Qt5Core) and would execute the *target* qmake. Beyond
        # being wrong for a cross build, the published Qt5 config is unusable
        # there (see _prepare_qt_mkspec_compat).
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF5DocTools"] = "ON"
        # HarmonyOS is not mapped to the Linux CMake platform, so
        # CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays undefined and the shared
        # library would carry no ELF DT_SONAME. Keep SONAME emission but skip the
        # versioned symlinks that some OHOS/HMDFS paths reject.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        qt5 = self.dependencies["qt5-qtbase"]
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        moc_path = os.path.join(qt5.package_folder, "bin", "moc")
        rcc_path = os.path.join(qt5.package_folder, "bin", "rcc")
        if not os.path.isfile(moc_path):
            raise RuntimeError(
                "qt5-qtbase does not provide the required bin/moc tool"
            )
        if not os.path.isfile(rcc_path):
            raise RuntimeError(
                "qt5-qtbase does not provide the required bin/rcc tool"
            )
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = rcc_path

        # kpackage's CMakeLists calls ki18n_install(po), which runs
        # KF5I18n's build-pofiles.cmake and shells out to
        # ${GETTEXT_MSGFMT_EXECUTABLE} for every .po file. That variable is
        # unset here (the published KF5I18n config does not locate gettext), so
        # the build died with "failed generating <build>/po". Point it at a
        # real msgfmt instead of patching upstream or dropping the translation
        # catalogues: prefer one on PATH (this recipe runs on the target), else
        # the gettext package the ki18n dependency already brings in.
        msgfmt = shutil.which("msgfmt")
        if not msgfmt:
            gettext = self.dependencies.get("gettext")
            if gettext and gettext.package_folder:
                candidate = os.path.join(gettext.package_folder, "bin", "msgfmt")
                if os.path.isfile(candidate):
                    msgfmt = candidate
        if msgfmt:
            tc.cache_variables["GETTEXT_MSGFMT_EXECUTABLE"] = msgfmt

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
        tc.generate()

        # ECM is a build-context tool_requires; CMakeDeps only adds
        # share/ECM/cmake to CMAKE_MODULE_PATH, while the project calls
        # find_package(ECM 5.116.0 NO_MODULE) which needs it on the config-mode
        # search path too. KF5 dependencies publish their configs under
        # <prefix>/lib/cmake.
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake)
        for dep_name in ("qt5-qtbase", "karchive5", "kcoreaddons5", "ki18n5"):
            dep = self.dependencies.get(dep_name)
            if not dep or not dep.package_folder:
                continue
            self._append_dependency_paths(lines, dep.package_folder)
        # The Conan-exported Qt5 component targets do not carry the per-module
        # include directories: Qt5::DBus exposes no include/QtDBus, so
        # src/kpackage/private/packagejob.cpp fails on
        # '#include <QDBusConnection>'. Add the module directories the package
        # actually ships to the directory scope. Qt5::DBus is the first
        # per-module Qt target this repository consumes, which is why no
        # existing workaround covered it.
        qt_include = os.path.join(qt5.package_folder, "include")
        for module in (
            "QtCore",
            "QtDBus",
            "QtGui",
            "QtNetwork",
            "QtTest",
            "QtWidgets",
        ):
            module_dir = os.path.join(qt_include, module)
            if os.path.isdir(module_dir):
                lines.append('include_directories("%s")' % module_dir)

        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        """Make the Qt5 package's baked-in mkspec path resolvable.

        The published qt5-qtbase package ships
        lib/cmake/Qt5Core/Qt5CoreConfigExtrasMkspecDir.cmake containing
        "${_qt5Core_install_prefix}/../b//mkspecs/linux-clang" - a path into
        Conan's *build* folder, which does not survive into the package, so
        every find_package(Qt5Core) fails. Copy the real mkspecs tree to where
        that generated config looks. The whole tree is copied because the
        mkspec headers include their siblings by relative path (linux-clang/
        qplatformdefs.h does #include "../common/posix/qplatformdefs.h"), and
        the copy merges rather than skipping when the target already exists so
        a partial tree from an earlier run is repaired. Same remedy as
        attica-kf5/5.116.0 and karchive5/5.116.0.
        """
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
        if os.path.isdir(source):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected, dirs_exist_ok=True)

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % package_folder)
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % package_folder)
        lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % package_folder)
        lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % package_folder)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

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
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
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
        # Define LD_LIBRARY_PATH outright for the test run. The incremental
        # prepends above proved insufficient for the Qt/KF5 test executables:
        # four of the ten upstream tests died with
        # 'Error loading shared library libKF5CoreAddons.so.5' even though the
        # dependency package provides that exact SONAME, so every library
        # directory is assembled explicitly.
        # The compatibility bin comes FIRST. It holds the re-signed copies of
        # every dependency library, and the OHOS loader rejects the original
        # kcoreaddons5 binary's signature with EACCES. With the dependency lib
        # directories first - as they were - the loader resolved
        # libKF5CoreAddons.so.5 straight from the package and never reached
        # the signed copy, so signing alone changed nothing.
        compat_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        lib_dirs = [
            compat_bin,
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "lib"),
            os.path.join(self.build_folder, "src", "lib"),
        ]
        lib_dirs.extend(
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
        )
        test_env.define(
            "LD_LIBRARY_PATH",
            ":".join(d for d in lib_dirs if os.path.isdir(d)),
        )

        with test_env.vars(self).apply():
            # Every registered entry is run, with a per-test timeout so a
            # wedged test fails as TIMEOUT instead of hanging the build. An
            # earlier revision excluded plasma-plasmoidpackagetest outright;
            # excluding a test is a claim about the platform, so it is run
            # here and any failure is recorded rather than assumed.
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 180'.format(self.build_folder)
            )

    @staticmethod
    def _resign_ohos_library(path, workdir):
        """Re-sign a copied library so the OHOS loader will map it.

        No-op where binary-sign-tool is unavailable or the signature is
        already accepted; the caller keeps whatever copy it had.
        """
        if not os.path.isfile(path):
            return
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            return
        signed = os.path.join(workdir, os.path.basename(path) + ".signed")
        try:
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", signed,
                 "-selfSign", "1"],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if os.path.isfile(signed):
                os.chmod(signed, 0o755)
                os.replace(signed, path)
        except (OSError, subprocess.SubprocessError):
            if os.path.exists(signed):
                try:
                    os.remove(signed)
                except OSError:
                    pass

    def _prepare_ctest_runtime_links(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        # This farm's umask yields drwxr-s--x for new directories: the group
        # has read but NOT execute. The tests run as a uid in the owning group
        # but not as the owner, so group permissions apply and the directory
        # cannot be traversed at all - every library inside it is unopenable
        # and the loader reports 'Error loading shared library
        # libKF5CoreAddons.so.5' even though the file is present, readable and
        # exports the symbols being relocated. Force a traversable mode.
        os.chmod(compatibility_bin, 0o755)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                # Copy rather than symlink: a symlink still has to be resolved
                # through the dependency package's own drwxr-s--x directory,
                # which is exactly what cannot be traversed. A real file in the
                # compatibility bin is reachable regardless.
                try:
                    shutil.copy2(src, dst)
                except OSError:
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        continue
            if os.path.exists(dst):
                try:
                    os.chmod(dst, 0o755)
                except OSError:
                    pass
            # These libraries are built with
            # CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE, so a package may ship
            # only the fully versioned file (libQt5Core.so.5.15.2) with no
            # libQt5Core.so.5, while the ELF SONAME the loader asks for is
            # exactly that shorter name. The four Qt/KF5 upstream tests then
            # die with 'Error loading shared library libKF5CoreAddons.so.5'
            # even though every file is present and readable - the failure is
            # really the unresolvable Qt5 dependency of that library. Create
            # the missing <name>.so.<major> alias alongside each library.
            base = os.path.basename(src)
            head, sep, tail = base.partition(".so.")
            if sep and "." in tail:
                alias = os.path.join(
                    compatibility_bin, "%s.so.%s" % (head, tail.split(".")[0])
                )
                if os.path.exists(src) and not os.path.exists(alias):
                    try:
                        os.symlink(src, alias)
                    except OSError:
                        pass

            # HarmonyOS refuses to map a shared library whose .codesign
            # section the loader does not accept, and reports it as
            #   Error loading shared library <name>: Permission denied
            # even when the file is present, readable and exports the symbols
            # being relocated. Measured on the device: an unmodified copy of
            # libKF5CoreAddons.so.5 fails to dlopen with EACCES, while the
            # exact same bytes re-signed with binary-sign-tool load fine, and
            # the Qt libraries (valid signature) load untouched. The invalid
            # signature lives in the published kcoreaddons5 package, which
            # this recipe cannot change, so the test-runtime copy is re-signed.
            self._resign_ohos_library(dst, compatibility_bin)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Package"]
        self.cpp_info.bindirs = ["bin"]
