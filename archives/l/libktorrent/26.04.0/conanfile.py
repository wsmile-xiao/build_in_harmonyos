#!/usr/bin/env python3
"""Conan recipe for libktorrent 26.04.0 — KDE BitTorrent protocol library.

libktorrent (KDE Gear 26.04.0) is the core BitTorrent protocol library
backing KTorrent: bencode codec, torrent/magnet metadata handling, peer
wire protocol, DHT, uTP, MSE encrypted handshake, disk IO with
preallocation, tracker and UPnP support.  Upstream target is the
KTorrent6 shared library plus a testlib consumed by the upstream
ecm_add_test suites.

Upstream test registration (38 ctest entries, counted from
src/*/tests/CMakeLists.txt ecm_add_test calls in the 26.04.0 tarball):
  bcodec 2, datachecker 1, dht 2, diskio 2, download 2, magnet 1,
  mse 1, net 3, peer 4, torrent 3, util 5, utp 12.

Dependency line: qtbase/6.11.1 + KF6 6.26 line (karchive/kcrash/ki18n/
kio/solid all published on 6.26.0, kio 6.26.0 recipe precedent),
ecm 6.26.0 as the build tool (version-matched ECM modules are
compatible with the 6.26 KF6 line, kgoldrunner 26.04.0 precedent).

Crypto backend: LibGcrypt (libgcrypt/1.12.2). The upstream OpenSSL path
needs the legacy provider for RC4; the ohpcd openssl/3.5.6.1 static
package ships no ossl-modules, so bt::InitLibKTorrent() would fail for
every RC4 consumer. LibGcrypt provides ARCFOUR natively.

OHOS adaptations (patches/0001-ohos-kiocore-only.patch):

* KIOWidgets trimmed to the KIOCore-only ohpcd baseline (the kio
  package publishes KIOCORE_ONLY: KIOGui/KIOWidgets/KIOFileWidgets
  are not built, kio 6.26.0 notes).  KF6::KIOWidgets replaced with
  KF6::KIOCore + KF6::ConfigCore (KSharedConfig, kconfig); the three
  widgets-only call sites (createDefaultJobUiDelegate /
  uiDelegate()->showErrorMessage) are commented out — KJob reports
  errors via error()/errorText() without a presenter, and the calls
  were the only KIOWidgets usage in the library.
* KIO::ERR_* enums: the JobUiDelegate include chain that carried
  kio/global.h is replaced with a direct <KIO/Global> include
  (job.cpp / singlefilecache.cpp).
* httprequest.cpp: explicit <QTcpSocket> include (the transitive
  include chain is not stable on the trimmed qtbase).
* All 38 ecm_add_test entries link Qt6::Gui explicitly: QTEST_MAIN
  expands to a QGuiApplication main whenever the TU sees any QtGui
  header, which depends on include order on the trimmed qtbase.
* KTorrent6Config.cmake.in: add the missing find_dependency calls
  for KF6Solid/KF6I18n — the KTorrent6Targets INTERFACE_LINK_LIBRARIES
  references them but the upstream template forgot the find_dependency,
  so every consumer's find_package(KTorrent6) would fail with "target
  KF6::Solid not found" (upstream bug, any platform).

Runtime environment: pure library; upstream tests run headless with
QT_QPA_PLATFORM=offscreen (Qt6::Test + Qt6::Gui only).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibktorrentConan(ConanFile):
    name = "libktorrent"
    version = "26.04.0"
    description = ("KDE BitTorrent protocol library - bencode, torrent and "
                   "magnet metadata, peer wire protocol, DHT, uTP, MSE "
                   "encrypted handshake (KTorrent core)")
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/network/libktorrent"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/libktorrent-26.04.0.tar.xz"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KF6 6.26 line — kio/6.26.0 is the anchor (all five required
        # frameworks are published on the 6.26 line; mixing 6.18/6.26
        # changes every package id and no prebuilt binaries match,
        # kgoldrunner lesson).
        self.requires("qtbase/6.11.1")
        self.requires("karchive/6.26.0", options={"shared": True})
        self.requires("kcrash/6.26.0", options={"shared": True})
        self.requires("ki18n/6.26.0", options={"shared": True})
        self.requires("kio/6.26.0", options={"shared": True})
        self.requires("solid/6.26.0", options={"shared": True})
        # header-only usage: boost/align, boost/smart_ptr, boost/circular_buffer
        self.requires("boost/1.90.0.3")
        # upstream cmake/FindLibGMP.cmake (classic module)
        self.requires("gmp/6.3.0.1")
        # crypto backend: LibGcrypt. The ohpcd openssl/3.5.6.1 package is a
        # static build without the legacy provider module (RC4 lives there);
        # bt::InitLibKTorrent() hard-fails when OSSL_PROVIDER_try_load(
        # "legacy") returns null, breaking 10 upstream tests at init.
        # libgcrypt provides ARCFOUR (RC4) natively, matching the upstream
        # USE_CRYPTO_BACKEND=LibGcrypt path.
        self.requires("libgcrypt/1.12.2")
        # libgcrypt's gcrypt.h includes <gpg-error.h>; the transitive_headers
        # flag on libgcrypt's requirement does not always surface the include
        # path through CMakeDeps — require it explicitly.
        self.requires("libgpg-error/1.55")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libktorrent is adapted for Linux and OHOS, not "
                f"{self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream 38 ecm_add_test entries are built and run via ctest
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Skip translation catalog generation (audiocd 26.04.3 precedent:
        # the CI worker msgfmt fails to load its own libintl).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # The kdoctools handbook toolchain is not part of the OHOS package
        # set (audiocd 26.04.3 precedent).
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "TRUE"
        # KDEInstallDirs single-prefix layout on conan (kgoldrunner precedent)
        tc.variables["KDE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # Crypto backend selection: LibGcrypt path (OpenSSL legacy provider
        # unavailable on the ohpcd static build, see requirements())
        tc.variables["USE_CRYPTO_BACKEND"] = "LibGcrypt"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_OpenSSL"] = "TRUE"
        # gcrypt.h includes <gpg-error.h>; surface the libgpg-error include
        # dir on the compile line (the FindLibGcrypt module only resolves
        # gcrypt.h itself).
        gpgerr = self.dependencies.get("libgpg-error")
        if gpgerr and gpgerr.package_folder:
            inc = os.path.join(gpgerr.package_folder, "include")
            tc.variables["CMAKE_CXX_FLAGS"] = f"-I{inc}"
        # XFS preallocation probes linux-only headers; keep the code but
        # let the check fail silently (graceful upstream path)
        tc.variables["WITH_XFS"] = "OFF"
        # ECM's own ECMConfig.cmake sets ECM_MODULE_PATH but the
        # CMakeDeps-generated one does not (audiocd precedent).
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
        if self.settings.os == "OHOS":
            # OHOS loader workaround (audiocd precedent): pin page size.
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
        tc.generate()

        # qtbase and the KF6 packages use cmake_find_mode=none, so
        # CMakeDeps does not generate conan_cmakedeps_paths.cmake. Create it
        # manually (audiocd / libkdegames / kgoldrunner precedent).
        lines = []
        # include every package whose cmake config may be reached through
        # find_dependency chains (KF6 configs find_dependency each other);
        # host dependencies + build tools (ecm) both contribute prefixes.
        all_pkgs = {}
        for dep in self.dependencies.values():
            if dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep in self.dependencies.host.values():
            if dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep in self.dependencies.build.values():
            if dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep_name in sorted(all_pkgs):
            pkg = all_pkgs[dep_name]
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
            for libdir in ("lib", "lib64"):
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/{libdir}")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/{libdir}")'
                )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")'
            )
            bindir = os.path.join(pkg, "bin")
            if os.path.isdir(bindir):
                lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{bindir}")')
        if ecm:
            ecm_pkg = ecm.package_folder
            ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{ecm_pkg}/bin")')
        # GMP: help the classic FindLibGMP module locate the conan package
        # (alkimia 8.2.1 precedent).
        gmp = self.dependencies.get("gmp")
        if gmp and gmp.package_folder:
            tc2 = None
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{gmp.package_folder}")'
            )
            # classic module search hints
            lines.append(
                f'set(GMP_INCLUDE_DIR "{os.path.join(gmp.package_folder, "include")}")'
            )
            gmp_libdir = os.path.join(gmp.package_folder, "lib")
            gmp_lib = os.path.join(gmp_libdir, "libgmp.so")
            if not os.path.isfile(gmp_lib):
                gmp_lib = os.path.join(gmp_libdir, "libgmp.a")
            lines.append(f'set(GMP_LIBRARIES "{gmp_lib}")')
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected (kio 6.26.0 recipe pattern).
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        # Host tools (kconfig_compiler / moc / uic / rcc / kjs) are OHOS
        # binaries needing libc++_shared from /system/lib64 plus the
        # dependency lib dirs on LD_LIBRARY_PATH (audiocd precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            import glob as _glob
            for llvm_lib in sorted(
                _glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        copy(self, "LICENSES",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["KTorrent6"]
        self.cpp_info.includedirs = ["include/libktorrent"]
        self.cpp_info.build_modules["cmake_find_package"].append(
            os.path.join("lib", "cmake")
        )
