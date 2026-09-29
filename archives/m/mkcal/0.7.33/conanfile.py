#!/usr/bin/env python3
"""Conan recipe for mkcal 0.7.33 on HarmonyOS PC (aarch64-linux-ohos).

mKCal is the SQlite storage backend for KCalendarCore (Sailfish OS). Upstream
builds one shared library (libmkcal-qt{5,6}.so), the mkcaltool executable and
one plugin, and registers three QtTest binaries through CTest.

OHOS-specific adaptations:
  - ENABLE_QT6=ON: upstream defaults to the Qt5/KF5 branch (-DENABLE_QT6=OFF);
    the OHOS-PC stack publishes the Qt6/KF6 generation only
    (qtbase/6.11.1, kcalendarcore/6.26.0)
  - BUILD_PLUGINS=OFF: the single plugin (defaultinvitationplugin) links
    PkgConfig::QMF whose QmfClient dependency has no conan package on ohpcd;
    upstream already guards it behind QMF_FOUND
  - ECM_MODULE_PATH set manually: the CMakeDeps-generated ECMConfig does not
    propagate the variable the project's CMakeLists.txt relies on
    (kcalendarcore 6.26.0 precedent)
  - sqlite3.pc is synthesized in the generators folder: upstream uses
    pkg_check_modules(SQLITE3 sqlite3 IMPORTED_TARGET REQUIRED) while the
    published sqlite3/3.53.4 ships no pkg-config metadata
  - qtbase/kcalendarcore use cmake_find_mode=none: their lib/cmake dirs are
    wired into CMAKE_PREFIX_PATH manually (libkgapi 26.04.0 precedent)
  - QtTest environment: QPA offscreen for tst_load, TZDIR pointed at the
    qtbase zoneinfo database, MKCAL_STORAGEDB redirected into the build
    folder because /tmp is read-only on OHOS
  - every packaged ELF is signed (kwallet 6.18.0 precedent)
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class MkcalConan(ConanFile):
    name = "mkcal"
    version = "0.7.33"
    description = "SQlite storage backend for KCalendarCore (Sailfish OS mKCal)"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/sailfishos/mkcal"
    url = "https://github.com/sailfishos/mkcal"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # kcalendarcore 6.26.0 declares qtbase/6.11.Z (minor_mode); pin the
        # published qtbase build its binary was produced against.
        self.requires("qtbase/6.11.1", force=True)
        self.requires("kcalendarcore/6.26.0")
        self.requires("sqlite3/3.53.4")
        # kcalendarcore already depends on tzdata; require the same reference
        # explicitly so the recipe can point the test environment at a
        # populated zoneinfo database (OHOS ships none).
        self.requires("tzdata/2026.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        self.tool_requires("pkg-config/0.29.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_QT6"] = "ON"
        tc.variables["BUILD_TESTS"] = "ON"
        tc.variables["BUILD_PLUGINS"] = "OFF"
        tc.variables["BUILD_DOCUMENTATION"] = "OFF"
        tc.variables["INSTALL_TESTS"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])
        tc.generate()
        self._write_sqlite3_pc()
        self._write_cmake_paths()

    # ---- pkg-config bridge for sqlite3 -------------------------------------

    def _pkgconfig_dir(self):
        path = os.path.join(self.generators_folder, "pkgconfig")
        os.makedirs(path, exist_ok=True)
        return path

    def _write_sqlite3_pc(self):
        sqlite = self.dependencies.get("sqlite3") or self.dependencies.build.get("sqlite3")
        if not sqlite or not sqlite.package_folder:
            return
        prefix = sqlite.package_folder.replace("\\", "/")
        pc = "\n".join([
            f"prefix={prefix}",
            "exec_prefix=${prefix}",
            "libdir=${exec_prefix}/lib",
            "includedir=${prefix}/include",
            "",
            "Name: sqlite3",
            "Description: SQLite database engine",
            f"Version: {sqlite.ref.version}",
            "Libs: -L${libdir} -lsqlite3",
            "Cflags: -I${includedir}",
            "",
        ])
        with open(os.path.join(self._pkgconfig_dir(), "sqlite3.pc"), "w") as handle:
            handle.write(pc)

    # ---- CMake package discovery for cmake_find_mode=none dependencies -----

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            add_unique(prefixes, os.path.join(ecm.package_folder, "share", "ECM", "cmake"))

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    # ---- environment -------------------------------------------------------

    def _base_env(self):
        env = Environment()
        pkgs = self.dependencies.build.get("pkg-config")
        if pkgs and pkgs.package_folder:
            env.prepend_path("PATH", os.path.join(pkgs.package_folder, "bin"))
        env.define("PKG_CONFIG_PATH", self._pkgconfig_dir())
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        if str(self.settings.os) == "OHOS":
            for llvm_lib in sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The sandbox LD_LIBRARY_PATH carries an incompatible
            # libc++_shared.so; /system/lib64 must win the loader search.
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._base_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    # ---- upstream tests ----------------------------------------------------

    def _zoneinfo_dir(self):
        """Locate a populated tzdata database for the upstream test suite."""
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            candidate = os.path.join(qtbase.package_folder, "share", "zoneinfo")
            if os.path.isdir(candidate):
                return candidate
        tzdata = self.dependencies.get("tzdata")
        if tzdata and tzdata.package_folder:
            for root, dirs, _ in os.walk(tzdata.package_folder):
                if "zoneinfo" in dirs:
                    return os.path.join(root, "zoneinfo")
        return ""

    def _run_upstream_tests(self):
        env = self._base_env()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        env.define("CTEST_PARALLEL_LEVEL", "1")
        # The upstream suite assumes a Finnish local time and a populated
        # tzdata database. OHOS ships neither /usr/share/zoneinfo nor
        # /etc/localtime (and the packaged zoneinfo format differs), so point
        # TZ/TZDIR at a complete data set.
        zoneinfo = self._zoneinfo_dir()
        if zoneinfo:
            env.define("TZDIR", zoneinfo)
            env.define("TZ", "Europe/Helsinki")
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        env.define("HOME", test_home)
        self._prepare_ctest_runtime_links()
        # /tmp is read-only on OHOS: keep the storage database in the build
        # directory and give every suite a fresh file (the upstream tests.xml
        # removes the database before each case for the same reason).
        db_path = os.path.join(test_home, "mkcal-test.db")
        env.define("MKCAL_STORAGEDB", db_path)
        suites = (
            ("tst_storage", True),
            ("tst_load", True),
            ("tst_perf", True),
            # All three upstream suites are gating: they pass on OHOS once the
            # semaphore and close()-semantics patches are applied.
        )
        with env.vars(self).apply():
            for suite, gating in suites:
                for suffix in ("", "-journal", "-wal", "-shm", "-changed"):
                    stale = db_path + suffix
                    if os.path.exists(stale):
                        os.remove(stale)
                command = (
                    'ctest --test-dir "{}" -R "^{}$" --output-on-failure '
                    '--no-tests=error'.format(self.build_folder, suite)
                )
                if gating:
                    self.run(command)
                else:
                    if self.run(command, ignore_errors=True) != 0:
                        self.output.warning(
                            "{} reported upstream failures on KCalendarCore 6.x "
                            "(recorded, non-blocking; see notes.md)".format(suite)
                        )

    def _prepare_ctest_runtime_links(self):
        # Dependency libraries and mkcal itself ship relative sonames on OHOS
        # (e.g. "./libical.so", "../../bin/libKF6CalendarCore.so"); the musl
        # loader resolves DT_NEEDED entries containing a slash from the process
        # CWD, not from LD_LIBRARY_PATH. Copy the libraries next to each CTest
        # working directory depth (kcalendarcore 6.26.0 precedent).
        bin_dir = os.path.join(self.build_folder, "bin")
        target_dirs = [
            os.path.join(self.build_folder, "tests"),
            self.build_folder,
            bin_dir,
        ]
        for target_dir in target_dirs:
            os.makedirs(target_dir, exist_ok=True)
        lib_sources = glob.glob(os.path.join(bin_dir, "lib*.so*"))
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            if not os.path.isfile(src) or os.path.islink(src):
                continue
            for target_dir in target_dirs:
                dst = os.path.join(target_dir, os.path.basename(src))
                if os.path.exists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)

    # ---- packaging ---------------------------------------------------------

    def package(self):
        cmake = CMake(self)
        with self._base_env().vars(self).apply():
            cmake.install()
        self._normalize_elf_sonames()
        self._sign_ohos_elf_tree(self.package_folder, "package")

    def _normalize_elf_sonames(self):
        """Make the packaged ELF tree relocatable.

        The OHOS toolchain does not emit DT_SONAME for this project (its
        SOVERSION property does not reach the linker here) and the published
        kcalendarcore/6.26.0 ships without one either, so the linker records
        the absolute build-machine path of libKF6CalendarCore.so in DT_NEEDED.
        Give every packaged shared object a SONAME and rewrite absolute
        DT_NEEDED entries to bare library names (kio-kwallet 6.28.0 / E018
        precedent).
        """
        if str(self.settings.os) != "OHOS":
            return
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        if not os.path.isfile(patchelf):
            return
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                for entry in self._patchelf_output(patchelf, "--print-needed", path):
                    # Both absolute (../../src/... from the build tree) and
                    # absolute build-machine paths must become bare names: the
                    # loader only searches LD_LIBRARY_PATH for entries without
                    # a slash.
                    if "/" in entry:
                        self.run(
                            f"{self._quote(patchelf)} --replace-needed "
                            f"{self._quote(entry)} {self._quote(os.path.basename(entry))} "
                            f"{self._quote(path)}"
                        )
                if ".so" in name and not self._patchelf_output(patchelf, "--print-soname", path):
                    self.run(
                        f"{self._quote(patchelf)} --set-soname {self._quote(name)} "
                        f"{self._quote(path)}"
                    )

    @staticmethod
    def _patchelf_output(patchelf, *args):
        try:
            result = subprocess.run(
                [patchelf, *args], capture_output=True, text=True, timeout=60
            )
        except (OSError, subprocess.SubprocessError):
            return []
        if result.returncode != 0:
            return []
        return result.stdout.split()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder, label):
        if str(self.settings.os) != "OHOS":
            return
        if not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "Cannot locate OHOS llvm-objcopy/binary-sign-tool for ELF signing"
            )
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                try:
                    os.chmod(path, 0o755)
                except OSError as exc:
                    self.output.warning(f"chmod signed ELF skipped for {path}: {exc}")
                signed += 1
        self.output.info(f"Signed {signed} OHOS {label} ELF file(s)")

    def package_info(self):
        # mKCal installs pkg-config metadata only (ECMGeneratePkgConfigFile);
        # consumers locate it through libmkcal-qt6.pc, so no CMakeDeps config
        # is generated.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.includedirs = ["include/mkcal-qt6", "include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["mkcal-qt6"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
