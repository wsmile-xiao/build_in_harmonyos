#!/usr/bin/env python3
"""Conan recipe for libkeduvocdocument 26.04.0 on HarmonyOS PC (aarch64).

libkeduvocdocument (KDE Gear 26.04.0, upstream CMake project
``LibKEduVocDocument`` VERSION 5.1.0) ships the vocabulary-document
library libKEduVocDocument.so.5 used by Parley, KWordQuiz, KHangman and
Kanagram to read/write the KVTML/KVTL vocabulary formats plus the CSV,
Pauker, Vokabeln, WordQuiz (wql) and XDXF import formats.

Upstream hard requirements (CMakeLists.txt):
    cmake_minimum_required(VERSION 3.16)
    find_package(ECM 6.3.0 REQUIRED NO_MODULE)
    find_package(Qt6 6.4.0 REQUIRED NO_MODULE COMPONENTS Xml)
    find_package(KF6 6.3.0 REQUIRED COMPONENTS I18n Archive KIO)
    target_link_libraries(KEduVocDocument PUBLIC Qt6::Xml
                          PRIVATE KF6::I18n KF6::KIOCore KF6::Archive)
The upstream test trees additionally need KF6::CoreAddons and Qt6::Test.

Dependency line: published KF6 6.26.0 line (qtbase/6.11.1 + ki18n +
karchive + kio 6.26.0, whose own recipe requires kconfig/kcoreaddons/
kservice/kcrash 6.26.0 - the whole graph therefore reuses published
binaries built against the same qtbase/6.11.1) and ecm/6.26.0 as the
build tool (libktorrent 26.04.0 / kio 6.26.0 precedent).

OHOS adaptations (configuration only - no source patch):
  - KF_IGNORE_PLATFORM_CHECK=TRUE: bypass the KDE platform whitelist
    (HarmonyOS is not recognised by ECM's platform detection).
  - KF_SKIP_PO_PROCESSING=ON: ki18n_install(po) needs gettext/msgfmt for
    86 translations; OHOS ships no msgfmt and translations are not
    required for the library to function (accessibility 26.04.3 /
    keditbookmarks 26.04.0 precedent).
  - CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG/-C_FLAG: CMake has no
    Platform/HarmonyOS module, so the SONAME link flag is undefined and
    libKEduVocDocument.so.5.1.0 would ship without DT_SONAME (consumers
    would record a path-form DT_NEEDED, E537). Supplying the flag at
    link time lets lld emit the real soname from upstream's
    VERSION/SOVERSION properties (keditbookmarks / kio 6.26.0 precedent).
  - libxml2/2.15.3: the OHOS SDK lld needs libxml2.so.16 (libxml2/2.15.3
    SONAME) while linking KIOCore; its lib dir is injected into
    LD_LIBRARY_PATH for the build (kio 6.26.0 / keditbookmarks
    precedent). /system/lib64 is prepended so the host tools pick the
    compatible libc++_shared.so instead of the SDK linker script.
  - ECM_MODULE_PATH is set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate it; conan_cmakedeps_paths.cmake is
    written by hand because qtbase and the KF6 packages use
    cmake_find_mode=none. ECM's find-modules dir is on CMAKE_MODULE_PATH
    so the umbrella find_package(KF6 COMPONENTS I18n Archive KIO)
    resolves through FindKF6.cmake.

Upstream tests: BUILD_TESTING=ON registers 10 ctest entries
(keduvocdocument/tests: sharedkvtmlfilestest, converter;
keduvocdocument/autotests non-GUI: keduvocdocumenttest,
emptydocumenttest, keduvoctexttest; autotests GUI/static:
readerkvtml2test, readerwordquiztest, readerpaukertest,
readervokabelntest, readerxdxftest). They are executed inside build()
with the offscreen QPA platform and a sandboxed HOME/XDG tree.
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


class LibkeduvocdocumentConan(ConanFile):
    name = "libkeduvocdocument"
    version = "26.04.0"
    description = (
        "libkeduvocdocument - KDE vocabulary document library "
        "(KVTML/KVTL readers and writers used by Parley/KWordQuiz)"
    )
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/education/libkeduvocdocument"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/libkeduvocdocument-26.04.0.tar.xz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("ki18n/6.26.0")
        self.requires("karchive/6.26.0")
        self.requires("kio/6.26.0")
        # kio link-time requirement on OHOS: the SDK lld loads
        # libxml2.so.16 (libxml2/2.15.3 SONAME) while linking KIOCore.
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # CMake ships no Platform/HarmonyOS.cmake -> no SONAME flag.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])
        self._write_cmake_paths(ecm)
        tc.generate()

        # Build-time helper tools (moc, uic, kconfig_compiler_kf6, lld) run
        # as plain processes; expose every dependency lib dir plus
        # /system/lib64 to the build environment.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    self.buildenv.append_path("LD_LIBRARY_PATH", lib_dir)

    def _write_cmake_paths(self, ecm):
        # qtbase and the KF6 packages use cmake_find_mode=none, so the
        # generated conan_cmakedeps_paths.cmake would not contain their
        # lib/cmake dirs. Write it manually (keditbookmarks precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        deps = list(self.dependencies.values()) + list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                    % dep.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % dep.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % dep.package_folder
                )
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            for sub in ("cmake", "find-modules", "modules", "kde-modules"):
                lines.append(
                    'list(PREPEND CMAKE_MODULE_PATH "%s/%s")' % (ecm_share, sub)
                )
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s/%s")' % (ecm_share, sub)
                )
        if self.settings.os == "OHOS":
            for sdk_inc in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/"
                    "sysroot/usr/include")):
                lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s")' % sdk_inc)
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
        for rel in ("bin", "lib", os.path.join("keduvocdocument", "bin")):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return env

    def _build_env(self):
        # Prepend /system/lib64 LAST so it ends up FIRST: the SDK
        # aarch64-linux-ohos/libc++.so is a linker script the runtime
        # loader cannot use (kconfig/kcrash 6.26.0 precedent).
        env = self._runtime_env()
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        if str(self.settings.os) in ("Linux", "OHOS"):
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        env = self._build_env()
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        env.define("CTEST_PARALLEL_LEVEL", "1")
        env.define("QT_QPA_PLATFORM", "offscreen")
        home = os.path.join(self.build_folder, "test-home")
        tmp = os.path.join(self.build_folder, "test-tmp")
        xdg = os.path.join(self.build_folder, "xdg-runtime")
        for d in (home, tmp, xdg):
            os.makedirs(d, exist_ok=True)
        os.chmod(xdg, 0o700)
        env.define("HOME", home)
        env.define("TMPDIR", tmp)
        env.define("TEMP", tmp)
        env.define("TMP", tmp)
        env.define("XDG_RUNTIME_DIR", xdg)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        self._bridge_absolute_needed_paths()
        self._prepare_test_runtime_links()
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "%s" --output-on-failure --no-tests=error'
                % self.build_folder
            )
            self._run_unregistered_upstream_tests(tmp)

    def _run_unregistered_upstream_tests(self, work_dir):
        """Run the two upstream test programs that upstream builds but never
        registers with ctest (keduvocdocument/tests/CMakeLists.txt uses
        ecm_mark_as_test, which only marks the targets EXCLUDE_FROM_ALL and
        does *not* call add_test). They are genuine upstream test artifacts,
        so they are exercised explicitly here:

          * sharedkvtmlfilestest - SharedKvtmlFiles::languages()/fileNames()
          * converter            - KEduVocDocument::open()/saveAs() round trip
        """
        bindir = os.path.join(self.build_folder, "bin")
        shared = os.path.join(bindir, "sharedkvtmlfilestest")
        converter = os.path.join(bindir, "converter")
        if not (os.path.isfile(shared) and os.path.isfile(converter)):
            self.output.warning(
                "upstream test executables not found in %s; skipping" % bindir
            )
            return

        self.output.info("[upstream] sharedkvtmlfilestest (no args)")
        self.run('"%s"' % shared)

        sample = os.path.join(
            self.source_folder, "keduvocdocument", "kvtml_empty_sample.kvtml"
        )
        if not os.path.isfile(sample):
            self.output.warning("upstream KVTML sample missing: %s" % sample)
            return
        outfile = os.path.join(work_dir, "converter-roundtrip.kvtml")
        self.output.info(
            "[upstream] converter %s %s (KVTML2 read/write round trip)"
            % (sample, outfile)
        )
        self.run('"%s" "%s" "%s"' % (converter, sample, outfile))
        if not os.path.isfile(outfile) or os.path.getsize(outfile) == 0:
            raise ConanException(
                "converter did not produce an output document: %s" % outfile
            )
        with open(outfile, "r", encoding="utf-8", errors="replace") as handle:
            produced = handle.read()
        if '<kvtml version="2.0">' not in produced:
            raise ConanException(
                "converter output is not a KVTML 2 document: %s" % outfile
            )
        if "<identifier" not in produced:
            raise ConanException(
                "converter lost the identifiers of the source document"
            )
        self.output.info(
            "[upstream] converter round trip OK (%d bytes, identifiers kept)"
            % os.path.getsize(outfile)
        )

    def _bridge_absolute_needed_paths(self):
        """E537: published KF6 binaries (kio/6.26.0 in particular) embed
        absolute Conan cache DT_NEEDED entries pointing at the cache layout of
        the machine that built them (".../.cache/conan2/p/<hash>/p/lib/
        libKF6I18n.so"). The musl loader resolves absolute DT_NEEDED entries
        directly and LD_LIBRARY_PATH cannot override them, so materialize the
        missing paths as symlinks onto the libraries that are present in this
        worker's cache. No-op where the paths already exist.
        (akonadi 25.12.3 precedent.)"""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        readelf = self._find_tool("llvm-readelf") or self._find_tool("readelf")
        if not readelf:
            self.output.warning(
                "llvm-readelf/readelf not found; skipping absolute DT_NEEDED bridge"
            )
            return
        libraries = {}
        elf_paths = []
        roots = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for sub in ("lib", "bin"):
                    roots.append(os.path.join(dep.package_folder, sub))
        for rel in ("bin", "lib", os.path.join("keduvocdocument", "bin")):
            roots.append(os.path.join(self.build_folder, rel))
        for root in roots:
            if not os.path.isdir(root):
                continue
            for name in sorted(os.listdir(root)):
                path = os.path.join(root, name)
                if not os.path.isfile(path):
                    continue
                if ".so" in name:
                    libraries.setdefault(name, path)
                    elf_paths.append(path)
                elif os.access(path, os.X_OK):
                    elf_paths.append(path)

        created = 0
        missing = []
        for elf_path in elf_paths:
            for needed in self._needed_entries(readelf, elf_path):
                if not os.path.isabs(needed) or os.path.exists(needed):
                    continue
                source = libraries.get(os.path.basename(needed))
                if not source:
                    missing.append(needed)
                    continue
                if self._link_as(source, needed):
                    created += 1
        if created:
            self.output.info(
                "E537 bridge: materialized %d absolute DT_NEEDED path(s)" % created
            )
        if missing:
            self.output.warning(
                "E537 bridge: %d absolute DT_NEEDED entries unresolved: %s"
                % (len(missing), sorted(set(missing))[:5])
            )

    @staticmethod
    def _needed_entries(readelf, elf_path):
        try:
            probe = subprocess.run(
                [readelf, "-d", elf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
        except OSError:
            return []
        if probe.returncode != 0:
            return []
        entries = []
        marker = "Shared library: ["
        for line in probe.stdout.splitlines():
            if marker in line:
                entries.append(line.split(marker, 1)[1].split("]", 1)[0])
        return entries

    @staticmethod
    def _link_as(source, target):
        if os.path.lexists(target):
            if os.path.exists(target):
                return False
            os.unlink(target)
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            os.symlink(source, target)
        except OSError:
            shutil.copy2(source, target)
        return True

    def _find_tool(self, name):
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

    def _prepare_test_runtime_links(self):
        # Published KF6 binaries may carry build-tree relative DT_NEEDED
        # entries ("../../bin/libKF6*.so"); the loader resolves them
        # relative to the test process cwd. Provide compatibility links at
        # every plausible bin/ location (keditbookmarks / ktextwidgets
        # precedent).
        candidate_bases = [
            self.build_folder,
            os.path.normpath(os.path.join(self.build_folder, "keduvocdocument")),
            os.path.normpath(
                os.path.join(self.build_folder, "keduvocdocument", "autotests")
            ),
            os.path.normpath(
                os.path.join(self.build_folder, "keduvocdocument", "tests")
            ),
        ]
        roots = []
        for base in candidate_bases:
            roots.append(os.path.join(base, "bin"))
            roots.append(os.path.normpath(os.path.join(base, os.pardir, "bin")))
        sources = []
        for rel in ("bin", "lib", os.path.join("keduvocdocument", "bin"),
                    os.path.join("keduvocdocument", "lib")):
            sources.extend(glob.glob(os.path.join(self.build_folder, rel, "lib*.so*")))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                sources.extend(glob.glob(
                    os.path.join(dep.package_folder, "lib", "lib*.so*")))
        seen = set()
        for root in roots:
            if root in seen or not os.path.isdir(os.path.dirname(root)):
                continue
            seen.add(root)
            os.makedirs(root, exist_ok=True)
            for src in sources:
                dst = os.path.join(root, os.path.basename(src))
                if os.path.exists(src) and not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream installs its own LibKEduVocDocumentConfig.cmake
        # (configured from LibKEduVocDocumentConfig.cmake.in) next to
        # LibKEduVocDocumentTargets.cmake under lib/cmake/libkeduvocdocument,
        # so CMakeDeps must not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KEduVocDocument"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
