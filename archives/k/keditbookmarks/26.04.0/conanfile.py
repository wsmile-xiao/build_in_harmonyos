#!/usr/bin/env python3
"""Conan recipe for keditbookmarks 26.04.0 on HarmonyOS PC (aarch64).

keditbookmarks is the KDE bookmark editor (KDE Gear application). It ships
two executables (keditbookmarks GUI editor + kbookmarkmerger CLI) and one
private shared library (libkbookmarkmodel).

OHOS adaptations (patch 0001, applied on OHOS only):
  - KF6::Parts dependency removed: kparts is not published on the ohpcd
    registry and its only use (FavIconUpdater::downloadIconUsingWebBrowser +
    FavIconWebGrabber) loaded a text/html KPart at runtime - no HTML part
    exists on HarmonyOS PC, so that fallback path was dead code. The
    KIO-based favicon flow (KIO::favIconForUrl + KIO::FavIconRequestJob)
    is kept.
  - Qt6 DBus component removed: Qt6::DBus is not in the published
    qtbase/6.11.1 line (the KF6 6.14 baseline). The single-instance
    detection dialog (askUser) enumerated the D-Bus session bus and the
    KEBApp constructor registered a D-Bus object; HarmonyOS PC has no
    session bus so both were runtime no-ops / dead code.
  - find_package(Qt6) COMPONENTS trimmed to Core (DBus dropped).
  - find_package(KF6) COMPONENTS: Parts dropped, the rest resolves from
    the published 6.14.0 line (kio, kbookmarks, kxmlgui, kconfigwidgets,
    ktextwidgets, kiconthemes -> KF6::IconWidgets, kcompletion, kcodecs,
    kcoreaddons, ki18n, kwidgetsaddons, kwindowsystem, kcrash).
  - KF6DocTools stays OPTIONAL and is not found on ohpcd (kdoctools
    6.19.0 conflicts with the 6.14 baseline; audiocd 26.04.3 precedent) -
    the doc/ handbook subdirectory is simply skipped upstream.
  - KF_IGNORE_PLATFORM_CHECK=TRUE (KDE platform whitelist bypass).
  - ki18n_install(po) is gated upstream by KF_SKIP_PO_PROCESSING=ON
    (lconvert / Qt6 LinguistTools not shipped).
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable; conan_cmakedeps_paths
    .cmake written manually (qtbase and KF6 packages use
    cmake_find_mode=none).

Upstream tests: BUILD_TESTING=ON registers kbookmarkmodeltest
(src/kbookmarkmodel/tests, QTest). It is executed via ctest inside the
build with an offscreen Qt platform and a sandboxed HOME/XDG tree.
"""
import glob
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KeditbookmarksConan(ConanFile):
    name = "keditbookmarks"
    version = "26.04.0"
    description = (
        "KDE bookmark editor - keditbookmarks GUI organizer/editor and "
        "kbookmarkmerger CLI, with the private kbookmarkmodel library"
    )
    license = "GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://invent.kde.org/utilities/keditbookmarks"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/keditbookmarks-26.04.0.tar.xz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Published KF6 6.14.0 baseline line (same as kio/6.14.0, kxmlgui/
        # 6.14.0, kbookmarks/6.14.0) so the whole graph reuses published
        # binaries built against the same qtbase/6.11.1 (no Qt6DBus).
        self.requires("qtbase/6.11.1")
        self.requires("kcodecs/6.14.0")
        self.requires("kcompletion/6.14.0")
        self.requires("kconfig/6.14.0")
        self.requires("kconfigwidgets/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("kcrash/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kiconthemes/6.14.0")  # provides KF6::IconWidgets
        self.requires("kio/6.14.0")  # KIOCore (favIconForUrl) + KIOGui
        self.requires("kbookmarks/6.14.0")
        self.requires("ktextwidgets/6.14.0")  # KF6::IconWidgets dep chain
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("kwindowsystem/6.14.0")
        self.requires("kxmlgui/6.14.0")
        # kio/6.14.0 link-time requirement: the OHOS SDK lld depends on
        # libxml2.so.16 (libxml2/2.15.3 SONAME); its lib dir is injected
        # into LD_LIBRARY_PATH (kio recipe precedent).
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # No Platform/HarmonyOS module -> supply -Wl,-soname explicitly
        # (baloo 26.04.3 precedent) for libkbookmarkmodel.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])
        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        # qtbase and the KF6 packages use cmake_find_mode=none, so the
        # generated conan_cmakedeps_paths.cmake would not contain their
        # lib/cmake dirs. Create it manually (baloo/libkdegames precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                    % dep.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s")' % dep.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % dep.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % dep.package_folder
                )
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake)
            lines.append('list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake)
        if self.settings.os == "OHOS":
            # OHOS sysroot usr/include for CMake find_path() probes
            # (baloo 26.04.3 precedent).
            for sdk_inc in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/"
                    "sysroot/usr/include")):
                lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s")' % sdk_inc)
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder,
                                  "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH",
                                 os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH",
                                 os.path.join(dep.package_folder, "lib", "plugins"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            env.prepend_path("LD_LIBRARY_PATH",
                             os.path.join(self.build_folder, rel))
        return env

    def _build_env(self):
        # Host tools (moc, kconfig_compiler_kf6, qtpaths) are plain
        # executables with no RPATH; they must see the conan Qt/KF libs,
        # and /system/lib64 provides the compatible libc++_shared.so.
        # It is prepended LAST (so it ends up FIRST) because the SDK
        # aarch64-linux-ohos/libc++.so is a linker script that the runtime
        # loader cannot use - shadowing it is required for the Qt host
        # tools to start (kconfig 6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0
        # precedent, and the ohos-aarch64 profile comment).
        env = self._runtime_env()
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # libxml2/2.15.3: the OHOS SDK lld needs libxml2.so.16 at link
        # time (kio/6.14.0 precedent).
        libxml2 = self.dependencies.get("libxml2")
        if libxml2 and libxml2.package_folder:
            env.prepend_path("LD_LIBRARY_PATH",
                             os.path.join(libxml2.package_folder, "lib"))
        return env

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Upstream registers exactly one ctest target: kbookmarkmodeltest
        # (src/kbookmarkmodel/tests, ecm_add_test, QTest). Sandbox env:
        # offscreen Qt platform + isolated HOME/XDG tree (libkdegames /
        # ktextwidgets precedent).
        env = self._runtime_env()
        # OHOS sandbox libc++ shadow fix: the SDK aarch64-linux-ohos
        # libc++.so is a linker script the runtime loader cannot use;
        # /system/lib64 carries the compatible libc++_shared.so and must
        # come first (kconfig 6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0
        # precedent).
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        env.define("QT_QPA_PLATFORM", "offscreen")
        home = os.path.join(self.build_folder, "test-home")
        tmp = os.path.join(self.build_folder, "test-tmp")
        xdg = os.path.join(self.build_folder, "xdg-runtime")
        for d in (home, tmp, xdg):
            os.makedirs(d, exist_ok=True)
        os.chmod(xdg, 0o700)
        env.define("HOME", home)
        env.define("TMPDIR", tmp)
        env.define("TEMP", tmp)
        env.define("TMP", tmp)
        env.define("XDG_RUNTIME_DIR", xdg)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        self._prepare_test_runtime_links()
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "%s" --output-on-failure --no-tests=error'
                % self.build_folder
            )

    def _prepare_test_runtime_links(self):
        # Published KF6 binaries carry build-tree relative DT_NEEDED
        # entries ("../../bin/libKF6*.so"); the musl loader resolves them
        # relative to the test process cwd (ctest runs the test binary in
        # its CMakeLists dir, so "../../bin" resolves inside the build
        # tree). Provide compatibility links at every plausible bin
        # location (ktextwidgets / kxmlgui / libkdegames precedent).
        import shutil
        candidate_bases = [
            self.build_folder,
            os.path.normpath(os.path.join(self.build_folder, os.pardir)),
            os.path.normpath(os.path.join(self.build_folder, "src")),
            os.path.normpath(os.path.join(
                self.build_folder, "src", "kbookmarkmodel")),
            os.path.normpath(os.path.join(
                self.build_folder, "src", "kbookmarkmodel", "tests")),
        ]
        roots = []
        for base in candidate_bases:
            roots.append(os.path.join(base, "bin"))
            roots.append(os.path.normpath(os.path.join(base, os.pardir, "bin")))
        sources = []
        for rel in ("bin", "lib"):
            sources.extend(glob.glob(
                os.path.join(self.build_folder, rel, "lib*.so*")))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                sources.extend(glob.glob(
                    os.path.join(dep.package_folder, "lib", "lib*.so*")))
        seen = set()
        for root in roots:
            if root in seen or not os.path.isdir(os.path.dirname(root)):
                continue
            seen.add(root)
            os.makedirs(root, exist_ok=True)
            for src in sources:
                dst = os.path.join(root, os.path.basename(src))
                if os.path.exists(src) and not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.install()

    def package_info(self):
        # Application package: executables in bin/, private shared library
        # libkbookmarkmodel in lib/. No downstream CMake consumption is
        # advertised (upstream installs no config files for the private
        # lib), so plain bindirs/libdirs/libs info is provided.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.package_folder, "plugins")
        )
        self.runenv_info.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.package_folder, "lib", "plugins")
        )
