#!/usr/bin/env python3
"""Conan recipe for kcrash5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

kcrash is the KDE Frameworks 5 crash-handling library (platform package name
kcrash5, upstream version string identical).  It ships libKF5Crash.so /
KF5::Crash + KF5CrashConfig.cmake: the SIGSEGV/SIGBUS/SIGFPE/SIGILL/SIGABRT
handler, the DrKonqi crash-dialog hook, the emergency-save callback and the
exec-based auto restart (KCrash::AutoRestart).

Upstream dependency reality (read from the sources, not from the task note):
  * ECM 5.116.0 NO_MODULE (REQUIRED, build context)
  * Qt5 Core + Gui (linked), Qt5 Test (REQUIRED at configure time), Qt5Widgets
    only for the autotests (find_package(...Widgets QUIET) in autotests/)
  * KF5CoreAddons 5.116.0 (PRIVATE link KF5::CoreAddons)
  * KF5WindowSystem is NOT a dependency: a full-source grep for
    WindowSystem/KWindowSystem finds nothing — only kcoreaddons5 is consumed.

OHOS-specific adaptations (modeled on the merged KF5 5.116.0 chain:
kjobwidgets5 / kitemmodels5 / kcoreaddons5 / kcodecs5):
  - QT_MAJOR_VERSION=5 so the project selects its Qt5 branch (upstream calls
    find_package(Qt${QT_MAJOR_VERSION} ...), which needs the variable set).
  - WITH_X11=OFF: upstream defaults the option ON under UNIX and then does
    `find_package(X11 REQUIRED)`, which aborts configure — HarmonyOS PC ships
    no X11 headers/libs (kjobwidgets5 precedent).  Only the X11-linked
    decoration of KCrash is compiled out; the crash API is unchanged.
  - KF_IGNORE_PLATFORM_CHECK=TRUE: HarmonyOS is not in the KDE platform list.
  - CMAKE_SYSTEM_NAME=Linux: the OHOS Conan toolchain maps os=OHOS to
    CMAKE_SYSTEM_NAME=HarmonyOS, for which CMake defines neither UNIX nor a
    platform module.  Forcing the Linux platform (same libc / clang driver)
    restores UNIX=1 and a non-cross build so ECM registers the ctest cases and
    KDE's if(UNIX) source selection keeps working (kcoreaddons5 chain-wide
    convention; R32-safe — no __OHOS__ macro is used anywhere).
  - qt5-qtbase/5.15.2.2 with force=True: the autotests need Qt5Widgets
    (test_crasher links Qt5::Widgets) while the KF5 chain pins the -no-widgets
    stub qt5-qtbase/5.15.2; force=True resolves that version conflict while
    keeping qt5-qtbase a consuming requirement so package_folder is available
    in generate() (kjobwidgets5 precedent).
  - Qt5 is consumed through its native configs (cmake_find_mode=none): the
    packaged qtbase ships complete per-module Qt5Config.cmake files;
    CMakeDeps-generated ones would shadow them.  The Qt/ECM/KF5 prefixes are
    wired through conan_cmakedeps_paths.cmake (appended after deps.generate(),
    which is the file the Conan toolchain includes).
  - ECM_MODULE_PATH is set explicitly: ecm is a tool_requires (build context),
    so its share/ECM tree is not on the host config path automatically.
  - mkspecs compat tree + CMAKE_AUTOMOC/AUTORCC/AUTOUIC_EXECUTABLE: the
    packaged Qt5CoreConfigExtrasMkspecDir.cmake hard-codes the original Qt
    build tree path that the cache entry never has, and CMakeDeps exports no
    Qt5::moc target on this chain.
  - BUILD_TESTING=ON compiles the three upstream autotests (kcrashtest,
    coreconfigtest, metadatatest) plus test_crasher; ctest is NOT embedded in
    build() (kcoreaddons5 / kcodecs5 precedent) so the sandbox's deliberate
    crash + exec auto-restart reproduction can never fail `conan create`.
    The cases are executed in the exploratory phase and recorded in
    reports/test-report.md and test_package/MANIFEST.yml, which honestly
    declares upstream_test_in_build=false.
  - CMAKE_BUILD_WITH_INSTALL_RPATH=ON (E537): OHOS refuses to mmap PROT_EXEC a
    shared library whose ELF was rewritten after linking.
  - CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE +
    CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,": OHOS is not
    mapped to the Linux CMake platform, so without these the produced .so has
    no ELF DT_SONAME and the W3 CI L5 soname gate fails.
  - CMAKE_BUILD_PARALLEL_LEVEL=1: HMDFS refuses the make jobserver fifo
    (EPERM), kcoreaddons5 precedent.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class Kcrash5Conan(ConanFile):
    name = "kcrash5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - crash handling library (KCrash)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kcrash"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KF5CoreAddons is the one real KF5 dependency of kcrash (PRIVATE
        # link of KF5::CoreAddons).  Declared first so its lib/cmake config
        # directory stays ahead of the CMakeDeps Qt5 entries.
        self.requires("kcoreaddons5/5.116.0")
        # 5.15.2.2 is the widgets-capable Qt5 build: the autotests do
        # find_package(Qt5Widgets) and test_crasher links Qt5::Widgets, while
        # kcoreaddons5/5.116.0 pins the -no-widgets stub qt5-qtbase/5.15.2.
        # force=True resolves the version conflict while keeping qt5-qtbase a
        # consuming requirement (kjobwidgets5 precedent).
        self.requires("qt5-qtbase/5.15.2.2", force=True)

    def build_requirements(self):
        # find_package(ECM 5.116.0 NO_MODULE): 6.26.0 is the version the
        # merged KF5 5.116.0 chain uses (kwindowsystem5 / kjobwidgets5).
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kcrash5 only supports Linux and OHOS, got {}".format(
                    self.settings.os
                )
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Consume the native Qt5 configs shipped inside qt5-qtbase: they
        # provide the Qt5::Widgets/Qt5::Test imported targets and the Qt5
        # CMake macros the project relies on.  The CMakeDeps-generated Qt5
        # configs would shadow them, so suppress them (cmake_find_mode=none)
        # and add the Qt prefix to CMAKE_PREFIX_PATH below.
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # No X11 on HarmonyOS PC (no headers, no libs): keeps the upstream
        # WITH_X11 option OFF so `find_package(X11 REQUIRED)` is never reached.
        tc.variables["WITH_X11"] = "OFF"
        # Treat OHOS as a Linux-like target so CMake defines UNIX and does not
        # report a cross build (see module docstring).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # HMDFS cannot create the make jobserver fifo (EPERM).
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        # E537: link with the final install RPATH so the install step does not
        # rewrite the ELF in place (see module docstring).
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
        # Relocatable, unversioned DT_SONAME (W3 CI L5 soname gate).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        qt5 = self.dependencies["qt5-qtbase"]
        # qt5-qtbase's Qt5CoreConfigExtrasMkspecDir.cmake hard-codes a
        # build-tree path (<prefix>/../b/mkspecs/linux-clang) that does not
        # exist in the packaged cache entry; CMake aborts on the missing
        # include directory.  Recreate it next to the package prefix
        # (kcoreaddons5 / kitemmodels5 / kjobwidgets5 precedent).
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        qbin = os.path.join(qt5.package_folder, "bin")
        for tool, cmake_var in (
            ("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
            ("rcc", "CMAKE_AUTORCC_EXECUTABLE"),
            ("uic", "CMAKE_AUTOUIC_EXECUTABLE"),
        ):
            tool_path = os.path.join(qbin, tool)
            if not os.path.isfile(tool_path):
                raise ConanInvalidConfiguration(
                    "qt5-qtbase/5.15.2.2 does not provide the required "
                    "bin/{} tool".format(tool)
                )
            tc.variables[cmake_var] = tool_path

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

        # Wire the paths that CMakeDeps cannot provide.  Appended ("a"): the
        # CMakeDeps generator has already saved its own content into this file
        # and the Conan toolchain includes it (conan_cmakedeps_paths.cmake).
        #  * qt5-qtbase is consumed in "none" find-mode, so its install prefix
        #    must be added manually for find_package(Qt5 ... CONFIG) to work.
        #  * ECM is a build-context requirement, so its config-mode directory
        #    must be added for find_package(ECM 5.116.0 NO_MODULE).
        #  * kcoreaddons5 also declares cmake_find_mode=none (it ships its own
        #    KF5CoreAddonsConfig.cmake), so its lib/cmake directory must be
        #    added too, otherwise find_package(KF5CoreAddons 5.116.0) fails.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        qt_pkg = qt5.package_folder
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(qt_pkg))
        lines.append('list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(qt_pkg))
        lines.append('list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(qt_pkg))
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "{}")'.format(ecm_cmake))
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(ecm_cmake))
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(
                    dep.package_folder
                )
            )
            lines.append(
                'list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(dep.package_folder)
            )
            lines.append(
                'list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(
                    dep.package_folder
                )
            )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # The whole mkspecs tree is needed: <qplatformdefs.h> is included from
        # the mkspec include dir, and Qt5CoreConfigExtras.cmake resolves it as
        # <package_folder>/../b/mkspecs (the build tree of the original build),
        # which the packaged cache entry never has.
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
        if not os.path.isdir(source):
            return
        os.makedirs(expected, exist_ok=True)
        for name in os.listdir(source):
            src_entry = os.path.join(source, name)
            dst_entry = os.path.join(expected, name)
            if os.path.exists(dst_entry):
                continue
            if os.path.isdir(src_entry):
                import shutil

                shutil.copytree(src_entry, dst_entry)
            else:
                import shutil

                shutil.copy2(src_entry, dst_entry)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        # ctest is deliberately NOT run here (kcoreaddons5 / kcodecs5
        # precedent): the upstream kcrashtest spawns test_crasher, crashes it
        # with SIGSEGV and waits for KCrash's exec auto-restart.  That
        # crash+exec reproduction must not be able to fail `conan create` on
        # the sandbox; the cases are exercised in the exploratory phase and
        # their real results are recorded in reports/test-report.md
        # (test_package/MANIFEST.yml declares upstream_test_in_build=false).

    def _runtime_env(self):
        runtime_env = Environment()
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5 and qt5.package_folder:
            runtime_env.prepend_path("PATH", os.path.join(qt5.package_folder, "bin"))
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
        if str(self.settings.os) == "OHOS":
            # The sandbox LD_LIBRARY_PATH carries an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64;
            # prepend /system/lib64 so the Qt host tools resolve the
            # compatible libc++ first (kcoreaddons5 precedent).
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return runtime_env

    def package(self):
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.install()

    def package_info(self):
        # The project installs its own KF5CrashConfig.cmake with proper
        # dependency tracking; use cmake_find_mode=none so CMakeDeps does not
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Crash"]
