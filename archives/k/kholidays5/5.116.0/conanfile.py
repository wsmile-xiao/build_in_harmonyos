#!/usr/bin/env python3
"""Conan recipe for kholidays5 5.116.0 (KDE Frameworks 5 / Qt5) on HarmonyOS PC.

kholidays is the KDE Frameworks holiday calculation library: libKF5Holidays.so
computes holiday calendars (the bundled plan2 region data + parser) and
astronomical events - sunrise/sunset (SunRiseSet), lunar phases (LunarPhase),
zodiac signs (Zodiac) and astro seasons (AstroSeasons).  The
org.kde.kholidays QML declarative plugin (HolidayRegionsModel, Lunar /
SunRiseSet gadget singletons) ships in <lib>/qml/org/kde/kholidays.

The KF5-line final release (5.116.0) tarball is published on download.kde.org
under frameworks/5.116 (redirects to the Attic archive tree now that the 5
line is EOL; conan get() follows it fine).  The package name kholidays5 keeps
the platform task #14898 registration distinct from the KF6-line
kholidays/6.28.0 recipe (different Qt line, different library soname).

OHOS-specific adaptations (KF5 5.116.0 chain conventions: kpeople5/5.116.0
PR #14576, kcalcore/5.116.0, kcoreaddons5/5.116.0):

  - qt5-qtbase/5.15.2.2 forced (force=True): the KF5-chain Qt supply
    (kpeople5 precedent); .2 is the DBus-capable superset binary and is
    ABI-compatible on the 5.15.2 line, so the whole chain shares one Qt.
  - Qt5 supply split across two packages (kpeople5 precedent, reduced to the
    two components the top-level find_package(Qt5 5.15.2 CONFIG REQUIRED
    Core Qml) needs):
      qt5-qtbase/5.15.2.2       Core/Gui/Network/Test (native per-module
                                configs, cmake_find_mode=none)
      qt5-qtdeclarative/5.15.2  Qt5Qml (CMakeDeps, cmake_file_name Qt5Qml;
                                the package ships libraries only, no
                                per-module cmake configs)
    A hand-written aggregated Qt5Config.cmake shim is placed in the
    generators folder (first on CMAKE_PREFIX_PATH, exact-name match beats
    any lowercase qt5-config.cmake aggregate CMakeDeps would emit); it
    find_dependency()'s the native per-module configs from qt5-qtbase and
    the CMakeDeps-generated Qt5QmlConfig.  The autotests'
    find_package(Qt5Test CONFIG REQUIRED) resolves directly against the
    native Qt5Test config on CMAKE_PREFIX_PATH.
  - ECM 6.26.0 satisfies find_package(ECM 5.116.0 NO_MODULE) (6.26.0 >=
    5.116.0 - kcoreaddons5/5.116.0 was built with ecm/6.20.0 the same way);
    ECM_DIR/ECM_MODULE_PATH are set manually because ecm is a tool_requires
    and nothing wires its share/ECM tree into the CMake search paths.
    ECMQmlModule's Qt5 implementation (ECMQmlModule5.cmake) serves the
    org.kde.kholidays declarative plugin (no qmlplugindump run: the plugin
    is only created through ecm_add_qml_module/ecm_finalize_qml_module).
  - QT_MAJOR_VERSION=5 so the project's find_package(Qt${QT_MAJOR_VERSION})
    selects the Qt5 supply (ECM 6.x would otherwise default to 6).
  - CMAKE_SYSTEM_NAME=Linux (+ CMAKE_SYSTEM_PROCESSOR matching the host
    arch) forced through the toolchain cache variables, in the main recipe
    AND in test_package (chain-wide convention): the OHOS conan toolchain
    maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, for which the CMake >= 4
    workers ship no Platform/ module and compiler detection breaks.  OHOS
    is POSIX, so forcing the Linux platform keeps everything intact, and
    because it matches the host system the build stays native-like: UNIX
    is set, ECMAddTests registers the upstream tests, and the ctest suite
    really runs on the OHOS runner.
  - KF_SKIP_PO_PROCESSING=ON: Qt5LinguistTools is not published to ohpcd,
    so the poqm/ -> .qm processing is skipped; the qm loader source the
    library links (ecm_create_qm_loader) is unconditionally generated and
    only embeds the catalogs, so skipping po processing keeps the library
    API intact with an empty catalog set (chain-wide convention).
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS is not in the KDE platform list).
  - CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE point at the qt5-qtbase bin
    tools; AUTORCC embeds the 153-file holidays.qrc region-data resource
    into libKF5Holidays.so.
  - Qt5CoreConfigExtrasMkspecDir.cmake (shipped inside the packaged
    qt5-qtbase) hard-codes a build-tree path <prefix>/../b/mkspecs/... which
    the packaged cache entry never has; generate() recreates the whole
    mkspecs tree there from the package's own mkspecs/ (kcoreaddons5
    precedent).  ECMGeneratePriFile's ecm_query_qt runs the qtbase qmake
    from PATH (qtbase/bin prepended in the build env).
  - CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE +
    CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname," -> relocatable,
    unversioned DT_SONAME (W3 CI L5 soname gate).
  - CMAKE_BUILD_WITH_INSTALL_RPATH=ON (E537): OHOS refuses to mmap PROT_EXEC
    a shared library whose ELF was rewritten after linking.
  - CMAKE_BUILD_PARALLEL_LEVEL=1: the HMDFS cache filesystem refuses the
    make jobserver fifo (EPERM).
  - /system/lib64 is prepended to LD_LIBRARY_PATH while running the Qt host
    tools and the upstream tests so the loader resolves the compatible
    libc++ first (kcoreaddons5 / kpeople5 precedent).
  - package() signs every packaged ELF (libKF5Holidays.so and the QML
    plugin) with the OHOS binary-sign-tool self-signing (kcalcore /
    libical precedent).
  - BUILD_TESTING=ON: the five upstream autotests (testlunar, testseasons,
    testsunriseset, testzodiac, testholidayregion) are registered by ECM's
    ecm_mark_as_test and really executed from build() through ctest.  They
    are pure computation tests over the bundled region data and astronomy
    code (QTEST_MAIN binaries on Qt5::Test; testzodiac is a plain main()
    smoke run) and need no display and no session services.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class KHolidays5Conan(ConanFile):
    name = "kholidays5"
    version = "5.116.0"
    description = (
        "KDE Frameworks 5 - holiday calendars and astronomical events "
        "(sunrise/sunset, lunar phases, zodiac, astro seasons) - "
        "libKF5Holidays.so + the org.kde.kholidays QML plugin"
    )
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kholidays"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KF5-chain Qt supply (kpeople5/5.116.0 precedent): 5.15.2.2 is the
        # DBus-capable superset binary, ABI-compatible on the 5.15.2 line;
        # force=True normalises the whole graph onto it (kholidays5 has no
        # KF5 library dependency, but keeping the chain on one Qt avoids
        # mixed-graph refusals for consumers like kcalcore5/eventviews).
        self.requires("qt5-qtbase/5.15.2.2", force=True)
        # Qt5Qml supply (top-level REQUIRED component): the declarative
        # org.kde.kholidays QML plugin links Qt5::Qml.
        self.requires("qt5-qtdeclarative/5.15.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        from conan.tools.files import get

        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase is consumed through its native Qt5 per-module configs
        # (cmake_find_mode=none suppresses the CMakeDeps forwarding configs);
        # qt5-qtdeclarative ships libraries only, so CMakeDeps generates the
        # Qt5Qml config for it (cmake_file_name=Qt5Qml, kpeople5 precedent).
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        deps.set_property("qt5-qtdeclarative", "cmake_file_name", "Qt5Qml")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # W3 CI L5 soname gate + E537 install-RPATH + HMDFS jobserver
        # (kpeople5/5.116.0 precedent).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"

        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Chain-wide convention (kpeople5/kcalcore, main recipe AND
            # test_package): the OHOS conan toolchain maps os=OHOS to
            # CMAKE_SYSTEM_NAME=HarmonyOS, for which the CMake >= 4 workers
            # ship no Platform/ module and compiler detection breaks.  OHOS
            # is POSIX, so the Linux platform is forced; the matching
            # CMAKE_SYSTEM_PROCESSOR keeps the build native-like (UNIX set,
            # ECM test registration on, the ctest suite really runs).
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            if str(self.settings.arch) == "armv8":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            elif str(self.settings.arch) == "x86_64":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "x86_64"

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

        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase and qtbase.package_folder:
            # AUTOMOC/AUTORCC host tools: the Q_OBJECT classes in src/ and
            # src/declarative/ need moc, and the 153-file holidays.qrc is
            # embedded through rcc; ECMGeneratePriFile runs qmake through
            # ecm_query_qt.
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
                        "bin/{} tool".format(tool)
                    )
                tc.variables[cmake_var] = tool_path
            # The packaged Qt5CoreConfigExtrasMkspecDir.cmake hard-codes a
            # build-tree path <prefix>/../b/mkspecs/... which the packaged
            # cache entry never has; recreate the mkspecs tree there
            # (kcoreaddons5/kpeople5 precedent).
            self._prepare_qt_mkspec_compat(qtbase.package_folder)

        tc.generate()

        # ------------------------------------------------------------------
        # Aggregated Qt5Config.cmake shim (kpeople5/5.116.0 precedent,
        # reduced to this graph's components): the top-level
        # find_package(Qt5 5.15.2 CONFIG REQUIRED Core Qml) needs one
        # aggregate serving components from two conan packages.  The shim
        # is written into the generators folder (first on
        # CMAKE_PREFIX_PATH, exact-name match beats the lowercase
        # qt5-config.cmake aggregate CMakeDeps emits for qt5-qtdeclarative's
        # transitive qt5-qtbase requires).
        # ------------------------------------------------------------------
        qt_prefix = (
            qtbase.package_folder
            if qtbase and qtbase.package_folder
            else ""
        )
        if qt_prefix:
            shim = [
                "# Aggregated Qt5Config for kholidays5 (two-package supply).",
                "# Generated by conanfile.py generate().",
                "include(CMakeFindDependencyMacro)",
                # Guard against mutual re-entry: the CMakeDeps-generated
                # Qt5QmlConfig (qt5-qtdeclarative) find_dependency's Qt5;
                # marking the aggregate found FIRST stops that callback from
                # re-including this shim mid-execution.
                "set(Qt5_FOUND TRUE)",
                'find_dependency(Qt5Core 5.15.2 PATHS "%s/lib/cmake/Qt5Core" NO_DEFAULT_PATH)'
                % qt_prefix,
            ]
            # Network/Gui are referenced by the CMakeDeps-generated Qt5Qml
            # target interface (qt5-qtdeclarative cpp_info.requires), so
            # they must be preloaded before Qt5QmlConfig is included; Test
            # serves the autotests' find_package(Qt5Test CONFIG REQUIRED).
            for comp in ("Network", "Gui", "Test"):
                shim.append(
                    'find_dependency(Qt5%s 5.15.2 PATHS "%s/lib/cmake/Qt5%s" NO_DEFAULT_PATH)'
                    % (comp, qt_prefix, comp)
                )
            shim += [
                "find_dependency(Qt5Qml)",
                "set(Qt5_Core_FOUND TRUE)",
                "set(Qt5_Network_FOUND TRUE)",
                "set(Qt5_Gui_FOUND TRUE)",
                "set(Qt5_Test_FOUND TRUE)",
                "set(Qt5_Qml_FOUND TRUE)",
                'set(Qt5_VERSION_STRING "5.15.2.2")',
            ]
            with open(
                os.path.join(self.generators_folder, "Qt5Config.cmake"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write("\n".join(shim) + "\n")
            with open(
                os.path.join(self.generators_folder, "Qt5ConfigVersion.cmake"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(
                    "set(PACKAGE_VERSION 5.15.2.2)\n"
                    "if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)\n"
                    "  set(PACKAGE_VERSION_COMPATIBLE FALSE)\n"
                    "else()\n"
                    "  set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
                    "  if(PACKAGE_FIND_VERSION STREQUAL PACKAGE_VERSION)\n"
                    "    set(PACKAGE_VERSION_EXACT TRUE)\n"
                    "  endif()\n"
                    "endif()\n"
                )

        # ------------------------------------------------------------------
        # CMake search-path wiring (conan_cmakedeps_paths.cmake, included by
        # the conan toolchain): qt5-qtbase is consumed through its native
        # Qt5 configs so its package root must be wired onto the CMake
        # search paths manually (kcoreaddons5 / kcalcore precedent).
        # ------------------------------------------------------------------
        qtdecl = self.dependencies.get("qt5-qtdeclarative")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for pkg in (qtdecl, qtbase):
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
        if qtbase and qtbase.package_folder:
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % qtbase.package_folder
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
        # Host tools executed during configure/build (moc/rcc for AUTOMOC/
        # AUTORCC, and qmake for ECM's ecm_query_qt / ecm_generate_pri_file)
        # must load a compatible libc++_shared.so: the sandbox
        # LD_LIBRARY_PATH can contain an incompatible one under
        # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
        # system copy (kwidgetsaddons5 / kpeople5 precedent).  The OHOS SDK
        # llvm lib dir is also prepended so lld can resolve libxml2 (E132).
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
        # The five upstream autotests are registered by ECM's
        # ecm_mark_as_test; they are QTEST_MAIN binaries (testzodiac a
        # plain main() smoke run) driving the real KHolidays API over the
        # bundled region data (holidays.qrc is embedded in the library) and
        # the astronomy code, with the three KDESRCDIR-relative fixture
        # directories (holiday_calendar_systems, holiday_gb-eaw_en-gb_Test,
        # holiday_solstice_in_holidays) resolved from the source tree at
        # compile time.  No display, no session services, no plugin
        # scanning.
        if not can_run(self):
            return
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("TZ", "UTC")
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
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 300'.format(self.build_folder)
            )

    def _prepare_ctest_runtime_links(self):
        # ctest launches the test executables from <build>/bin; their
        # libKF5Holidays/Qt5 runtime deps live in the build tree / conan
        # package folders.  The KDE install rpath is stripped on OHOS, so
        # the library resolves through the relative soname from the CTest
        # CWD: symlink everything next to <build>/../bin (kconfig /
        # kcalcore / kpeople5 precedent).
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
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        # The project installs its own KF5HolidaysConfig.cmake
        # (find_dependency on Qt5Core) with the KF5::Holidays exported
        # target; use cmake_find_mode=none so CMakeDeps doesn't shadow it
        # (kcoreaddons5 / kpeople5 / kcalcore precedent).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Holidays"]
        self.cpp_info.resdirs = ["share"]
        # KF5Holidays depends on Qt5Core; the installed
        # KF5HolidaysConfig.cmake drives the Qt5 find_dependency itself
        # (consumer-side Qt5 supply wiring, kcalcore precedent).
        self.cpp_info.requires = []
        # The org.kde.kholidays QML plugin (lib/qml/org/kde/kholidays) is
        # part of the deliverable: expose it on the consumer runtime env so
        # any Qt5 process can import org.kde.kholidays.
        self.runenv_info.append_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )

    # ------------------------------------------------------------------
    # OHOS ELF signing (kcalcore / libical precedent): every packaged ELF
    # (libKF5Holidays.so and the org.kde.kholidays QML plugin) gets a
    # .codesign section through binary-sign-tool self-signing after the
    # install step.
    # ------------------------------------------------------------------
    def _sign_ohos_elf_tree(self, root_folder):
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS llvm-objcopy and binary-sign-tool are required for ELF signing"
            )
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign "
                    f"{self._quote(path)} 2>/dev/null || true"
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )

    @staticmethod
    def _is_elf(path):
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"

    @staticmethod
    def _quote(value):
        return '"' + value.replace('"', '\\"') + '"'
