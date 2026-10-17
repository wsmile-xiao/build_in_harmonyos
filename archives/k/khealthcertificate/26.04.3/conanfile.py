#!/usr/bin/env python3
"""Conan recipe for KHealthCertificate 26.04.3 on HarmonyOS PC.

KHealthCertificate is the KDE PIM health certificate parsing/verification
library (libKHealthCertificate.so): C++ API for EU DGC, Divoc, ICAO VDS,
NL CoronaCheck and SHC vaccination/test/recovery certificates, plus a small
CLI decoder (health-certificate-decode) and an optional QML plugin.

OHOS adaptation (pattern aligned with published kmime/25.12.3,
karchive/6.18.0 and knewstuff/6.14.0):
  - KF_IGNORE_PLATFORM_CHECK=TRUE, KF_SKIP_PO_PROCESSING=ON
  - BUILD_TESTING=ON: all 5 upstream QTest autotests executed via ctest
    (divoc/eudgc/icaovds/nlcoronacheck/shc parsers), offscreen
  - Qt6 Core/Network/Test from qtbase/6.11.1; Qt6 Qml (src/qml plugin) from
    the published qtdeclarative/6.11.1 split package
  - KF6 Archive/Codecs/I18n resolved via published 6.18.0 (KF_MIN_VERSION
    6.0.0 accepts them)
  - OpenSSL: static libcrypto.a from openssl/3.5.6.1
    (OPENSSL_USE_STATIC_LIBS, same as karchive)
  - ZLIB: static libz.a from zlib/1.3.2 via CMake FindZLIB module
  - runtime env + `<build>/../bin` symlink farm for DT_NEEDED quirks of
    published KF6/Qt6 binaries (knewstuff/kmime pattern)
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KHealthCertificateConan(ConanFile):
    name = "khealthcertificate"
    version = "26.04.3"
    description = "KDE PIM health certificate parsing and verification library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/pim/khealthcertificate"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # Qt6 Qml component for the src/qml plugin (knewstuff pattern)
        self.requires("qtdeclarative/6.11.1")
        # KF6 find_package(KF6 6.0.0 COMPONENTS Archive Codecs I18n)
        self.requires("karchive/6.18.0")
        self.requires("kcodecs/6.18.0")
        self.requires("ki18n/6.18.0")
        # signature verification (OpenSSL::Crypto) + EU DGC zlib data
        self.requires("openssl/3.5.6.1")
        self.requires("zlib/1.3.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # Test-time data only (must not leak into the consumer graph /
        # package_id, kfilemetadata shared-mime-info precedent):
        # - iso-codes: KF6 I18nLocaleData (KCountry) resolves ISO 3166-1
        #   country codes at runtime from iso-codes/json/iso_3166-1.json;
        #   the icaovds upstream autotest compares country() against the
        #   2-letter code ("AU") which needs the iso_3166-1 table.
        # - tzdata: the nlcoronacheck upstream autotest expects
        #   QTimeZone("Europe/Amsterdam") to be valid; OHOS ships no
        #   /usr/share/zoneinfo, so TZDIR/QT_ZONEINFO point at the tzdata
        #   package zoneinfo tree (kcalendarcore 6.26.0 precedent).
        self.tool_requires("iso-codes/4.20.1")
        self.tool_requires("tzdata/2026.3")

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
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        openssl = self.dependencies.get("openssl")
        if openssl:
            tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder
            tc.variables["OPENSSL_USE_STATIC_LIBS"] = "TRUE"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # Qt6 split-package component discovery: qtbase's Qt6Config.cmake
        # resolves REQUIRED COMPONENTS (Qml from qtdeclarative) only against
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH (knewstuff verified pattern).
        qt_extra = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                cmake_dir = os.path.join(dep.package_folder, "lib", "cmake")
                if os.path.isdir(cmake_dir) and any(
                        n.startswith("Qt6") for n in os.listdir(cmake_dir)):
                    qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables[
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

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
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    # package ROOT so that split configs under
                    # <pkg>/lib/cmake/Qt6Qml/ (and KF6*, ...) resolve
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}")'
                    )
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
            lines.append(
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
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
            # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the
            # SDK's llvm/lib directory; CI workers may not export it via
            # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link.
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
            # which shadows the compatible one; prepend /system/lib64 so
            # the loader resolves the compatible libc++ first (kconfig
            # 6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
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
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
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
            # which shadows the compatible one; prepend /system/lib64 so
            # test executables resolve the compatible libc++ first
            # (kconfig 6.26.0 / kcrash 6.26.0 precedent).
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
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
        # KF6 I18nLocaleData (KCountry) reads iso-codes JSON tables via
        # QStandardPaths::GenericDataLocation ("iso-codes/json/iso_3166-1.json").
        # OHOS has no /usr/share/iso-codes; stage the iso-codes package share
        # tree and point XDG_DATA_DIRS at it (kfilemetadata mime DB precedent).
        iso_codes = self.dependencies.build.get("iso-codes")
        if iso_codes and iso_codes.package_folder:
            test_env.prepend_path(
                "XDG_DATA_DIRS", os.path.join(iso_codes.package_folder, "share")
            )
        # The nlcoronacheck autotest expects QTimeZone("Europe/Amsterdam");
        # OHOS ships no /usr/share/zoneinfo so TZDIR/QT_ZONEINFO point at
        # the tzdata package zoneinfo tree (kcalendarcore 6.26.0 precedent).
        tzdata = self.dependencies.build.get("tzdata")
        if tzdata and tzdata.package_folder:
            zoneinfo = os.path.join(
                tzdata.package_folder,
                "lib", "python3.12", "site-packages", "tzdata", "zoneinfo",
            )
            if os.path.isdir(zoneinfo):
                test_env.define("TZDIR", zoneinfo)
                test_env.define("QT_ZONEINFO", zoneinfo)
        self._prepare_ctest_runtime_links()
        self._patch_ctest_qt_plugin_path()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _qt_plugin_path(self):
        plugin_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    plugin_dir = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(plugin_dir):
                        plugin_dirs.append(plugin_dir)
        plugin_dirs.append(os.path.join(self.build_folder, "bin"))
        return os.pathsep.join(plugin_dirs)

    def _patch_ctest_qt_plugin_path(self):
        build_bin = os.path.join(self.build_folder, "bin")
        full_plugin_path = self._qt_plugin_path()
        needle = f"QT_PLUGIN_PATH={build_bin}"
        replacement = f"QT_PLUGIN_PATH={full_plugin_path}"
        for test_file in glob.glob(
            os.path.join(self.build_folder, "**", "CTestTestfile.cmake"),
            recursive=True,
        ):
            with open(test_file) as f:
                content = f.read()
            if needle in content:
                with open(test_file, "w") as f:
                    f.write(content.replace(needle, replacement))

    def _prepare_ctest_runtime_links(self):
        # Published KF6/Qt6 binary packages embed build-tree-relative DT_NEEDED
        # entries ("../../bin/libKF6XXX.so"); mirror the expected layout with a
        # symlink farm next to the build folder (kmime/knewstuff pattern).
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
            if os.path.exists(src) and not os.path.lexists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._self_sign_elfs()

    def _self_sign_elfs(self):
        # OHOS enforces ELF code signing at load time (freshly built .so in
        # the package folder -> dlopen EACCES until the .codesign section is
        # filled; cf. gulkan/0.15.1). Best effort, never fails the build.
        if str(self.settings.os) != "OHOS":
            return
        tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(tool):
            self.output.info("binary-sign-tool absent; skipping self-sign")
            return
        import subprocess
        pkg = self.package_folder
        # lib/*.so* + the QML plugin under lib/qml/**/ (dlopen'ed at runtime
        # by QQmlEngine, unsigned .so would fail with EACCES)
        targets = (glob.glob(os.path.join(pkg, "lib", "*.so*")) +
                   glob.glob(os.path.join(pkg, "lib", "qml", "**", "*.so*"),
                             recursive=True) +
                   glob.glob(os.path.join(pkg, "bin", "*")))
        signed = 0
        for path in targets:
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                out = path + ".signed"
                r = subprocess.run(
                    [tool, "sign", "-selfSign", "1", "-signAlg",
                     "SHA256withECDSA", "-inFile", path, "-outFile", out],
                    capture_output=True, timeout=60)
                if r.returncode == 0 and os.path.isfile(out):
                    shutil.copymode(path, out)
                    os.replace(out, path)
                    signed += 1
                else:
                    if os.path.isfile(out):
                        os.remove(out)
                    self.output.warn(
                        f"self-sign failed for {path} "
                        f"(rc={r.returncode}): "
                        f"{r.stderr.decode('utf-8', 'replace')[:120]}")
            except Exception as e:  # noqa: BLE001 - best effort by design
                self.output.warn(f"self-sign skipped for {path}: {e}")
        self.output.info(f"self-signed {signed} ELF file(s) in package")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KHealthCertificate"]
        self.cpp_info.includedirs = [
            os.path.join("include", "KHealthCertificate"),
        ]
        # NOTE: bindirs intentionally not declared — upstream does not
        # install() the health-certificate-decode development CLI or the
        # tests/ decoders (no install rules in src/cli/CMakeLists.txt);
        # the package ships libKHealthCertificate.so + the QML plugin only.
