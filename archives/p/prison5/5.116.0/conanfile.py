#!/usr/bin/env python3
"""Conan recipe for prison5 5.116.0 (KDE Frameworks 5 / Qt5) on HarmonyOS PC.

prison is the KDE Frameworks barcode abstraction library (tier 1).  From
the 5.116.0 tarball this recipe builds:

  * KF5Prison         - core library (Prison::createBarcode factory and the
                        QRCode / Code39 / Code93 / Code128 / Aztec
                        generators, backed by qrencode for the QR codes)
  * prison-datamatrix - small CLI demo tool (installed into bin/; prints a
                        DataMatrix barcode image, which requires Dmtx and
                        therefore degenerates to an error exit here, the
                        tool is shipped unchanged for upstream parity)

OHOS-specific adaptations (KF5 chain conventions validated on the
kpeople5/ki18n5/kwidgetsaddons5 skeletons plus the prison/6.18.0
same-software KF6 precedent):

  - QT_MAJOR_VERSION=5 so the project selects Qt5.
  - Qt5 supply: qt5-qtbase/5.15.2.2 consumed through its native
    lib/cmake/Qt5* configs (cmake_find_mode=none + CMAKE_PREFIX_PATH
    wiring).  .2 is the DBus-capable superset binary of the 5.15.2 line
    the KF5 chain normalises onto; force=True keeps the dependency graph
    consistent with the published KF5 recipes that still pin
    qt5-qtbase/5.15.2.
  - qrencode/4.1.1 is the REQUIRED QR barcode backend.  Upstream consumes
    it through a manual FindQRencode.cmake (module mode), so
    QRencode_INCLUDE_DIRS / QRencode_LIBRARIES are handed to the toolchain
    directly (prison/6.18.0 precedent - the find_library call is
    short-circuited by the pre-set cache variables) and the qrencode
    package prefix is additionally put on CMAKE_PREFIX_PATH /
    CMAKE_LIBRARY_PATH as the fallback search root.
  - libdmtx / ZXing are optional upstream backends (DataMatrix / PDF417 /
    EAN13 generation plus the video scanner); they are cut off with
    CMAKE_DISABLE_FIND_PACKAGE_Dmtx=ON / CMAKE_DISABLE_FIND_PACKAGE_ZXing=ON.
    The task card mandates the qrencode line only (upstream default when
    neither optional dependency is present), and the cut also naturally
    disables the scanner/ (Qt5Multimedia-gated) and quick/ (Qt5Quick-
    gated) sub-directories.
  - ECM_MODULE_PATH / ECM_DIR set manually because ecm is a
    tool_requires (build context) and CMakeDeps does not wire its
    share/ECM tree into the host prefix paths.
  - CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE point at the qt5-qtbase
    bin tools (the upstream autotests are Q_OBJECT classes carrying .qrc
    reference images).
  - Qt5CoreConfigExtrasMkspecDir.cmake (shipped inside the packaged
    qt5-qtbase) hard-codes a build-tree path <prefix>/../b/mkspecs/
    linux-clang which the packaged cache entry never has; generate()
    recreates the whole mkspecs tree there from the package's own
    mkspecs/ (kpeople5 precedent).
  - CMAKE_SYSTEM_NAME=Linux, set BOTH as a toolchain variable and as a
    cache variable ("double override"): the OHOS Conan toolchain maps
    os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, for which CMake defines
    neither UNIX nor a platform module.  ECM's KDEInstallDirs /
    KDEFrameworkCompilerSettings need the POSIX branch, so the Linux
    platform is forced (chain-wide convention; pan/0.165 and kpeople5
    precedents).
  - KF_SKIP_PO_PROCESSING=ON: Qt5LinguistTools is not published to ohpcd,
    so any poqm/ -> .qm processing is skipped (chain-wide convention).
  - KF_IGNORE_PLATFORM_CHECK=TRUE so ECM accepts the OHOS host triplet.
  - BUILD_TESTING=ON: the upstream QTEST targets are really executed
    from build() through ctest.  All six upstream autotests are
    QTEST_APPLESS_MAIN binaries (no GUI event loop needed, headless-
    friendly); with Dmtx/ZXing cut off, four targets are registered and
    run: prison-aztecbarcodetest (53 QTest executions),
    prison-code128barcodetest (22), prison-qrtest (5) and
    prison-reedsolomontest (4) - 84 QTest executions in total, all
    passing (verified by re-running the built binaries directly and
    reading their Totals lines).  The two optional-backend tests
    (prison-datamatrixtest, prison-zxingutiltest) are compiled out by
    upstream's own "if(TARGET Dmtx::Dmtx)" / "if(TARGET ZXing::ZXing)"
    guards, not skipped by this recipe.
  - CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE +
    CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname," ->
    relocatable, unversioned DT_SONAME (W3 CI L5 soname gate).
  - CMAKE_BUILD_WITH_INSTALL_RPATH=ON (E537): OHOS refuses to mmap
    PROT_EXEC a shared library whose ELF was rewritten after linking.
  - CMAKE_BUILD_PARALLEL_LEVEL=1: the HMDFS cache filesystem refuses the
    make jobserver fifo (EPERM).
  - /system/lib64 is prepended to LD_LIBRARY_PATH while running the Qt
    host tools and the upstream tests so the loader resolves the
    compatible libc++ first (kcoreaddons5 / kpeople5 precedent).
  - ELF signing: after cmake.install() the packaged lib/libKF5Prison.so
    and bin/prison-datamatrix are re-signed with binary-sign-tool
    (llvm-objcopy removes any old .codesign section first), following
    the p11-kit/0.26.2 in-recipe pattern.
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


class Prison5Conan(ConanFile):
    name = "prison5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - barcode abstraction library providing uniform access to generation of barcodes"
    license = "MIT"
    homepage = "https://invent.kde.org/frameworks/prison"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # .2 is the DBus-capable superset of the 5.15.2 line; force=True
        # normalises the graph (published KF5 recipes still pin
        # qt5-qtbase/5.15.2 - kpeople5 precedent).
        self.requires("qt5-qtbase/5.15.2.2", force=True)
        self.requires("qrencode/4.1.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "%s only supports Linux and OHOS, got %s"
                % (self.name, self.settings.os)
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase is consumed through its native lib/cmake/Qt5* configs
        # and qrencode through the upstream FindQRencode.cmake module;
        # neither needs (nor benefits from) CMakeDeps-generated lowercase
        # configs, so suppress them to keep the search path clean.
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        deps.set_property("qrencode", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Optional upstream backends (task card: qrencode line only).
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Dmtx"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_ZXing"] = "ON"
        # Double override of the OHOS->HarmonyOS toolchain mapping: both
        # the toolchain variable and the cache entry carry Linux so the
        # ECM POSIX branch is taken no matter which one wins.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        qtbase = self.dependencies["qt5-qtbase"]
        qrencode = self.dependencies["qrencode"]

        self._prepare_qt_mkspec_compat(qtbase.package_folder)

        qbin = os.path.join(qtbase.package_folder, "bin")
        for tool, cmake_var in (
            ("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
            ("rcc", "CMAKE_AUTORCC_EXECUTABLE"),
            ("uic", "CMAKE_AUTOUIC_EXECUTABLE"),
        ):
            tool_path = os.path.join(qbin, tool)
            if not os.path.isfile(tool_path):
                raise ConanInvalidConfiguration(
                    "qt5-qtbase/5.15.2.2 does not provide the required "
                    "bin/%s tool" % tool
                )
            tc.variables[cmake_var] = tool_path

        # FindQRencode.cmake is module mode; hand it the qrencode package
        # directly (pre-set cache variables short-circuit find_library /
        # find_path) - prison/6.18.0 precedent.
        qr_lib = os.path.join(qrencode.package_folder, "lib", "libqrencode.so")
        if not os.path.isfile(qr_lib):
            qr_lib = os.path.join(qrencode.package_folder, "lib", "libqrencode.a")
        tc.variables["QRencode_INCLUDE_DIRS"] = os.path.join(
            qrencode.package_folder, "include"
        )
        tc.variables["QRencode_LIBRARIES"] = qr_lib

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_DIR"] = os.path.join(ecm_share, "cmake")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        tc.generate()

        # Wire the search paths CMakeDeps cannot provide: the native Qt5
        # configs of qt5-qtbase, the qrencode fallback roots and the ECM
        # cmake trees (appended to the CMakeDeps-generated file - kpeople5
        # precedent).
        lines = []
        for pkg in (qtbase, qrencode):
            if pkg and pkg.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s")' % pkg.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % pkg.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % pkg.package_folder
                )
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake)
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # Qt5CoreConfigExtrasMkspecDir.cmake inside the packaged qt5-qtbase
        # resolves the mkspecs dir against <prefix>/../b/mkspecs/<spec>;
        # recreate that tree from the package's own mkspecs/ so the
        # include path exists (kpeople5 precedent).
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
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _cmake_build_env(self):
        # Host tools executed during configure/build (moc/rcc, and qmake
        # for ECM's ecm_query_qmake / ecm_generate_pri_file) must load a
        # compatible libc++_shared.so: the sandbox LD_LIBRARY_PATH can
        # contain an incompatible one under
        # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
        # system copy (kwidgetsaddons5 / kpeople5 precedent).  The OHOS
        # SDK llvm lib dir is also prepended so lld can resolve libxml2
        # (E132).
        build_env = self._library_runtime_env()
        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase and qtbase.package_folder:
            build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        if str(self.settings.os) == "OHOS":
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib*"
                )
            ):
                if os.path.isdir(llvm_lib):
                    build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return build_env

    def _run_upstream_tests(self):
        # The upstream QTEST targets are registered by ECM's ecm_add_test;
        # every one of them is a QTEST_APPLESS_MAIN binary (no GUI event
        # loop, no D-Bus, no QStandardPaths data - the .qrc-embedded
        # reference images make them fully self-contained), so the whole
        # suite really runs on OHOS.  With Dmtx/ZXing disabled, four
        # targets are registered: prison-aztecbarcodetest,
        # prison-code128barcodetest, prison-qrtest and
        # prison-reedsolomontest; the datamatrix/zxingutil tests are
        # compiled out by upstream's own TARGET guards.
        if not can_run(self):
            return
        test_env = self._library_runtime_env()
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
        if str(self.settings.os) == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error'.format(self.build_folder)
            )

    def _prepare_ctest_runtime_links(self):
        # ctest launches the test executables from <build>/bin; their
        # libKF5Prison/Qt5/qrencode runtime deps live in the build tree /
        # conan package folders.  Symlink them next to the test binaries
        # so the loader can resolve (kcoreaddons5 / kpeople5 precedent).
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
        self._sign_elfs()

    def _sign_elfs(self):
        # Re-sign the shipped ELF files for HarmonyOS code verification
        # (binary-sign-tool self-sign; llvm-objcopy strips any pre-existing
        # .codesign section first) - p11-kit/0.26.2 in-recipe pattern.
        if str(self.settings.os) != "OHOS":
            return
        hnp_bin = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp_bin, "llvm-objcopy")
        signer = os.path.join(hnp_bin, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool/llvm-objcopy unavailable; skipping ELF re-signing"
            )
            return

        patterns = ("bin/*", "lib/*.so", "lib/*.so.*")
        files = []
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(self.package_folder, pattern)))
        for path in sorted(set(files)):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as handle:
                    if handle.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            self.run(
                '{objcopy} --remove-section .codesign "{path}" 2>/dev/null '
                "|| true".format(objcopy=objcopy, path=path)
            )
            self.run(
                '{signer} sign -inFile "{path}" -outFile "{path}.signed" '
                "-selfSign 1".format(signer=signer, path=path)
            )
            if os.path.isfile(path + ".signed"):
                shutil.move(path + ".signed", path)

    def package_info(self):
        # The project installs its own KF5PrisonConfig.cmake
        # (find_dependency on Qt5Gui) with the KF5::Prison exported target;
        # use cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Prison"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
