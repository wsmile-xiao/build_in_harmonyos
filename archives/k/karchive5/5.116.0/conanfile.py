#!/usr/bin/env python3
"""Conan recipe for karchive5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

karchive is the KDE Frameworks archive library (libKF5Archive): it provides
KArchive / KZip / KTar / KAr / KRcc plus transparent compression filters for
gzip, bzip2, xz/LZMA and zstd.

OHOS-specific adaptations (validated against the sibling KF5 recipes
ki18n5/5.116.0 and kimageformats5/5.116.0):
  - QT_MAJOR_VERSION=5 so the project takes the Qt5 code paths and finds
    qt5-qtbase/5.15.2.2 (KF5 line still targets Qt5).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (HarmonyOS
    is not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON: qt5-qtbase ships no LinguistTools, so the
    translation catalog generation must be skipped.
  - HarmonyOS is not mapped to the Linux CMake platform, so
    CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG would be undefined and the
    produced .so files would lack DT_SONAME (W3 CI L5 gate). Set the soname
    flag plus CMAKE_PLATFORM_NO_VERSIONED_SONAME (expat/attica5 pattern).
  - ecm is a tool_requires; ecm/6.26.0 satisfies find_package(ECM 5.116.0)
    because that call has minimum-version semantics.
  - qt5-qtbase ships per-module cmake configs but no aggregated Qt5Config, so
    CMakeDeps regenerates one via cmake_file_name "Qt5".
  - CMAKE_AUTOMOC_EXECUTABLE / CMAKE_AUTORCC_EXECUTABLE point at the
    qt5-qtbase bin/moc and bin/rcc (CMakeDeps does not export them).
  - The compression backends are consumed as Conan packages instead of the
    host /lib (R26): zlib (REQUIRED upstream), bzip2 (RECOMMENDED), xz
    (optional LibLZMA) and zstd (optional, probed through pkg-config).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KArchive5Conan(ConanFile):
    name = "karchive5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - Qt addon providing access to numerous types of archives"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/karchive"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
        # Upstream find_package(ZLIB) is TYPE REQUIRED and KF5Archive links
        # ZLIB::ZLIB unconditionally.
        #
        # qt5-qtbase/5.15.2.2 pins zlib/1.3.1, whose published libz.a is a
        # non-PIC static archive: linking it into our shared libKF5Archive.so
        # fails on AArch64 with
        #   relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against
        #   symbol 'z_errmsg'; recompile with -fPIC
        # zlib/1.3.1.1 is the same upstream version rebuilt with -fPIC
        # (knowledge E541/E533). force=True both resolves the version conflict
        # against qt5-qtbase's zlib/1.3.1 pin and keeps zlib as a consuming
        # requirement, so its package folder is available in generate()
        # (a plain override=True would leave package_folder as None and the
        # FindZLIB search roots could not be emitted).
        self.requires("zlib/1.3.1.1", force=True)
        # BZip2 is TYPE RECOMMENDED; keep it enabled so the .bz2 filter is
        # actually built (a missing backend would silently drop functionality).
        self.requires("bzip2/1.0.8")
        # Optional xz/LZMA backend (find_package(LibLZMA)) - adds k7zip + kxz.
        self.requires("xz/5.6.2")
        # Optional zstd backend, probed via pkg_check_modules(libzstd).
        self.requires("zstd/1.5.7")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Regenerate a clean aggregated Qt5Config (qt5-qtbase only ships
        # per-module configs; find_package(Qt5Core) needs one).
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        # The compression backends are left to CMake's own Find*.cmake modules
        # (the ohpcd zlib/1.3.1.1, bzip2/1.0.8 and xz/5.6.2 recipes ship no
        # cmake_file_name/target_name, so their CMakeDeps configs would only
        # define the lowercase zlib::zlib style targets the project never
        # links). conan_cmakedeps_paths.cmake below puts their package folders
        # on CMAKE_PREFIX_PATH/LIBRARY_PATH/INCLUDE_PATH so FindZLIB finds the
        # PIC zlib, and FindBZip2/FindLibLZMA define the canonical targets.
        # The mixed-case result variables the CMakeDeps configs set
        # (BZip2_FOUND, LibLZMA_FOUND) are aliased to the uppercase spellings
        # src/CMakeLists.txt reads, otherwise those backends are silently
        # compiled out (config-compression.h ends up all-zero).
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # SONAME emission on OHOS (see module docstring).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        # ECM's CMakeDeps-generated ECMConfig.cmake does not propagate
        # ECM_MODULE_PATH; set it manually so the KDE cmake modules
        # (KDEInstallDirs, KDECMakeSettings, ...) are found.
        # The CMakeDeps configs for the compression backends only define the
        # lowercase zlib::zlib style targets and set mixed-case result
        # variables, neither of which upstream uses. conan_toolchain.cmake
        # forces CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, which makes
        # find_package(ZLIB/BZip2/LibLZMA) hit those configs. Flip it back to
        # OFF after project() and before the dependency lookups so CMake's own
        # Find modules run: they define the canonical ZLIB::ZLIB /
        # BZip2::BZip2 / LibLZMA::LibLZMA targets and the uppercase
        # ZLIB_FOUND / BZIP2_FOUND / LIBLZMA_FOUND variables the project
        # reads (knowledge DRAFT-13532, getdns 1.7.3 precedent).
        inject = os.path.join(self.generators_folder,
                              "karchive5-disable-prefer-config.cmake")
        with open(inject, "w", encoding="utf-8") as fh:
            fh.write(
                "# Generated by the karchive5 recipe (see conanfile.py).\n"
                "# Let the upstream Find modules win over the CMakeDeps\n"
                "# configs for the compression backends.\n"
                "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\n"
            )
        tc.variables["CMAKE_PROJECT_INCLUDE"] = inject

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_DIR"] = os.path.join(ecm_share, "cmake")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qt5 = self.dependencies["qt5-qtbase"]
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

        tc.generate()

        # find_package(ECM 5.116.0 NO_MODULE) needs ECMConfig.cmake on the
        # config-mode search path; qtbase's native Qt5Core config needs its
        # cmake dir; zstd is located through a pkg-config file. The toolchain
        # only populates CMAKE_PREFIX_PATH / CMAKE_MODULE_PATH from its else
        # branch when conan_cmakedeps_paths.cmake does NOT exist - classic
        # CMakeDeps never creates that file, so write it here.
        extra_paths = []
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            extra_paths.append(
                ('list(PREPEND CMAKE_MODULE_PATH "%s")\n'
                 'list(PREPEND CMAKE_PREFIX_PATH "%s")') % (ecm_cmake, ecm_cmake)
            )
        qt_pkg = qt5.package_folder
        extra_paths.append(
            ('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")\n'
             'list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")\n'
             'list(PREPEND CMAKE_INCLUDE_PATH "%s/include")') % (qt_pkg, qt_pkg, qt_pkg)
        )
        # Compression backends: CMakeDeps emits only lowercase configs for
        # these (the ohpcd zlib/bzip2/xz recipes declare no cmake_file_name or
        # cmake_target_name), so upstream's FindZLIB / FindBZip2 / FindLibLZMA
        # have to resolve them. Give those modules explicit search roots; they
        # define the canonical ZLIB::ZLIB / BZip2::BZip2 / LibLZMA::LibLZMA
        # targets upstream links.
        for dep_name in ("zlib", "bzip2", "xz"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                dep_pkg = dep.package_folder
                extra_paths.append(
                    ('list(PREPEND CMAKE_PREFIX_PATH "%s")\n'
                     'list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")\n'
                     'list(PREPEND CMAKE_INCLUDE_PATH "%s/include")')
                    % (dep_pkg, dep_pkg, dep_pkg)
                )
        # zstd is probed with pkg_check_modules(LibZstd libzstd) and linked as
        # PkgConfig::LibZstd. The ohpcd zstd/1.5.7 package ships a
        # NON-relocatable libzstd.pc (hardcoded prefix=/usr/local) and the
        # host pkg-config does not look in the package folder, so the probe
        # reports "No package 'libzstd' found". Define PkgConfig::LibZstd and
        # LibZstd_FOUND ourselves against the Conan package before the project
        # runs its probe; pkg_check_modules then leaves the existing target
        # alone (akonadi 25.12.3 precedent). PKG_CONFIG_PATH is also exported
        # in the build env (see _runtime_env) so the probe can find the .pc.
        zstd = self.dependencies.get("zstd")
        if zstd and zstd.package_folder:
            zstd_pkg = zstd.package_folder
            zstd_lib = None
            for candidate in ("libzstd.so", "libzstd.a"):
                candidate_path = os.path.join(zstd_pkg, "lib", candidate)
                if os.path.isfile(candidate_path):
                    zstd_lib = candidate_path
                    break
            if zstd_lib is None:
                raise ConanException(
                    "zstd package does not provide lib/libzstd.so or libzstd.a"
                )
            extra_paths.append(
                'if(NOT TARGET PkgConfig::LibZstd)\n'
                '  add_library(PkgConfig::LibZstd UNKNOWN IMPORTED)\n'
                '  set_target_properties(PkgConfig::LibZstd PROPERTIES\n'
                '    IMPORTED_LOCATION "%s"\n'
                '    INTERFACE_INCLUDE_DIRECTORIES "%s/include"\n'
                '  )\n'
                '  set(LibZstd_FOUND TRUE)\n'
                'endif()\n'
                'set(LibZstd_FOUND TRUE)' % (zstd_lib, zstd_pkg)
            )
        # The CMakeDeps config files for the compression backends set the
        # mixed-case result variables (BZip2_FOUND, LibLZMA_FOUND), but
        # src/CMakeLists.txt reads the uppercase spellings (BZIP2_FOUND,
        # LIBLZMA_FOUND). Flipping CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF (see
        # CMAKE_PROJECT_INCLUDE above) makes the Find modules run, which set
        # both the canonical targets and the uppercase variables, so no
        # aliasing is needed here.
        extra_paths.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")\n'
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            # PREFER_CONFIG is deliberately left OFF (see CMAKE_PROJECT_INCLUDE
            # above) so the upstream Find modules resolve the compression
            # backends; the paths below still make qtbase/ECM configs visible.
            f.write(
                "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\n"
                + "\n".join(extra_paths) + "\n"
            )

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # Qt5CoreConfigExtrasMkspecDir.cmake hardcodes
        # <pkg>/../b/mkspecs/linux-clang (a build-tree path that does not
        # exist in the conan cache). attica-kf5/5.116.0 validated workaround:
        # copy the mkspecs tree from the package folder to the expected spot.
        #
        # karchive additionally pulls in Qt's qplatformdefs.h (karchive.cpp /
        # kzip.cpp), and mkspecs/linux-clang/qplatformdefs.h starts with
        # #include "../common/posix/qplatformdefs.h". Copying only the
        # linux-clang subdirectory therefore fails with
        #   fatal error: '../common/posix/qplatformdefs.h' file not found
        # so mirror the whole mkspecs tree instead of a single directory.
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs"
        )
        if os.path.isdir(source) and not os.path.exists(expected):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected)

    def _runtime_env(self):
        env = Environment()
        # Host tools (moc/rcc) from qt5-qtbase need the system libc++_shared.so
        # which is not on the default loader path.
        if os.path.isdir("/system/lib64"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "PATH", os.path.join(dep.package_folder, "bin")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return env

    def _pkgconfig_wrapper_dir(self):
        """Create a pkg-config wrapper that redefines the zstd prefix.

        The ohpcd zstd/1.5.7 package ships libzstd.pc with a hardcoded
        prefix=/usr/local, so a plain pkg_check_modules() probe reports
        /usr/local/include and /usr/local/lib. Invoking pkg-config with
        --define-variable=prefix=<conan package> makes the .pc relocate to the
        package folder without patching the dependency's file.
        Returns the wrapper directory, or None when zstd is absent.
        """
        zstd = self.dependencies.get("zstd")
        if not zstd or not zstd.package_folder:
            return None
        wrapper_dir = os.path.join(self.build_folder, "pkgconfig-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        real_pkg_config = shutil.which("pkg-config") or "pkg-config"
        wrapper = os.path.join(wrapper_dir, "pkg-config")
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write(
                "#!/bin/sh\n"
                "# Generated by the karchive5 recipe: relocate the zstd .pc.\n"
                'exec "%s" --define-variable=prefix="%s" "$@"\n'
                % (real_pkg_config, zstd.package_folder)
            )
        os.chmod(wrapper, 0o755)
        return wrapper_dir

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        qt5 = self.dependencies["qt5-qtbase"]
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        cmake = CMake(self)
        build_env = self._runtime_env()
        # Make the zstd .pc probe resolve against the Conan package: put its
        # pkgconfig dir on PKG_CONFIG_PATH and relocate the hardcoded
        # /usr/local prefix through a pkg-config wrapper.
        zstd = self.dependencies.get("zstd")
        if zstd and zstd.package_folder:
            for pc_rel in (os.path.join("lib", "pkgconfig"),
                           os.path.join("share", "pkgconfig")):
                pc_dir = os.path.join(zstd.package_folder, pc_rel)
                if os.path.isfile(os.path.join(pc_dir, "libzstd.pc")):
                    build_env.prepend_path("PKG_CONFIG_PATH", pc_dir)
                    break
            wrapper_dir = self._pkgconfig_wrapper_dir()
            if wrapper_dir:
                build_env.prepend_path("PATH", wrapper_dir)
        with build_env.vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_env = self._runtime_env()
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
        """Generate a test-only shared-mime-info database.

        KTar decides whether to compress on write by looking up the file name
        in QMimeDatabase. The OHOS runner's system MIME database knows the
        gzip/bzip2/xz compressed-tar types but has no zstd entry, so a
        ".tar.zst" falls back to application/octet-stream, KTar writes a plain
        uncompressed tar, and the upstream karchivetest rows that round trip
        .tar.zst fail ("ZSTD_decompressStream ... Unknown frame descriptor",
        'totalSize > 26000' returned FALSE).

        Emit the compressed-tar MIME types the upstream tests exercise, zstd
        included, and expose the tree through XDG_DATA_DIRS (knowledge
        precedent: karchive 6.26.0). This only affects the test run, not the
        packaged library.
        """
        mime_root = os.path.join(self.build_folder, "test-mime", "share")
        mime_packages = os.path.join(mime_root, "mime", "packages")
        os.makedirs(mime_packages, exist_ok=True)
        with open(os.path.join(mime_packages, "freedesktop.org.xml"),
                  "w", encoding="utf-8") as f:
            f.write(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">\n'
                '  <mime-type type="application/x-gzip">\n'
                '    <comment>gzip archive</comment>\n'
                '    <glob pattern="*.gz"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/gzip">\n'
                '    <sub-class-of type="application/x-gzip"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-bzip2">\n'
                '    <comment>bzip2 archive</comment>\n'
                '    <glob pattern="*.bz2"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-bzip">\n'
                '    <comment>bzip1 archive</comment>\n'
                '    <glob pattern="*.bz"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-lzma">\n'
                '    <comment>lzma archive</comment>\n'
                '    <glob pattern="*.lzma"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-xz">\n'
                '    <comment>xz archive</comment>\n'
                '    <glob pattern="*.xz"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/zstd">\n'
                '    <comment>zstd archive</comment>\n'
                '    <glob pattern="*.zst"/>\n'
                '    <glob pattern="*.zstd"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-tar">\n'
                '    <comment>tar archive</comment>\n'
                '    <glob pattern="*.tar"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-compressed-tar">\n'
                '    <sub-class-of type="application/x-gzip"/>\n'
                '    <glob pattern="*.tar.gz"/>\n'
                '    <glob pattern="*.tgz"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-bzip2-compressed-tar">\n'
                '    <sub-class-of type="application/x-bzip2"/>\n'
                '    <glob pattern="*.tar.bz2"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-bzip-compressed-tar">\n'
                '    <sub-class-of type="application/x-bzip"/>\n'
                '    <glob pattern="*.tar.bz"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-lzma-compressed-tar">\n'
                '    <sub-class-of type="application/x-lzma"/>\n'
                '    <glob pattern="*.tar.lzma"/>\n'
                '    <glob pattern="*.tlzma"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-xz-compressed-tar">\n'
                '    <sub-class-of type="application/x-xz"/>\n'
                '    <glob pattern="*.tar.xz"/>\n'
                '    <glob pattern="*.txz"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-zstd-compressed-tar">\n'
                '    <sub-class-of type="application/zstd"/>\n'
                '    <glob pattern="*.tar.zst"/>\n'
                '    <glob pattern="*.tzst"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="image/svg+xml-compressed">\n'
                '    <sub-class-of type="application/x-gzip"/>\n'
                '  </mime-type>\n'
                '  <mime-type type="application/x-gzdvi">\n'
                '    <sub-class-of type="application/x-gzip"/>\n'
                '  </mime-type>\n'
                '</mime-info>\n'
            )
        return mime_root

    def _prepare_ctest_runtime_links(self):
        # CTest discovers executables in <build>/bin; their libKF5Archive and
        # Qt5 runtime deps live in the build tree / conan package folders.
        # Symlink them next to the test binaries so the linker resolves.
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
        # The project installs its own KF5ArchiveConfig.cmake with proper
        # dependency tracking (find_dependency on Qt5Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Archive"]
