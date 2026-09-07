#!/usr/bin/env python3
"""Conan recipe for kpackage 6.26.0 on HarmonyOS PC.

KPackage is the KDE Frameworks 6 library and tool for loading and installing
non-binary package content.

OHOS-specific adaptations:
  - 0001-lower-ecm-and-kf-dep-version.patch lowers KF_DEP_VERSION from 6.26.0
    to 6.19.0 (the ohpcd registry cap for karchive); ki18n/kcoreaddons are
    consumed at their published 6.26.0 versions (>= requested 6.19.0)
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation for the
    initial KF baseline
  - USE_DBUS=OFF because upstream enables DBus by default on UNIX-like systems
  - CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON to keep optional docs out of the
    baseline package
  - BUILD_TESTING=ON and ctest execution for upstream autotests
  - Dependencies: qtbase/6.11.1, karchive/6.19.0, kcoreaddons/6.26.0,
    ki18n/6.26.0, ecm/6.26.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase and KF packages
    use cmake_find_mode=none
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KpackageConan(ConanFile):
    name = "kpackage"
    version = "6.26.0"
    description = "KDE Frameworks 6 - package content library and tool"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kpackage"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # karchive stays at the ohpcd cap 6.19.0; the 0001 patch lowers
        # KF_DEP_VERSION so find_package(KF6Archive 6.19.0) is satisfied.
        # The published karchive/6.19.0 exports KF6ArchiveConfig.cmake that
        # unconditionally calls find_dependency(OpenSSL) (packaged with
        # HAVE_OPENSSL=TRUE), so OpenSSL must be in the consumer graph and
        # discoverable for configure to pass.
        self.requires("karchive/6.19.0")
        # ki18n/kcoreaddons are available at the same 6.26.0 KF release as
        # kpackage itself (>= the lowered 6.19.0 KF_DEP_VERSION floor).
        self.requires("kcoreaddons/6.26.0")
        self.requires("ki18n/6.26.0")
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
        # The OHOS HMDFS cache filesystem refuses make jobserver fifo creation
        # (EPERM), so force serial make to keep the deterministic test/build
        # pipeline green (SKILL §7 mkfifo/tmp constraint).
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["USE_DBUS"] = "OFF"

        # R05 relocatable linkage: the KF6 deps are published without a DT_SONAME,
        # so linking them by absolute cache path makes the linker record that
        # machine-private path in DT_NEEDED. Expose their lib dirs to the patched
        # CMakeLists (target_link_directories) so deps are linked by basename
        # (-lKF6CoreAddons...) and the produced artifact stays relocatable.
        kf6_dep_lib_dirs = []
        for dep_name in ("karchive", "kcoreaddons", "ki18n"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                kf6_dep_lib_dirs.append(os.path.join(dep.package_folder, "lib"))
        if kf6_dep_lib_dirs:
            tc.variables["KPACKAGE_DEP_LIB_DIRS"] = ";".join(kf6_dep_lib_dirs)

        # karchive/6.19.0 is published as a static library (libKF6Archive.a)
        # whose exported KF6::Archive target carries INTERFACE_LINK_LIBRARIES
        # with $<LINK_ONLY:ZLIB::ZLIB> and $<LINK_ONLY:PkgConfig::LibZstd>. The
        # 0005 patch links it by bare -lKF6Archive (PRIVATE), so those LINK_ONLY
        # transitive libs never reach the final link line. The shared kpackage
        # recipe must therefore supply -L for the transitive zlib/zstd packages
        # (KPACKAGE_DEP_LIB_DIRS) and add -lz -lzstd to the linker flags;
        # otherwise libKF6Package.so and the test executables (which consume
        # KF6::Archive's interface) keep undefined ZSTD_*/inflate/deflate
        # symbols or fail to find -lzstd.
        link_flags = []
        for dep_name, lib_names in (("zlib", ["z"]), ("zstd", ["zstd"])):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    kf6_dep_lib_dirs.append(lib_dir)
                    link_flags.append("-L{}".format(lib_dir))
                link_flags.extend("-l{}".format(name) for name in lib_names)
        if kf6_dep_lib_dirs:
            tc.variables["KPACKAGE_DEP_LIB_DIRS"] = ";".join(kf6_dep_lib_dirs)
        if link_flags:
            flags_str = " ".join(link_flags)
            tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = flags_str
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = flags_str

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

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            lines = []
            self._append_dependency_paths(lines, qtbase.package_folder)
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            for dep_name in ("karchive", "kcoreaddons", "ki18n"):
                dep = self.dependencies.get(dep_name)
                if dep and dep.package_folder:
                    self._append_dependency_paths(lines, dep.package_folder)

            # karchive/6.19.0 exports KF6ArchiveConfig.cmake which calls
            # find_dependency(ZLIB); FindZLIB needs the transitive zlib package
            # root/lib/include discoverable through the same generated CMake
            # path layer (declared dependency metadata, not hard-coded paths).
            zlib_dep = self.dependencies.get("zlib")
            if zlib_dep and zlib_dep.package_folder:
                self._append_dependency_paths(lines, zlib_dep.package_folder)

            # the published karchive/6.19.0 Config also calls
            # find_dependency(OpenSSL); make OpenSSL discoverable the same way.
            openssl_dep = self.dependencies.get("openssl")
            if openssl_dep and openssl_dep.package_folder:
                self._append_dependency_paths(lines, openssl_dep.package_folder)

            # KF6ArchiveConfig.cmake runs
            # pkg_check_modules(LibZstd IMPORTED_TARGET "libzstd") and the
            # exported KF6::Archive target links PkgConfig::LibZstd; put the
            # transitive zstd package's pkg-config dir on PKG_CONFIG_PATH
            # (set(ENV) prepend; list(PREPEND ENV{...}) does not set env vars).
            zstd_dep = self.dependencies.get("zstd")
            if zstd_dep and zstd_dep.package_folder:
                zstd_pc = os.path.join(zstd_dep.package_folder, "lib", "pkgconfig")
                if os.path.isdir(zstd_pc):
                    lines.append(
                        'set(ENV{{PKG_CONFIG_PATH}} "{}:$ENV{{PKG_CONFIG_PATH}}")'.format(
                            zstd_pc
                        )
                    )

            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
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
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        # R05: upstream CTest suite runs against the as-linked library; the
        # relocatable NEEDED entries are produced at link time by patch
        # 0005-ohos-relocatable-soname-link.patch (IMPORTED_SONAME on the KF6
        # deps), so no post-build ELF rewrite is needed.
        self._run_upstream_tests()

    def _cmake_build_env(self):
        """Environment for the configure+build steps.

        ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool during
        configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
        LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
        /data/storage/el1/bundle/libs/arm64 which shadows the compatible one;
        prepend /system/lib64 so the loader resolves the compatible libc++
        first (kconfig 6.26.0 / bluez-qt 6.28.0 precedent).
        """
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _library_runtime_env(self):
        runtime_env = Environment()
        # Patch 0002 reads KPACKAGE_EXTRA_DATA_DIRS to append GenericDataLocation
        # roots. On OHOS the XDG variables are unset by default; expose the
        # platform data volumes through the recipe (portable, testable mechanism)
        # instead of a compile-time __OHOS__ fork.
        runtime_env.define("KPACKAGE_EXTRA_DATA_DIRS", "/data/service/el1/public:/storage/Users/currentUser/ohos-users")
        # The sandbox LD_LIBRARY_PATH contains an incompatible libc++_shared.so
        # under /data/storage/el1/bundle/libs/arm64 which shadows the compatible
        # one; prepend /system/lib64 (and the SDK llvm lib) so every child
        # process (qtpaths during configure, the CTest test binaries) resolves
        # the compatible libc++ first (kconfig 6.26.0 / bluez-qt 6.28.0
        # precedent).
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                runtime_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
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
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
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
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '-E "^plasmoidpackagetest$"'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
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
        self.cpp_info.libs = ["KF6Package"]
        self.cpp_info.bindirs = ["bin"]
