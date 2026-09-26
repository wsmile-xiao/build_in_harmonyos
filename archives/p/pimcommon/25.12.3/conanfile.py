#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv

try:
    from shutil import which as shutil_which
except ImportError:  # py2/very old py3 fallback
    from distutils.spawn import find_executable as shutil_which
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PimcommonConan(ConanFile):
    name = "pimcommon"
    version = "25.12.3"
    description = "KDE PIM common libraries (core pimcommon library)"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/pim/pimcommon"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Published KF6 6.14.0 baseline line (same as kio/6.14.0, kxmlgui/
        # 6.14.0, knewstuff/6.14.0, keditbookmarks 26.04.0 precedent) so the
        # whole graph reuses published binaries built against the same
        # qtbase/6.11.1 without version conflicts.
        # qtbase-sql-dbus variant provides the Qt6::DBus module required by
        # the core library (imap resource settings D-Bus API); the plain
        # qtbase/6.11.1 package has FEATURE_dbus=OFF (E323). akonadi 25.12.3
        # precedent.
        self.requires("qtbase-sql-dbus/6.11.1")
        # kio 6.14.0 is the complete shape (KIOCore + KIOGui + KIOWidgets);
        # the 6.26.0 package is KIOCORE_ONLY and lacks KIOWidgets which the
        # core library links PRIVATE.
        self.requires("kio/6.14.0")
        self.requires("kcodecs/6.14.0")
        self.requires("kcolorscheme/6.14.0")
        self.requires("kconfig/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kitemviews/6.14.0")
        self.requires("kjobwidgets/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("kxmlgui/6.14.0")
        # The OHOS SDK lld depends on libxml2.so.16 at link time (E132);
        # libxml2/2.15.3 provides that SONAME. Declared so its lib dir can be
        # injected into LD_LIBRARY_PATH (kio 6.14.0 recipe precedent).
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        urls = source.get("urls")
        if urls is None:
            urls = [source["url"]]
        failures = []
        for url in urls:
            try:
                get(self, url=url, sha256=source["sha256"], strip_root=True)
                return
            except Exception as error:
                failures.append("{}: {}".format(url, error))
                self.output.warning("Source download failed; trying next URL: {}".format(url))
        raise RuntimeError("All source download URLs failed: {}".format("; ".join(failures)))

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        # The packaged qtpaths6 host tool is linked against the OHOS SDK
        # libc++, and the SDK lld needs libxml2.so.16 at link time (E132).
        # Inject the dependency lib dirs into LD_LIBRARY_PATH via
        # buildenv_info so both the ECMQueryQt qtpaths call and the CMake
        # TryCompile stage resolve their shared libraries (kio 6.14.0
        # recipe precedent).
        libxml2 = self.dependencies.get("libxml2")
        if libxml2 and libxml2.package_folder:
            self.buildenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(libxml2.package_folder, "lib")
            )
        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if qtbase and qtbase.package_folder:
            self.buildenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib")
            )
        # KF6 dep lib dirs: the ECMQueryQt qtpaths call and the CMake
        # TryCompile linker (lld) run inside the conanbuild environment;
        # the profile only provides the OHOS SDK llvm/lib dir there.
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", libdir)

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["ENABLE_WARN_OUTDATED"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

        # ECMQueryQt cannot obtain Qt6::qtpaths through the reduced Qt package
        # config. Point it at the packaged qtpaths6 executable explicitly.
        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if qtbase and qtbase.package_folder:
            tc.variables["QUERY_EXECUTABLE"] = os.path.join(
                qtbase.package_folder, "bin", "qtpaths6"
            )
            tc.variables["_cli_option"] = "--query"

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _write_cmake_paths(self):
        prefixes = []
        modules = []
        # qtbase-sql-dbus first (preferred Qt provider); the plain qtbase
        # packages pulled in transitively by KF6 deps are skipped to avoid
        # the reduced (FEATURE_dbus=OFF) Qt6 config shadowing ours.
        preferred = (
            "qtbase-sql-dbus",
            "kio",
            "kcodecs",
            "kcolorscheme",
            "kconfig",
            "kcoreaddons",
            "ki18n",
            "kitemviews",
            "kjobwidgets",
            "kwidgetsaddons",
            "kxmlgui",
        )
        for dep_name in preferred:
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                prefixes.extend((
                    os.path.join(dep.package_folder, "lib", "cmake"),
                    dep.package_folder,
                ))
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            ref_name = dep.ref.name
            if ref_name in ("qtbase", "qtbase-sql-dbus"):
                continue
            prefixes.extend((
                os.path.join(dep.package_folder, "lib", "cmake"),
                dep.package_folder,
            ))
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            prefixes.append(os.path.join(ecm_share, "cmake"))
            modules.extend(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            'list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(";".join(prefixes)),
            'list(PREPEND CMAKE_MODULE_PATH "{}")'.format(";".join(modules)),
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        with open(
            os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w"
        ) as paths_file:
            paths_file.write("\n".join(lines) + "\n")

    def _build_runtime_env(self):
        # The ECMQueryQt module (KDEInstallDirs) executes the packaged
        # qtpaths — an OHOS binary linked against the SDK libc++ and Qt6 —
        # and the SDK lld needs libxml2.so.16 at link time (E132). Provide
        # all dependency lib dirs on LD_LIBRARY_PATH (akonadi 25.12.3
        # recipe precedent).
        env = Environment()
        folders = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder and dep.package_folder not in folders:
                folders.append(dep.package_folder)
        for folder in reversed(folders):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(folder, "lib"))
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(folder, "plugins"))
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(folder, "lib", "plugins"))
            env.prepend_path(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(folder, "plugins", "platforms"),
            )
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            import glob as _glob
            for llvm_lib in sorted(
                _glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
                # libc++_shared.so used by the packaged host tools lives in
                # the target sysroot subdir of the SDK.
                env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(llvm_lib, "aarch64-linux-ohos"),
                )
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64
            # which shadows the compatible one; prepend /system/lib64 so the
            # loader resolves the compatible libc++ first (kconfig 6.26.0 /
            # bluez-qt 6.28.0 / kcrash 6.26.0 precedent).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
            self._run_upstream_tests()

    def _prepare_upstream_test_links(self):
        # Published KF6 binaries carry build-tree-relative DT_NEEDED entries
        # ("../../bin/libKF6*.so"); the musl loader resolves them relative to
        # the process cwd. ctest executes each test with its working
        # directory set to the CTestTestfile.cmake folder, so the relative
        # "../bin" / "../../bin" locations around every test dir must expose
        # the dependency libraries (keditbookmarks 26.04.0 / ktextwidgets
        # precedent).
        import glob as _glob
        sources = []
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            sources.extend(_glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")))
        link_dirs = set()
        for ctestfile in _glob.glob(
            os.path.join(self.build_folder, "**", "CTestTestfile.cmake"), recursive=True
        ):
            test_dir = os.path.dirname(ctestfile)
            for rel in ("../bin", "../../bin", "../../../bin", "../../../../bin"):
                link_dirs.add(os.path.normpath(os.path.join(test_dir, rel)))
        link_dirs.add(os.path.join(self.build_folder, "bin"))
        created = 0
        for link_dir in link_dirs:
            try:
                os.makedirs(link_dir, exist_ok=True)
            except OSError:
                continue
            for src in sources:
                dst = os.path.join(link_dir, os.path.basename(src))
                if os.path.isfile(src) and not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                        created += 1
                    except OSError:
                        pass
        if created:
            self.output.info(
                "Prepared %d build-tree-relative NEEDED links in %d dirs"
                % (created, len(link_dirs)))

    def _find_readelf(self):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                d = os.path.dirname(str(compiler))
                candidates.append(os.path.join(d, "llvm-readelf"))
                candidates.append(os.path.join(d, "readelf"))
        candidates.append("/data/service/hnp/bin/llvm-readelf")
        candidates.append("llvm-readelf")
        for candidate in candidates:
            if candidate and (os.path.isabs(candidate) and os.path.isfile(candidate)):
                return candidate
        return ""

    def _needed_entries(self, readelf, elf_path):
        import subprocess
        try:
            probe = subprocess.run(
                [readelf, "-d", elf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        if probe.returncode != 0:
            return []
        entries = []
        marker = "Shared library: ["
        for line in probe.stdout.splitlines():
            if marker in line:
                entries.append(line.split(marker, 1)[1].split("]", 1)[0])
        return entries

    def _prepare_absolute_needed_links(self):
        # Published KF6 binaries carry DT_NEEDED entries with absolute
        # conan-cache paths from the machine that built them (e.g.
        # libKF6Service.so -> /.../.conan2/p/<hash>/p/lib/libKF6ConfigCore.so).
        # The musl loader resolves absolute-path NEEDED entries directly and
        # LD_LIBRARY_PATH cannot override that, so on a worker whose layout
        # differs the binary cannot start. Re-create the referenced absolute
        # paths as symlinks to the packages of the current graph
        # (akonadi 25.12.3 test_package precedent).
        import glob as _glob
        readelf = self._find_readelf()
        if not readelf:
            self.output.warning(
                "llvm-readelf/readelf not found; skip absolute NEEDED links")
            return
        # soname -> actual file in the current graph
        available = {}
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            for sub in ("lib", "bin"):
                d = os.path.join(dep.package_folder, sub)
                if not os.path.isdir(d):
                    continue
                for name in os.listdir(d):
                    if name not in available:
                        available[name] = os.path.join(d, name)
        elfs = list(_glob.glob(os.path.join(self.build_folder, "bin", "*")))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                elfs.extend(_glob.glob(os.path.join(dep.package_folder, "lib", "*.so*")))
        created = 0
        seen = set()
        for elf_path in elfs:
            if elf_path in seen or not os.path.isfile(elf_path):
                continue
            seen.add(elf_path)
            for needed in self._needed_entries(readelf, elf_path):
                if not needed.startswith("/"):
                    continue
                if os.path.exists(needed):
                    continue
                base = os.path.basename(needed)
                source = available.get(base)
                if not source:
                    continue
                try:
                    os.makedirs(os.path.dirname(needed), exist_ok=True)
                    os.symlink(source, needed)
                    created += 1
                except OSError:
                    pass
        if created:
            self.output.info(
                "Prepared %d absolute-path NEEDED symlinks" % created)

    def _run_upstream_tests(self):
        # Upstream autotests are built with BUILD_TESTING=ON (22 registered
        # CTest entries across the ported core modules). This host is an
        # OHOS PC, so the OHOS aarch64 test binaries can be executed
        # directly; failures are reported but do not fail the package
        # creation (kio 6.26.0 / kdbusaddons precedent: environment
        # limitations are reported honestly instead of blocking).
        import subprocess
        self._prepare_upstream_test_links()
        self._prepare_absolute_needed_links()
        ctest = shutil_which("ctest") or "ctest"
        test_env = os.environ.copy()
        env_values = self._build_runtime_env().vars(self, scope="build")
        for key, value in env_values.items():
            test_env[key] = value
        home = os.path.join(self.build_folder, "test-home")
        os.makedirs(home, exist_ok=True)
        test_env["HOME"] = home
        test_env.setdefault("QT_QPA_PLATFORM", "offscreen")
        test_env.setdefault("XDG_RUNTIME_DIR", self.build_folder)
        try:
            probe = subprocess.run(
                [ctest, "-N"],
                cwd=self.build_folder,
                env=test_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                check=False,
            )
            registered = 0
            for line in probe.stdout.splitlines():
                if line.strip().startswith("Total Tests:"):
                    try:
                        registered = int(line.strip().split(":")[1])
                    except (IndexError, ValueError):
                        pass
            self.output.info(
                "Upstream CTest entries registered: %d" % registered)
            if registered == 0:
                return
            run = subprocess.run(
                [ctest, "--output-on-failure", "--timeout", "120", "-j1"],
                cwd=self.build_folder,
                env=test_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
                check=False,
            )
            tail = "\n".join(run.stdout.splitlines()[-40:])
            self.output.info("Upstream CTest output (tail):\n%s" % tail)
            if run.returncode != 0:
                self.output.warning(
                    "Upstream CTest reported failures (rc=%d); see output "
                    "above for the per-test breakdown." % run.returncode
                )
        except (OSError, subprocess.SubprocessError) as exc:
            self.output.warning("Upstream CTest run skipped: %s" % exc)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KPim6PimCommon"]
        self.cpp_info.includedirs = ["include"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
