#!/usr/bin/env python3
"""Conan recipe for kjobwidgets5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

Builds libKF5JobWidgets: the KDE Frameworks 5 Qt5 integration layer between
KJob (from kcoreaddons) and the widgets used to report job progress —
KWidgetJobTracker (progress dialog), KStatusBarJobTracker, KUiServerJobTracker /
KUiServerV2JobTracker, KDialogJobUiDelegate and the KJobWidgets/KJobWindows
window-association helpers.  The KF5 branch still targets Qt5.

This is a direct build requirement of kparts5 (KF5::JobWidgets).

OHOS-specific adaptations (reusing the validated kitemviews5 / kcoreaddons5
KF5 skeleton):
  - QT_MAJOR_VERSION=5 so the project selects Qt5 (qt5-qtbase/5.15.2.2, the
    widgets/DBus-capable Qt build; the plain 5.15.2 binary is the
    -no-widgets stub and cannot satisfy find_package(Qt5 ... Widgets)).
  - CMAKE_SYSTEM_NAME=Linux: the OHOS Conan toolchain maps os=OHOS to
    CMAKE_SYSTEM_NAME=HarmonyOS, for which CMake defines neither UNIX nor a
    platform module.  KJobWidgets guards its X11 integration with
    `if (NOT APPLE) find_package(X11)`, and ECM registers ctest cases only for
    non-cross builds (if(NOT CMAKE_CROSSCOMPILING)); the HarmonyOS platform
    also leaves ECM's POSIX compiler/rpath settings (guarded by if(UNIX))
    unset.  Forcing the Linux platform (same libc / clang driver) restores
    UNIX=1 and a native build, the chain-wide convention for Linux-like OHOS
    targets (kcoreaddons5 / kitemviews5).
  - KF_IGNORE_PLATFORM_CHECK=TRUE: HarmonyOS is not in the KDE platform list.
  - KF_SKIP_PO_PROCESSING=ON and patches/0001 disable
    ecm_install_po_files_as_qm(poqm): Qt5LinguistTools (lconvert/lrelease) is
    not shipped by the published qt5-qtbase package.
  - cmake_find_mode=none for qt5-qtbase: the package's own Qt5 CMake configs
    are consumed (Qt5::Widgets / Qt5::DBus / Qt5::Test plus the Qt5 macros and
    the mkspec include path); the CMakeDeps-generated Qt5 configs would shadow
    them.
  - Two KF5 dependencies are declared beyond qt5-qtbase:
    KF5CoreAddons (PUBLIC, provides KJob) and KF5WidgetsAddons (PRIVATE,
    KSqueezedTextLabel).  Both are published to ohpcd and are consumed through
    their own KF5*Config.cmake (cmake_find_mode=none, builddirs=lib/cmake).
    They must be listed BEFORE qt5-qtbase so that their config-directory
    entries stay ahead of CMakeDeps' own Qt5 entries in CMAKE_PREFIX_PATH.
  - CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE point at the qt5-qtbase bin
    tools (the CMakeDeps regeneration does not always export the Qt5::moc /
    Qt5::rcc / Qt5::uic targets).
  - Qt5CoreConfigExtrasMkspecDir.cmake (shipped inside the packaged
    qt5-qtbase) hard-codes a build-tree path <prefix>/../b/mkspecs/linux-clang
    which the packaged cache entry never has; generate() recreates the whole
    mkspecs tree there from the package's own mkspecs/ (kcoreaddons5 /
    kconfig5 / kitemviews5 precedent).
  - CMAKE_BUILD_WITH_INSTALL_RPATH=ON (E537): OHOS refuses to mmap PROT_EXEC a
    shared library whose ELF was rewritten after linking.  By default CMake
    rewrites DT_RUNPATH in place at install time (file(RPATH_CHANGE)); linking
    with the final install RPATH leaves the install step nothing to rewrite.
  - CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE +
    CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname," -> relocatable,
    unversioned DT_SONAME (W3 CI L5 soname gate, expat-validated pattern).
  - CMAKE_BUILD_PARALLEL_LEVEL=1: the HMDFS cache filesystem refuses the make
    jobserver fifo (EPERM) (kcoreaddons5 precedent).
  - /system/lib64 is prepended to LD_LIBRARY_PATH while running the Qt host
    tools and the upstream tests so the loader resolves the compatible libc++
    first (kcoreaddons5 / kconfig5 precedent).
  - WITH_X11=OFF: HarmonyOS PC has no X11 window system and no X11 headers, so
    HAVE_X11 turns out FALSE and the QX11Info branch in kdialogjobuidelegate
    is compiled out (kdbusaddons / kcrash precedent).
  - BUILD_TESTING=ON registers the two upstream programs in tests/ (built via
    add_executable + ecm_mark_as_test, so they carry no ctest assertions and
    no ctest registrations); the ctest suite is genuinely empty, therefore
    ctest is not embedded in build().  Evidence for the R51 declaration is
    captured in notes.md and reports/test-report.md.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Kjobwidgets5Conan(ConanFile):
    name = "kjobwidgets5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - job progress widgets (KWidgetJobTracker / KStatusBarJobTracker / KDialogJobUiDelegate)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kjobwidgets"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KF5CoreAddons (PUBLIC: KJob) and KF5WidgetsAddons (PRIVATE:
        # KSqueezedTextLabel) are the two KF5 deps of the project's
        # find_package list beyond Qt5.  Declared first so their
        # lib/cmake config directories stay ahead of the CMakeDeps Qt5
        # entries in CMAKE_PREFIX_PATH.
        self.requires("kcoreaddons5/5.116.0")
        self.requires("kwidgetsaddons5/5.116.0")
        # 5.15.2.2 is the widgets + DBus capable build that satisfies
        # find_package(Qt5 5.15.2 CONFIG REQUIRED Widgets) and the DBus
        # component (find_package(Qt5 ... DBus) is REQUIRED for non-Android).
        #
        # force=True is required because the published KF5 5.116.0 packages
        # are split across two Qt5 baselines: kcoreaddons5/5.116.0 (and
        # kglobalaccel5 / attica-kf5) pin the plain -no-widgets Qt5 stub
        # qt5-qtbase/5.15.2, while every Widgets-capable KF5 package
        # (kwidgetsaddons5, kitemviews5, ...) uses qt5-qtbase/5.15.2.2.
        # KJobWidgets needs Widgets + DBus from Qt5 AND KF5CoreAddons from its
        # KF5 dependency, so without unification Conan aborts with
        #   "Version conflict: Conflict between qt5-qtbase/5.15.2 and
        #    qt5-qtbase/5.15.2.2 in the graph"
        # force=True (not override=True) resolves the conflict while keeping
        # qt5-qtbase a consuming requirement so package_folder is available in
        # generate() (karchive5 zlib precedent).  Consequence: kcoreaddons5 is
        # no longer binary-reusable against its own pin and is rebuilt from
        # source with --build=missing against the same Qt5 baseline.
        self.requires("qt5-qtbase/5.15.2.2", force=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kjobwidgets5 only supports Linux and OHOS, got {}".format(
                    self.settings.os
                )
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Consume the native Qt5 configs shipped inside qt5-qtbase: they
        # provide the Qt5::Widgets/Qt5::DBus/Qt5::Test imported targets, the
        # Qt5 CMake macros and the mkspec include path the project relies on.
        # The CMakeDeps-generated Qt5 configs would shadow them, so suppress
        # them (cmake_find_mode=none) and add the Qt prefix to
        # CMAKE_PREFIX_PATH below.
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # No X11 on HarmonyOS PC (no window system, no X11 headers): leaves
        # HAVE_X11 off so the QX11Info code path is compiled out and no
        # Qt5::X11Extras lookup is attempted.
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
        # (kcoreaddons5 / kconfig5 / kitemviews5 precedent).
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

        # Wire the paths that CMakeDeps cannot provide:
        #  * qt5-qtbase is consumed in "none" find-mode, so its install prefix
        #    must be added manually for find_package(Qt5 ... CONFIG) to resolve
        #    the native Qt5 configs.
        #  * ECM is a build-context requirement, so its config-mode directory
        #    must be added for find_package(ECM 5.116.0 NO_MODULE).
        #  * kcoreaddons5 / kwidgetsaddons5 also declare cmake_find_mode=none
        #    (they ship their own KF5*Config.cmake with dependency tracking), so
        #    their lib/cmake directories must be added too, otherwise
        #    find_package(KF5CoreAddons 5.116.0) fails with "Could not find a
        #    package configuration file provided by KF5CoreAddons".  Iterating
        #    every dependency also covers the transitive find_dependency()
        #    chains of the KF5 configs (ktextwidgets precedent).
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
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # See module docstring: Qt5CoreConfigExtrasMkspecDir.cmake points at
        # <prefix>/../b/mkspecs/linux-clang, which the packaged qt5-qtbase
        # entry does not ship.  Mirror the mkspecs subtree so the
        # linux-clang/qplatformdefs.h relative include resolves.
        src_mkspecs = os.path.join(qt_package_folder, "mkspecs")
        dst_mkspecs = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs"
        )
        if os.path.isdir(src_mkspecs):
            for rel in ("linux-clang", "common"):
                src = os.path.join(src_mkspecs, rel)
                dst = os.path.join(dst_mkspecs, rel)
                if (
                    os.path.isdir(src)
                    and not os.path.islink(dst)
                    and not os.path.isdir(dst)
                ):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copytree(src, dst)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()

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
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        # The built KF5 libs record a relative DT_NEEDED (bin/libKF5*.so)
        # because the OHOS CMake platform ships no soname flag; that relative
        # path only resolves when the build root is on the library path and
        # the compatibility bin/ links exist (_prepare_runtime_links).
        runtime_env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder, os.pardir)
        )
        if str(self.settings.os) == "OHOS":
            # The sandbox LD_LIBRARY_PATH carries an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64;
            # prepend /system/lib64 so the Qt host tools and the test
            # executables resolve the compatible libc++ first.
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return runtime_env

    def _prepare_runtime_links(self):
        # The upstream tests/ programs are linked against the build-tree
        # libKF5JobWidgets.so via a relative DT_NEEDED plus the packaged KF5/Qt
        # libraries.  Symlink them next to the test binaries so the loader can
        # resolve them (kcoreaddons5 / kitemviews5 precedent).
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        lib_sources.extend(glob.glob(os.path.join(self.build_folder, "lib", "lib*.so*")))
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
        # The project installs its own KF5JobWidgetsConfig.cmake with proper
        # dependency tracking (find_dependency on Qt5Widgets/KF5CoreAddons);
        # use cmake_find_mode=none so CMakeDeps does not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5JobWidgets"]
