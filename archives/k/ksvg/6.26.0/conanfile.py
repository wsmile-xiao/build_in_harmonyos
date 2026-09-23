#!/usr/bin/env python3
"""Conan recipe for ksvg 6.26.0 on HarmonyOS PC.

ksvg is a KDE Frameworks 6 tier-3 library for rendering SVG-based themes
with stylesheet re-coloring and on-disk caching. It ships two artifacts:
  - libKF6Svg.so (core: KSvg::Svg / KSvg::FrameSvg / KSvg::ImageSet,
    QImage/QPainter software rendering path)
  - org.kde.ksvg QML plugin (declarativeimports: SvgItem / FrameSvgItem for
    Qt Quick scenes)

OHOS-specific adaptations (KF6 6.26 chain pattern, knotifications PR #8662 /
kirigami 6.18.0 precedents):
  - Patch 0001 lowers KF_DEP_VERSION 6.26.0 -> 6.18.0 to match the published
    ohpcd caps: karchive 6.19.0, kcolorscheme 6.18.0, kguiaddons 6.18.0,
    kirigami 6.18.0 (all >= 6.18.0).
  - Full build including the QML plugin: qtdeclarative/6.11.1 (Qt6Qml/
    Qt6Quick/Qt6QuickControls2) and qtsvg/6.11.1 (Qt6Svg) are published to
    ohpcd, so unlike knotifications (which had to skip QML) ksvg can build
    declarativeimports. kirigami/6.18.0 provides KF6::KirigamiPlatform.
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS not in KDE platform list).
  - BUILD_TESTING=ON: upstream autotests (plasmasvg-svgtest/framesvgtest/
    imagesettest) exercise the QImage software rendering path, which works
    headless with QT_QPA_PLATFORM=offscreen; they need Qt6::Qml for linking
    (upstream autotests/CMakeLists links Qt6::Qml) plus KF6::ConfigGui.
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project relies on.
  - conan_cmakedeps_paths.cmake written manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH.
  - qml tooling (qmlcachegen/qmlimportscanner/qmltyperegistrar from the
    qtdeclarative package, arm64 OHOS ELF binaries) put on PATH so
    ecm_add_qml_module / ecm_finalize_qml_module work at build time
    (kirigami 6.18.0 precedent).
  - SONAME flag injection: native OHOS builds leave CMake in the Generic
    platform module which has no shared-library SONAME rule; inject the
    Linux-style soname flag so VERSION/SOVERSION take effect (kcodecs
    6.26.0 fix 76da86d28c precedent, E330 knowledge entry).
  - /system/lib64 prepended to LD_LIBRARY_PATH for configure/build/tests
    (sandbox libc++_shared.so shadowing, kconfig 6.26.0 precedent).
  - zlib/zstd in the graph so karchive's exported find_dependency(ZLIB) and
    pkg_check_modules(LibZstd) resolve (kpackage 6.26.0 precedent).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KsvgConan(ConanFile):
    name = "ksvg"
    version = "6.26.0"
    description = "KDE Frameworks 6 - SVG theme rendering with stylesheet recoloring and caching"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/ksvg"
    url = "https://invent.kde.org/frameworks/ksvg"
    topics = ("kde", "frameworks", "svg", "qt", "theme")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # Qt6Qml/Qt6Quick/Qt6QuickControls2 for the declarativeimports plugin
        # and the upstream autotests (linked against Qt6::Qml).
        self.requires("qtdeclarative/6.11.1")
        # Qt6Svg renderer backend for the core library (private link).
        self.requires("qtsvg/6.11.1")
        # KF6 chain, pinned to the published ohpcd caps (see patch 0001).
        # kcolorscheme/6.18.0 locks kconfig/6.18.0 in its exported config,
        # so the whole KF6 chain is kept at 6.18.0 to avoid a version
        # conflict with kconfig/6.26.0.
        self.requires("kconfig/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("karchive/6.19.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("kirigami/6.18.0")
        # karchive/6.19.0 exports KF6ArchiveConfig.cmake which calls
        # find_dependency(ZLIB) and pkg_check_modules(LibZstd); the
        # transitive zlib/zstd packages must be in the consumer graph
        # (kpackage 6.26.0 precedent). KArchive_HAVE_OPENSSL=TRUE in the
        # published package makes find_dependency(OpenSSL) unconditional,
        # so OpenSSL is required in the graph too (kpackage precedent).
        self.requires("zlib/1.3.1.1")
        self.requires("zstd/1.5.7")
        self.requires("openssl/3.5.6.1")

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
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # The tools/ subdirectory (split-plasma-svgs) is only built with
        # BUILD_TOOLS=ON; upstream default is OFF, keep it that way.
        tc.variables["BUILD_TOOLS"] = "OFF"
        # QML module plugin goes to <prefix>/qml (ecm_finalize_qml_module
        # DESTINATION ${KDE_INSTALL_QMLDIR}); force the libdir-relative
        # layout so the plugin lands in lib/qml alongside the libs.
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_INSTALL_QMLDIR"] = "lib/qml"

        # Native builds on the HarmonyOS device leave CMake in the Generic
        # platform module (no CMAKE_SYSTEM_NAME because os_build == os_host
        # == OHOS), which has no shared-library SONAME rule. Without this
        # flag CMake drops -Wl,-soname and the resulting libKF6Svg.so has
        # no DT_SONAME (CI L5a gate) and the exported CMake targets get
        # IMPORTED_NO_SONAME TRUE (L5c). Inject the Linux-style soname flag
        # so VERSION/SOVERSION target properties take effect (kcodecs
        # 6.26.0 fix 76da86d28c precedent, E330 knowledge entry).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # The Qt6 metapackage config found first is qtbase's; the Qml/Quick/
        # QuickControls2 components live in the qtdeclarative package and Svg
        # in the qtsvg package. Qt6Config.cmake consults
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH for extra component prefixes
        # (kirigami 6.18.0 precedent).
        qt_extra = []
        for dep_name in ("qtdeclarative", "qtsvg"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_extra
            )

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ECMQmlModule,
        # ...) are found.
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
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Add every dependency's lib/cmake dir so find_package(Qt6*)/KF6*
            # and transitive find_dependency() chains all resolve.
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
            # karchive/6.19.0's exported KF6ArchiveConfig.cmake calls
            # pkg_check_modules(LibZstd IMPORTED_TARGET "libzstd"); expose
            # the transitive zstd package's pkg-config dir (kpackage 6.26.0
            # precedent).
            zstd = self.dependencies.get("zstd")
            if zstd and zstd.package_folder:
                zstd_pc = os.path.join(zstd.package_folder, "lib", "pkgconfig")
                if os.path.isdir(zstd_pc):
                    lines.append(
                        'set(ENV{PKG_CONFIG_PATH} '
                        f'"{zstd_pc}:$ENV{{PKG_CONFIG_PATH}}")'
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
            # ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool
            # during configure (ecm_query_qt -> QT_INSTALL_PREFIX). The
            # sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64
            # which shadows the compatible one; prepend /system/lib64 (and
            # the qtbase lib dir, already added by _library_runtime_env) so
            # the loader resolves the compatible libc++ first (kconfig
            # 6.26.0 / bluez-qt 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # ecm_add_qml_module / ecm_finalize_qml_module invoke the Qt QML
        # host tools (qmlcachegen, qmlimportscanner, qmltyperegistrar,
        # qmldom...) shipped inside the qtdeclarative package. The published
        # binaries are arm64 OHOS ELF executables, runnable on this device;
        # expose both bin/ and libexec/ on PATH (kirigami 6.18.0 precedent).
        qtdeclarative = self.dependencies.get("qtdeclarative")
        if qtdeclarative and qtdeclarative.package_folder:
            build_env.prepend_path(
                "PATH", os.path.join(qtdeclarative.package_folder, "libexec")
            )
            build_env.prepend_path(
                "PATH", os.path.join(qtdeclarative.package_folder, "bin")
            )
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
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "lib", "qml")
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
            # which shadows the compatible one; prepend /system/lib64 so test
            # executables resolve the compatible libc++ first (kconfig 6.26.0
            # / bluez-qt 6.28.0 precedent, same fix as _cmake_build_env).
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                test_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        # The upstream autotests render SVGs through the QImage software
        # path; run headless via the offscreen QPA platform plugin.
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
        test_env.define("XDG_DATA_HOME",
                        os.path.join(test_home, ".local", "share"))
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            # Upstream CTest add_test count in this feature set: 3
            # (plasmasvg-svgtest, plasmasvg-framesvgtest,
            # plasmasvg-imagesettest from autotests/); measured with
            # `ctest -N`. --no-tests=error keeps the run green only if the
            # count is genuinely 0, which it is not.
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error'.format(self.build_folder)
            )

    def _prepare_ctest_runtime_links(self):
        # The published kconfig/6.18.0 (and other KF6 packages built by the
        # same pipeline) record sibling libraries in DT_NEEDED as relative
        # paths like "../../bin/libKF6ConfigCore.so". The OHOS loader
        # resolves such relative NEEDED entries against the executable's
        # directory (test binaries live in <build>/Release/bin, so
        # "../../bin" resolves to <build>/bin). Place copies of every
        # runtime library there so the tests can load (kpackage 6.26.0
        # precedent).
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
        with self._library_runtime_env().vars(self).apply():
            cmake.install()

    def package_info(self):
        # The project installs its own KF6SvgConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Gui). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Svg"]
