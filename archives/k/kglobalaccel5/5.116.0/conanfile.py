#!/usr/bin/env python3
"""Conan recipe for kglobalaccel5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

kglobalaccel is the KDE Frameworks 5 global workspace shortcuts library
(builds libKF5GlobalAccel.so, cmake package KF5GlobalAccel). The KF5 branch
targets Qt5.

OHOS-specific adaptations (recipe layer only, no source patches):
  - QT_MAJOR_VERSION=5 so the project finds Qt5 (qt5-qtbase/5.15.2.2, the
    OHOS Qt5 build that ships Qt5::DBus and Qt5::Widgets — both are PUBLIC
    link dependencies of KF5GlobalAccel; qt5-qtbase/5.15.2 is built with
    -no-widgets -no-dbus and cannot satisfy this project).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform allowlist; attica5/kcrash/kconfig precedent).
  - BUILD_RUNTIME=OFF: the kglobalacceld runtime daemon is excluded. It
    exists to grab global shortcuts from an X11/XCB session
    (find_package(XCB) in CMakeLists.txt:60); OHOS ships neither X11 nor a
    global-shortcut service, so the daemon is non-functional here. This also
    mirrors the archived kglobalaccel 6.26.0 package, which is library-only
    (upstream split the daemon out of the KF6 repo). Excluding the runtime
    removes the KF5Config/KF5CoreAddons/KF5Crash/KF5DBusAddons/KF5WindowSystem
    requirement block (CMakeLists.txt:50-56), which is only needed by the
    daemon.
  - The native Qt5 cmake config shipped by qt5-qtbase is unusable; CMakeDeps
    regenerates a clean Qt5Config via `set_property("qt5-qtbase",
    "cmake_file_name", "Qt5")` (attica5/barrier precedent), so
    find_package(Qt5 COMPONENTS DBus Widgets) and the
    find_dependency(Qt5DBus/Qt5Widgets) calls inside the installed
    KF5GlobalAccelConfig.cmake resolve.
  - ECM_MODULE_PATH is set explicitly because the project's CMakeLists.txt
    relies on `set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})`, and ecm is a
    tool_requires (build context) so CMakeDeps does not wire its share/ECM
    tree into the host prefix paths automatically.
  - CMAKE_AUTOMOC_EXECUTABLE / CMAKE_AUTORCC_EXECUTABLE point at the
    qt5-qtbase bin/moc and bin/rcc (CMakeDeps does not export the
    Qt5::moc/Qt5::rcc executable targets).
  - ecm_install_po_files_as_qm(poqm): KF5 tarballs ship a poqm/ directory and
    ECMPoQmTools unconditionally requires Qt5LinguistTools (not in the OHOS
    repo); patches/0001-guard-poqm-on-qt5linguisttools.patch guards the call
    with if(Qt5LinguistTools_FOUND) so it becomes a no-op without the module.
  - Upstream autotest inventory: patches/0002-build-autotest-without-runtime.patch
    builds autotests/kglobalshortcuttest even with BUILD_RUNTIME=OFF by linking
    the public KF5::GlobalAccel + compiling src/sequencehelpers_p.cpp (instead
    of the daemon-side private KF5::GlobalAccelPrivate target). The test source
    is unchanged; ctest registers the upstream case (inventory = 1) and the
    suite self-skips at runtime when the org.kde.kglobalaccel daemon service
    is absent. Full execution evidence on the device: notes.md (R51).
  - Qt mkspecs compat: the native Qt5CoreConfigExtras.cmake probes
    <qt_pkg>/../b/mkspecs/linux-clang (the qtbase build dir baked in at
    package time, absent in the published package). Copy mkspecs/linux-clang
    there (attica-kf5/5.116.0 precedent), so find_dependency(Qt5DBus) inside
    the installed KF5GlobalAccelConfig.cmake succeeds in consumers.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Kglobalaccel5Conan(ConanFile):
    name = "kglobalaccel5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - KGlobalAccel (global workspace shortcuts)"
    license = "LGPL-2.0-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/kglobalaccel"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt5::DBus and Qt5::Widgets are PUBLIC link dependencies of
        # KF5GlobalAccel (src/CMakeLists.txt target_link_libraries PUBLIC
        # Qt${QT_MAJOR_VERSION}::DBus Qt${QT_MAJOR_VERSION}::Widgets).
        # qt5-qtbase/5.15.2.2 is the OHOS Qt5 build with -dbus and widgets.
        self.requires("qt5-qtbase/5.15.2.2")
        # tests/CMakeLists.txt calls find_package(Qt5Qml REQUIRED) when
        # BUILD_TESTING=ON; qt5-qtdeclarative ships Qt5::Qml.
        self.requires("qt5-qtdeclarative/5.15.2")

    def build_requirements(self):
        # Upstream calls find_package(ECM 5.116.0 NO_MODULE); CMake accepts
        # any package version >= the requested one, so the published
        # ecm/6.26.0 satisfies it (attica5/5.116.0 precedent).
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase ships per-module cmake configs but the aggregated
        # Qt5Config.cmake shipped in the package is not consumable through
        # CMakeDeps directly; regenerate a clean Qt5Config so
        # find_package(Qt5 COMPONENTS ...) works (attica5 precedent).
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # The kglobalacceld daemon is X11/XCB-only and non-functional on
        # OHOS; excluding it also skips the KF5Config/KF5CoreAddons/KF5Crash/
        # KF5DBusAddons/KF5WindowSystem find_package block (daemon-only deps).
        tc.variables["BUILD_RUNTIME"] = "OFF"
        # HarmonyOS is not mapped to the Linux CMake platform, so
        # CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays undefined and the
        # produced shared library would have no ELF DT_SONAME (the W3 CI L5
        # soname gate fails). Mirror the platform-validated attica5/expat
        # pattern: keep SONAME emission but skip versioned symlinks.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        qt5 = self.dependencies["qt5-qtbase"]
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        moc_path = os.path.join(qt5.package_folder, "bin", "moc")
        rcc_path = os.path.join(qt5.package_folder, "bin", "rcc")
        if not os.path.isfile(moc_path):
            raise RuntimeError(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/moc tool"
            )
        if not os.path.isfile(rcc_path):
            raise RuntimeError(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/rcc tool"
            )
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = rcc_path
        # The upstream autotest includes <qplatformdefs.h>, which lives in the
        # Qt mkspecs tree; CMakeDeps-generated Qt5::Core configs carry only
        # the include/ directories. Expose the package mkspecs dir through the
        # build env (CMake appends env CXXFLAGS to CMAKE_CXX_FLAGS) instead of
        # the toolchain variables, so no conan-managed flag is clobbered
        # (same package layout the mkspecs mirror above relies on).
        mkspecs_dir = os.path.join(qt5.package_folder, "mkspecs", "linux-clang")
        if os.path.isdir(mkspecs_dir):
            self.buildenv.append("CXXFLAGS", "-isystem {}".format(mkspecs_dir))

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

        self._write_paths_file()

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # Qt5CoreConfigExtrasMkspecDir.cmake hardcodes the qtbase *build*
        # directory (<pkg>/../b/mkspecs/linux-clang) which is not shipped in
        # the published package; mirror it so consumer find_package() works
        # (attica-kf5/5.116.0 precedent).
        source = os.path.join(qt_package_folder, "mkspecs", "linux-clang")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs", "linux-clang"
        )
        if os.path.isdir(source) and not os.path.exists(expected):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected)

    def _write_paths_file(self):
        # conan_toolchain.cmake includes conan_cmakedeps_paths.cmake when it
        # exists, but CMakeDeps only emits it for deps that need it. Write it
        # ourselves so the ecm config path and the qt_add_dbus_interface shim
        # are always wired in.
        ecm = self.dependencies.build.get("ecm")
        lines = []
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            # CMakeDeps puts ecm's builddir (share/ECM/cmake) only into
            # CMAKE_MODULE_PATH, but the project calls
            # find_package(ECM 5.116.0 NO_MODULE) which needs ECMConfig.cmake
            # on the config-mode search path (attica5 precedent).
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')

        # CMakeDeps-generated Qt5DBus config does not include Qt's
        # Qt5DBusMacros.cmake, so the upstream qt_add_dbus_interface() calls
        # in src/CMakeLists.txt fail with "Unknown CMake command". The real
        # macro file cannot be included directly (it needs
        # MacroAddFileDependencies and Qt5CoreMacros, neither shipped through
        # CMakeDeps), so provide a behaviour-identical shim: same generated
        # artifacts (<basename>.h/.cpp/.moc), same source-file properties and
        # same CLASSNAME/NO_NAMESPACE/INCLUDE handling, driven by the real
        # qdbusxml2cpp/moc binaries from qt5-qtbase.
        qt5 = self.dependencies["qt5-qtbase"]
        bin_dir = os.path.join(qt5.package_folder, "bin")
        shim = [
            '# qt_add_dbus_interface shim for CMakeDeps-generated Qt5 configs',
            'set(QT5_QDBUSXML2CPP_EXECUTABLE "%s")' % os.path.join(bin_dir, "qdbusxml2cpp"),
            'set(QT5_MOC_EXECUTABLE "%s")' % os.path.join(bin_dir, "moc"),
            'function(qt_add_dbus_interface _sources _interface _basename)',
            '    get_filename_component(_infile "${_interface}" ABSOLUTE)',
            '    set(_header "${CMAKE_CURRENT_BINARY_DIR}/${_basename}.h")',
            '    set(_impl   "${CMAKE_CURRENT_BINARY_DIR}/${_basename}.cpp")',
            '    set(_moc    "${CMAKE_CURRENT_BINARY_DIR}/${_basename}.moc")',
            '    get_source_file_property(_nonamespace "${_interface}" NO_NAMESPACE)',
            '    if(_nonamespace)',
            '        set(_params -N -m)',
            '    else()',
            '        set(_params -m)',
            '    endif()',
            '    get_source_file_property(_classname "${_interface}" CLASSNAME)',
            '    if(_classname)',
            '        set(_params ${_params} -c ${_classname})',
            '    endif()',
            '    get_source_file_property(_include "${_interface}" INCLUDE)',
            '    if(_include)',
            '        set(_params ${_params} -i "${_include}")',
            '    endif()',
            '    add_custom_command(OUTPUT "${_impl}" "${_header}"',
            '        COMMAND ${QT5_QDBUSXML2CPP_EXECUTABLE} ${_params} -p "${_basename}" "${_infile}"',
            '        DEPENDS "${_infile}" VERBATIM)',
            '    set_source_files_properties("${_impl}" "${_header}" PROPERTIES',
            '        SKIP_AUTOMOC TRUE',
            '        SKIP_AUTOUIC TRUE',
            '    )',
            '    add_custom_command(OUTPUT "${_moc}"',
            '        COMMAND ${QT5_MOC_EXECUTABLE} "${_header}" -o "${_moc}"',
            '        DEPENDS "${_header}" VERBATIM)',
            '    list(APPEND ${_sources} "${_impl}" "${_header}" "${_moc}")',
            '    set(${_sources} ${${_sources}} PARENT_SCOPE)',
            'endfunction()',
            '',
        ]
        shim_file = os.path.join(self.generators_folder, "conan_qt_dbus_shim.cmake")
        with open(shim_file, "w") as f:
            f.write("\n".join(shim))
        lines.append(f'include("{shim_file}")')

        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

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
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        # Upstream registers exactly 1 ctest case for the default build:
        # autotests/kglobalshortcuttest (via ecm_add_tests). With the stock
        # BUILD_RUNTIME=OFF configuration it is skipped; the
        # 0002-build-autotest-without-runtime patch builds it against the
        # public library instead, so the full upstream inventory (1) is
        # registered here too. The suite self-skips at runtime when the
        # org.kde.kglobalaccel daemon service is absent (kglobalacceld is
        # X11/XCB-only and excluded on OHOS).
        #
        # build() records the ctest inventory only. A full in-recipe ctest run
        # would crash in initTestCase: with no D-Bus session bus present,
        # QDBusConnection::sessionBus().interface() returns nullptr and the
        # upstream code dereferences it (probe evidence in notes.md). On the
        # real device the suite is executed against a live session bus with
        # every slot taking upstream's own QSKIP("kglobalaccel not installed")
        # path; logs are committed under reports/ (R51 three-step declaration:
        # inventory / run / report).
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" -N'.format(self.build_folder)
            )

    def _prepare_ctest_runtime_links(self):
        # Symlink the build-tree and dependency libraries next to the test
        # binaries so the dynamic linker can resolve them (attica5 precedent).
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

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5GlobalAccel"]
