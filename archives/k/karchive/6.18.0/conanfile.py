#!/usr/bin/env python3
"""Conan recipe for karchive 6.18.0 on HarmonyOS PC.

karchive is a KDE Frameworks 6 library for reading and writing archive files
(libKF6Archive.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalog generation for the
    initial KF baseline
  - WITH_BZIP2=OFF: avoid linking the current local static bzip2 archive into
    the shared KF library because that recipe does not guarantee PIC objects
  - WITH_LIBZSTD=OFF: the upstream zstd probe goes through host pkg-config, but
    the current OHOS runner does not provide pkg-config
  - BUILD_TESTING=ON and ctest execution for upstream autotests available in
    the current headless feature set
  - A minimal test-only MIME database is generated for gzip-derived MIME
    inheritance rows used by upstream kfiltertest and compressed-tar filename
    auto-detection used by upstream KTar tests
  - Dependencies: qtbase/6.11.1, zlib/1.3.2, xz/5.6.2, openssl/3.5.6.1,
    ecm/6.26.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KarchiveConan(ConanFile):
    name = "karchive"
    version = "6.18.0"
    description = "KDE Frameworks 6 - file compression and archive library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/karchive"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("zlib/1.3.2")
        self.requires("xz/5.6.2")
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
        tc.variables["BUILD_FUZZERS"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["WITH_BZIP2"] = "OFF"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_BZip2"] = "ON"
        tc.variables["WITH_LIBLZMA"] = "ON"
        tc.variables["WITH_OPENSSL"] = "ON"
        tc.variables["WITH_LIBZSTD"] = "OFF"

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

        xz = self.dependencies.get("xz")
        if xz:
            tc.variables["LIBLZMA_INCLUDE_DIR"] = os.path.join(
                xz.package_folder, "include"
            )
            for candidate in ("liblzma.so", "liblzma.a"):
                lib = os.path.join(xz.package_folder, "lib", candidate)
                if os.path.exists(lib):
                    tc.variables["LIBLZMA_LIBRARY"] = lib
                    break

        openssl = self.dependencies.get("openssl")
        if openssl:
            tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder
            tc.variables["OPENSSL_USE_STATIC_LIBS"] = "TRUE"

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = [
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            for dep_name in ("zlib", "xz", "openssl"):
                dep = self.dependencies.get(dep_name)
                if dep and dep.package_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )

            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

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
        test_env.define("XDG_DATA_DIRS", self._prepare_test_mime_database())
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_test_mime_database(self):
        mime_root = os.path.join(self.build_folder, "test-mime", "share")
        mime_packages = os.path.join(mime_root, "mime", "packages")
        os.makedirs(mime_packages, exist_ok=True)
        mime_xml = os.path.join(mime_packages, "freedesktop.org.xml")
        with open(mime_xml, "w") as f:
            f.write(
                """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-gzip">
    <comment>gzip archive</comment>
    <glob pattern="*.gz"/>
  </mime-type>
  <mime-type type="application/gzip">
    <sub-class-of type="application/x-gzip"/>
  </mime-type>
  <mime-type type="application/x-lzma">
    <comment>lzma archive</comment>
    <glob pattern="*.lzma"/>
  </mime-type>
  <mime-type type="application/x-lzip">
    <comment>lzip archive</comment>
    <glob pattern="*.lz"/>
  </mime-type>
  <mime-type type="application/x-xz">
    <comment>xz archive</comment>
    <glob pattern="*.xz"/>
  </mime-type>
  <mime-type type="application/x-tar">
    <comment>tar archive</comment>
    <glob pattern="*.tar"/>
  </mime-type>
  <mime-type type="application/x-compressed-tar">
    <sub-class-of type="application/x-gzip"/>
    <glob pattern="*.tar.gz"/>
    <glob pattern="*.tgz"/>
  </mime-type>
  <mime-type type="application/x-lzma-compressed-tar">
    <sub-class-of type="application/x-lzma"/>
    <glob pattern="*.tar.lzma"/>
    <glob pattern="*.tlzma"/>
  </mime-type>
  <mime-type type="application/x-lzip-compressed-tar">
    <sub-class-of type="application/x-lzip"/>
    <glob pattern="*.tar.lz"/>
  </mime-type>
  <mime-type type="application/x-xz-compressed-tar">
    <sub-class-of type="application/x-xz"/>
    <glob pattern="*.tar.xz"/>
    <glob pattern="*.txz"/>
  </mime-type>
  <mime-type type="image/svg+xml-compressed">
    <sub-class-of type="application/x-gzip"/>
  </mime-type>
  <mime-type type="application/x-gzdvi">
    <sub-class-of type="application/x-gzip"/>
  </mime-type>
</mime-info>
"""
            )
        return mime_root

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
        self.cpp_info.libs = ["KF6Archive"]
