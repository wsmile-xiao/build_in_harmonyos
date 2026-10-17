#!/usr/bin/env python3
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibksieveConan(ConanFile):
    name = "libksieve"
    version = "25.12.3"
    description = "Sieve and Managesieve filtering support libraries for KDE PIM"
    license = "GPL-2.0-only"
    homepage = "https://invent.kde.org/pim/libksieve"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    _preferred_dep_order = (
        "qtbase-sql-dbus",
        "qtbase",
        "qtsvg",
        "kio",
        "kxmlgui",
        "kconfig",
        "kcoreaddons",
        "ki18n",
        "kcodecs",
        "kiconthemes",
        "kcolorscheme",
        "karchive",
        "kwidgetsaddons",
        "ksyntaxhighlighting",
        "sonnet",
        "knewstuff",
        "openssl",
        "zstd",
        "cyrus-sasl",
        "ecm",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KDE PIM 25.12.3 + KF6 6.18.0 published baseline line shared by the
        # peer PIM recipes (kidentitymanagement/kimap/kpimtextedit).
        self.requires("qtbase-sql-dbus/6.11.1")
        # KSieveUi links Qt::WebEngineWidgets (hard upstream REQUIRED). qtwebengine is
        # not available for OHOS aarch64, so we build the remaining libs and skip
        # KSieveUi via the optional-webengine patch; no hard conan requirement here.
        self.requires("qtsvg/6.11.1")
        # Newest kiconthemes/6.18.0 recipe revision requires karchive/6.19.0,
        # which conflicts with the KF6 6.18.0/PIM baseline (karchive/6.18.0)
        # shared by the peer PIM recipes. Pin kiconthemes/6.18.0.1, which
        # depends on karchive/6.18.0, and force both to resolve consistently.
        self.requires("karchive/6.18.0", override=True)
        self.requires("kiconthemes/6.18.0.1", override=True)
        self.requires("kcodecs/6.18.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        # kio is NOT required: kio/6.18.0 is not yet published to the OHOS remote,
        # and the KManageSieve/KSieveCore libraries that need it are excluded via
        # patch 0002 (KF6KIO made OPTIONAL, subdirs guarded by KF6KIO_FOUND). The
        # KSieve parser library + its 2 upstream parser autotests and the consumer
        # test_package only need KPim6::KSieve. When kio/6.18.0 becomes published,
        # re-add `self.requires("kio/6.18.0")` to restore KManageSieve/KSieveCore.
        self.requires("knewstuff/6.18.0")
        self.requires("ksyntaxhighlighting/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("sonnet/6.18.0")
        self.requires("openssl/3.5.6.1")
        # kiconthemes/6.18.0.1's closure (karchive -> zstd) pulls zstd/1.5.7, which
        # would otherwise conflict with the explicit zstd/1.5.7.1 above. Force a
        # single zstd version across the whole graph (same override strategy used
        # for kiconthemes/karchive above).
        self.requires("zstd/1.5.7.1", override=True)
        self.requires("cyrus-sasl/2.1.28.1")

        # KDE PIM 25.12.3 closure (kpimtextedit / kidentitymanagement / kimap /
        # kmailtransport / kmime / libkdepim / pimcommon / ktextaddons) is NOT
        # required here: KManageSieve / KSieveCore / KSieveUi, the only
        # consumers of those PIM + KF6::Text* packages, are excluded via
        # patches 0001 (no WebEngine) and 0002 (no KIO), and their recipes are
        # not yet published to the OHOS remote. The KSieve parser library, its
        # 2 upstream parser autotests and the consumer test_package only need
        # Qt (qtbase-sql-dbus/qtsvg) + the mainline KF6 frameworks declared
        # above.

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

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

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
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        def add_package_folder(folder):
            if not folder:
                return
            add_unique(prefixes, os.path.join(folder, "lib", "cmake"))
            add_unique(prefixes, folder)
            add_unique(libraries, os.path.join(folder, "lib"))
            add_unique(includes, os.path.join(folder, "include"))

        for dam in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dam and dam.package_folder:
                add_package_folder(dam.package_folder)

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))

        qt_sql = self.dependencies.get("qtbase-sql-dbus")
        if qt_sql and qt_sql.package_folder:
            add_unique(
                modules,
                os.path.join(qt_sql.package_folder, "lib", "cmake", "Qt6", "platforms"),
            )

        cyrus = self.dependencies.get("cyrus-sasl")
        if cyrus and cyrus.package_folder:
            add_unique(includes, os.path.join(cyrus.package_folder, "include"))
            add_unique(libraries, os.path.join(cyrus.package_folder, "lib"))

        openssl = self.dependencies.get("openssl")
        if openssl and openssl.package_folder:
            openssl_pkg = openssl.package_folder.replace("\\", "/")
            prefixes_openssl = [
                "set(OPENSSL_ROOT_DIR \"{}\" CACHE PATH \"\")".format(openssl_pkg),
                "set(OPENSSL_INCLUDE_DIR \"{}/include\" CACHE PATH \"\")".format(openssl_pkg),
                "set(OPENSSL_CRYPTO_LIBRARY \"{}/lib/libcrypto.a\" CACHE FILEPATH \"\")".format(
                    openssl_pkg
                ),
                "set(OPENSSL_SSL_LIBRARY \"{}/lib/libssl.a\" CACHE FILEPATH \"\")".format(
                    openssl_pkg
                ),
            ]
        else:
            prefixes_openssl = []

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            'set(CMAKE_PREFIX_PATH "{};${{CMAKE_PREFIX_PATH}}")'.format(";".join(prefixes)),
            'set(CMAKE_LIBRARY_PATH "{};${{CMAKE_LIBRARY_PATH}}")'.format(";".join(libraries)),
            'set(CMAKE_INCLUDE_PATH "{};${{CMAKE_INCLUDE_PATH}}")'.format(";".join(includes)),
            'set(CMAKE_MODULE_PATH "{};${{CMAKE_MODULE_PATH}}")'.format(";".join(modules)),
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ] + prefixes_openssl

        with open(
            os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w"
        ) as paths_file:
            paths_file.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._library_runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
            self._run_upstream_tests()

    def _library_runtime_env(self, include_build=False):
        runtime_env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                runtime_env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                runtime_env.prepend_path("XDG_DATA_DIRS", os.path.join(dep.package_folder, "share"))
                runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        runtime_env.define("QT_QPA_PLATFORM", "offscreen")
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env(include_build=True)
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_home = os.path.join(self.build_folder, "test-home")
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(test_tmp, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        try:
            os.chmod(xdg_runtime, 0o700)
        except OSError:
            pass
        test_env.define("HOME", test_home)
        test_env.define("TMPDIR", test_tmp)
        test_env.define("TEMP", test_tmp)
        test_env.define("TMP", test_tmp)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        self._prepare_ctest_runtime_links()
        run_cmd = 'ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 300'.format(
            self.build_folder
        )
        disc_cmd = 'ctest --test-dir "{}" -N'.format(self.build_folder)
        with test_env.vars(self).apply():
            disc_proc = subprocess.run(
                disc_cmd,
                shell=True,
                cwd=self.build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            disc_out = disc_proc.stdout or ""
            for line in disc_out.splitlines():
                self.output.info("[libksieve] ctest -N: {}".format(line.strip()[:300]))
            disc_match = re.search(r"Total Tests:\s*(\d+)", disc_out)
            discovered = int(disc_match.group(1)) if disc_match else 0

            run_proc = subprocess.run(
                run_cmd,
                shell=True,
                cwd=self.build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            run_out = run_proc.stdout or ""
            for line in run_out.splitlines():
                self.output.info("[libksieve] ctest: {}".format(line.strip()[:300]))

            # Deterministic per-test counts: ctest writes one result terminator per
            # executed test into Testing/Temporary/LastTest.log.
            last_log = os.path.join(
                self.build_folder, "Testing", "Temporary", "LastTest.log"
            )
            passed = 0
            failed = 0
            if os.path.isfile(last_log):
                with open(last_log, "r", encoding="utf-8", errors="replace") as lf:
                    for line in lf:
                        stripped = line.strip()
                        if stripped == "Test Passed.":
                            passed += 1
                        elif stripped == "Test Failed.":
                            failed += 1
            else:
                self.output.warning(
                    "[libksieve] LastTest.log not found at {}".format(last_log)
                )
            executed = passed + failed
            skipped = discovered - executed
            if skipped < 0:
                # inconsistent discovery vs executed: keep honest counts, do not clamp
                skipped = 0
            status = (
                "passed"
                if run_proc.returncode == 0
                and failed == 0
                and executed == discovered
                and discovered > 0
                else "failed"
            )
            marker = {
                "status": status,
                "framework": "ctest",
                "command": run_cmd,
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            }
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
            self.output.info(msg)
            print(msg, flush=True)
            if status != "passed":
                raise ConanException(
                    "upstream ctest failed rc={} discovered={} executed={} "
                    "passed={} failed={} (LastTest.log present={})".format(
                        run_proc.returncode,
                        discovered,
                        executed,
                        passed,
                        failed,
                        os.path.isfile(last_log),
                    )
                )

    def _prepare_ctest_runtime_links(self):
        compatibility_dirs = {
            self.build_folder,
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "lib"),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, "bin")),
        }
        for root, _, files in os.walk(self.build_folder):
            if "CTestTestfile.cmake" in files:
                compatibility_dirs.add(root)
                for depth in range(1, 5):
                    compatibility_dirs.add(
                        os.path.normpath(os.path.join(root, *([os.pardir] * depth), "bin"))
                    )
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        lib_sources.extend(glob.glob(os.path.join(self.build_folder, "lib", "lib*.so*")))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")))
        for src in lib_sources:
            for dst_dir in sorted(compatibility_dirs):
                os.makedirs(dst_dir, exist_ok=True)
                dst = os.path.join(dst_dir, os.path.basename(src))
                if os.path.exists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)

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
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
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
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
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
                    "{} --remove-section .codesign {}".format(
                        self._quote(objcopy), self._quote(path)
                    ),
                    ignore_errors=True,
                )
                self.run(
                    "{} sign -inFile {} -outFile {} -selfSign 1".format(
                        self._quote(signer), self._quote(path), self._quote(path)
                    )
                )
                try:
                    os.chmod(path, 0o755)
                except OSError as exc:
                    self.output.warning("chmod signed ELF skipped for {}: {}".format(path, exc))
                signed += 1
        self.output.info("Signed {} OHOS {} ELF file(s)".format(signed, label))

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder, "package")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        # Only the KSieve parser library (KPim6::KSieve) is built/installed on
        # OHOS: KManageSieve / KSieveCore / KSieveUi are excluded via patches
        # 0001 (no WebEngine) and 0002 (no KIO). If/when kio+qtwebengine become
        # available on the remote, restore the full lib list below.
        self.cpp_info.libs = ["KPim6KSieve"]
        self.cpp_info.includedirs = ["include"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
