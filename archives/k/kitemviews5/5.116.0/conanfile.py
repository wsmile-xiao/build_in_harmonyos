#!/usr/bin/env python3
"""Conan recipe for kitemviews5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

Builds libKF5ItemViews (the KDE Frameworks 5 item-view widget library:
KCategorizedView, KCategorizedSortFilterProxyModel, KCategoryDrawer,
KWidgetItemDelegate, KListWidgetSearchLine, KTreeWidgetSearchLine,
KFilterProxySearchLine, ...).  The KF5 branch still targets Qt5.

OHOS-specific adaptations (reusing the validated kcoreaddons5 / kconfig5 KF5
skeleton):
  - QT_MAJOR_VERSION=5 so the project selects Qt5 (qt5-qtbase/5.15.2.2, the
    widgets-capable Qt build; 5.15.2 is the -no-widgets stub and is refused).
  - CMAKE_SYSTEM_NAME=Linux: the OHOS Conan toolchain maps os=OHOS to
    CMAKE_SYSTEM_NAME=HarmonyOS, for which CMake defines neither UNIX nor a
    platform module.  KItemViews is a Qt Widgets library whose autotests are
    registered by ECM's ecm_add_test/ecm_mark_as_test, and ECM only adds the
    ctest registration when the build is not cross-compiling
    (if(NOT CMAKE_CROSSCOMPILING)); the HarmonyOS platform also leaves ECM's
    POSIX compiler/rpath settings (guarded by if(UNIX)) unset.  Forcing the
    Linux platform (same libc / clang driver) restores UNIX=1 and a native
    build so the four upstream tests are registered and run; this is the
    chain-wide convention for Linux-like OHOS targets (kcoreaddons5).
  - KF_IGNORE_PLATFORM_CHECK=TRUE: HarmonyOS is not in the KDE platform list.
  - BUILD_DESIGNERPLUGIN=OFF: the default is ON whenever the build is not
    cross-compiling, and src/designer links the Qt Designer plugin API
    (Qt5Designer/Qt5UiPlugin) which is not part of qt5-qtbase.
  - KF_SKIP_PO_PROCESSING=ON: Qt5LinguistTools (lrelease/lconvert) is not part
    of the qtbase package, so ecm_install_po_files_as_qm(poqm) must be skipped
    (kcoreaddons5 / kconfig5 precedent).
  - qt5-qtbase is consumed through its native Qt5 CMake configs
    (cmake_find_mode=none suppresses the CMakeDeps-generated ones, and the Qt
    install prefix is added to CMAKE_PREFIX_PATH).  The project calls
    find_package(Qt5 5.15.2 CONFIG REQUIRED Widgets) and relies on the Qt5
    CMake macros/targets (Qt5::Widgets, Qt5::Test) plus the mkspec include
    path that only the native Qt5 configs expose.
  - ECM_MODULE_PATH is set explicitly: ecm is a tool_requires (build context),
    so CMakeDeps does not wire its share/ECM tree into the host prefix paths.
  - CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE point at the qt5-qtbase bin
    tools (CMakeDeps does not export the Qt5::moc/Qt5::rcc/Qt5::uic targets).
  - Qt5CoreConfigExtrasMkspecDir.cmake (shipped inside the packaged qt5-qtbase)
    hard-codes a build-tree path <prefix>/../b/mkspecs/linux-clang which the
    packaged cache entry never has; generate() recreates the whole mkspecs tree
    there from the package's own mkspecs/ (kcoreaddons5 / kconfig5 precedent).
  - CMAKE_BUILD_WITH_INSTALL_RPATH=ON (E537): OHOS refuses to mmap PROT_EXEC a
    shared library whose ELF was rewritten after linking.  By default CMake
    rewrites the DT_RUNPATH in place at install time (file(RPATH_CHANGE));
    linking with the final install RPATH leaves the install step nothing to
    rewrite, so libKF5ItemViews.so keeps loading.
  - CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE +
    CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname," -> relocatable,
    unversioned DT_SONAME (W3 CI L5 soname gate, expat-validated pattern).
  - CMAKE_BUILD_PARALLEL_LEVEL=1: the HMDFS cache filesystem refuses the make
    jobserver fifo (EPERM) (kcoreaddons5 precedent).
  - /system/lib64 is prepended to LD_LIBRARY_PATH while running the Qt host
    tools and the upstream tests so the loader resolves the compatible libc++
    first (kcoreaddons5 / kconfig5 precedent).
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


class KItemViews5Conan(ConanFile):
    name = "kitemviews5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - KItemViews (categorized item-view widgets)"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/kitemviews"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Consume the native Qt5 configs shipped inside qt5-qtbase: they provide
        # the Qt5::Widgets/Qt5::Test imported targets and the Qt5 CMake macros
        # the project relies on.  The CMakeDeps-generated Qt5 configs would
        # shadow them, so suppress them (cmake_find_mode=none) and add the Qt
        # prefix to CMAKE_PREFIX_PATH below.
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
        # The Qt Designer plugin needs Qt5Designer/Qt5UiPlugin, not shipped by
        # qt5-qtbase; the option defaults to ON for a non-cross build.
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        # Treat OHOS as a Linux-like target so CMake defines UNIX and does not
        # report a cross build (see module docstring): ECM then registers the
        # upstream ctest cases and applies the POSIX flags/rpath settings.
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
        # (kcoreaddons5 / kconfig5 precedent).
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
        #    the native Qt5 configs (kcoreaddons5 / kconfig5 precedent).
        #  * ECM is a build-context requirement, so its config-mode directory
        #    must be added for find_package(ECM 5.116.0 NO_MODULE).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        qt_pkg = qt5.package_folder
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(qt_pkg))
        lines.append('list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(qt_pkg))
        lines.append('list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(qt_pkg))
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "{}")'.format(ecm_cmake))
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(ecm_cmake))
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
                shutil.copytree(src_entry, dst_entry)
            else:
                shutil.copy2(src_entry, dst_entry)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _runtime_env(self):
        runtime_env = Environment()
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5 and qt5.package_folder:
            runtime_env.prepend_path(
                "PATH", os.path.join(qt5.package_folder, "bin")
            )
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
            # The sandbox LD_LIBRARY_PATH carries an incompatible libc++_shared.so
            # under /data/storage/el1/bundle/libs/arm64; prepend /system/lib64 so
            # the Qt host tools and the test executables resolve the compatible
            # libc++ first (kcoreaddons5 / kconfig5 precedent).
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return runtime_env

    def _run_upstream_tests(self):
        if not can_run(self):
            return
        test_env = self._runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        try:
            os.chmod(xdg_runtime, 0o700)
        except OSError:
            pass
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
        # CTest discovers the test executables in <build>/bin/Tests? Upstream
        # installs them under <build>/bin; their libKF5ItemViews and Qt5 runtime
        # deps live in the build tree / conan package folders.  Symlink them
        # next to the test binaries so the loader can resolve (kcoreaddons5).
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
        # The project installs its own KF5ItemViewsConfig.cmake with proper
        # dependency tracking; use cmake_find_mode=none so CMakeDeps does not
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5ItemViews"]
