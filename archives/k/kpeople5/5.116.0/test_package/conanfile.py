#!/usr/bin/env python3
"""Conan test_package for kpeople5 5.116.0 (L1 official test).

Consumer-side verification (R34): the C++ test links KF5::People and drives
the real public API — PersonsModel, PersonPluginManager data-source
registry, PersonsSortFilterProxyModel requiredProperties round-trip, the
KPeople::iconNameForPresenceString / presenceSortPriority helpers and a
PersonData constructed on an invalid URI — plus HarmonyOS-specific checks
(R53): the loaded libKF5People.so carries the unversioned DT_SONAME and a
DT_RUNPATH (E537 install-RPATH adaptation).

test() really executes the built binary through self.run() (L0d / R34).
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KPeople5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("qt-unixodbc/5.15.2")
        # libKF5People.so's KF5/Qt runtime deps declared DIRECTLY: on the
        # CI workers the test consumer graph does not expose kpeople5's
        # transitive requirements (build #90589: compat-lib ended up with
        # libKF5People.so but no libKF5CoreAddons.so.5, so the loader fell
        # through to the conanrun raw remote copy with the invalidated
        # .codesign and hard-failed). Direct requires put their package
        # folders into self.dependencies, which feeds BOTH the compat-lib
        # staging (re-signed alias copies) and the welded loader search
        # path — the main recipe's autotest staging works on CI for
        # exactly this reason (kcoreaddons5 is its direct requirement).
        # Same refs/versions as the main recipe, already in the graph.
        self.requires("kcoreaddons5/5.116.0")
        self.requires("kwidgetsaddons5/5.116.0")
        self.requires("ki18n5/5.116.0")
        self.requires("kitemviews5/5.116.0")
        self.requires("qt5-qtdeclarative/5.15.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        # Consume the native Qt5 configs shipped inside qt5-qtbase and
        # qt-unixodbc's none-mode suppression (same wiring as the library
        # build).
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.set_property("qt-unixodbc", "cmake_find_mode", "none")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        if str(self.settings.os) == "OHOS":
            # Same Linux-like platform force as the library build so the
            # native Qt5 configs apply their POSIX settings.
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qtbase = self.dependencies.get("qt5-qtbase")
        qtsql = self.dependencies.get("qt-unixodbc")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                % pkg.package_folder
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % qt_pkg)
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % qt_pkg)
        if qtsql:
            sql_pkg = qtsql.package_folder
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % sql_pkg)
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _build_env(self):
        # The Qt host tools (moc/uic) need the compatible libc++ first.
        env = Environment()
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resign_ohos_elf(self, path):
        # Re-sign an ELF copy with the OHOS self-sign tool: the dependency
        # binaries downloaded from the remote may carry an invalidated
        # .codesign section that the OHOS loader refuses to mmap (the
        # upstream-recipe twin of this helper carries the full experiment
        # log; ki18n 6.26.0.1 / kitemmodels 6.18.0.1 re-signing precedent).
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        if not self._is_elf(path):
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warn(
                "OHOS ELF signing tools unavailable; skipping resign of %s" % path
            )
            return
        # /system/lib64 must lead: binary-sign-tool NEEDED libc++.so (__h
        # namespace) which only the system libc++.so provides.
        sign_env = Environment()
        sign_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with sign_env.vars(self).apply():
            self.run(
                '"%s" --remove-section .codesign "%s"' % (objcopy, path),
                ignore_errors=True,
            )
            # CI-proven variant (xdg-desktop-portal #14823, green on the
            # same workers): sign to a SEPARATE output file and atomically
            # replace. Same-path in/out left the staged copies section-
            # removed-but-unsigned on the CI worker (build #90598: every
            # staged soname unloadable, zero sign evidence for compat-lib)
            # while local runs passed either way.
            signed = path + ".signed"
            self.run(
                '"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                % (signer, path, signed)
            )
            if os.path.isfile(signed):
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def _stage_versioned_lib_aliases(self):
        # The consumer binary loads libKF5People.so from the kpeople5
        # package folder, whose versioned NEEDED entries (libKF5CoreAddons
        # .so.5) resolve on the CI workers to DOWNLOADED package binaries
        # that may carry an invalidated OHOS .codesign section - the loader
        # refuses to mmap them ("Error loading shared library
        # libKF5CoreAddons.so.5", empty errno, KJob/KPluginFactory
        # relocation avalanche).  Stage a compat dir with HARD COPIES of
        # every real dependency library under all of its alias names (bare
        # .so / major .so.5 / full version), re-signed so the loader
        # accepts them, and keep it first on LD_LIBRARY_PATH (searched
        # before DT_RUNPATH).  Same loader gap as the upstream autotests,
        # see the recipe's _prepare_ctest_runtime_links.
        compat = os.path.join(self.build_folder, "compat-lib")
        os.makedirs(compat, exist_ok=True)
        lib_sources = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        # The kpeople5 package folder itself: libKF5People.so et al are
        # freshly built by this conan create run - stage them unresigned.
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        if pkg and pkg.package_folder:
            lib_sources.extend(
                glob.glob(os.path.join(pkg.package_folder, "lib", "lib*.so*"))
            )
        dep_names = set()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                dep_names.add(dep.package_folder)
        for src_path in lib_sources:
            if os.path.islink(src_path):
                # Symlink names are untrustworthy staging anchors; the real
                # file is reached through its own full-versioned name.
                continue
            base = os.path.basename(src_path)
            # dep_names holds package-folder ROOTS; the glob sources live
            # one level below (<root>/lib), so compare the PARENT dir.
            # (CI builds #90598/#90615: dirname(src_path)-in-dep_names
            # compared "<root>/lib" against "<root>" and never matched,
            # so every dependency copy was staged UNSIGNED — the OHOS
            # loader then rejected the remote packages' invalidated
            # .codesign and test_kpeople5 died loading
            # libKF5CoreAddons.so.5 while local runs passed because the
            # local cache holds healthy signatures.)
            is_dep_copy = (
                os.path.dirname(os.path.dirname(src_path)) in dep_names
            )
            dst_main = os.path.join(compat, base)
            if not os.path.exists(dst_main):
                shutil.copy2(src_path, dst_main)
                if is_dep_copy:
                    self._resign_ohos_elf(dst_main)
            names = {base}
            if base.endswith(".so"):
                names.add(base[:-3] + ".so.5")
            else:
                m = re.match(r"^(lib\S+)\.so\.(\d+)(?:\..*)?$", base)
                if m:
                    names.add(m.group(1) + ".so." + m.group(2))
                    names.add(m.group(1) + ".so")
            for name in sorted(names - {base}):
                dst = os.path.join(compat, name)
                if not os.path.exists(dst):
                    shutil.copy2(dst_main, dst)
        return compat

    def test(self):
        if not can_run(self):
            return
        compat = self._stage_versioned_lib_aliases()
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("XDG_DATA_HOME",
                   os.path.join(self.build_folder, "xdg-data"))
        with env.vars(self).apply():
            # CI builds 90459/90518: the OHOS musl loader hard-fails on
            # the FIRST candidate for a NEEDED soname that carries an
            # invalidated .codesign section (registry downloads on the
            # workers) and does NOT continue the search. Layered env
            # injection cannot guarantee the re-signed compat copies are
            # searched first — conanrun.sh sources after every
            # Environment() prepend and re-prepends the raw dependency
            # libdirs in front — so weld the full search order into the
            # command line itself (xdg-desktop-portal #14823 pattern):
            # compat (re-signed aliases) first, then the system dir, then
            # every dependency libdir, then whatever conanrun provided.
            search = [compat]
            if str(self.settings.os) == "OHOS":
                search.append("/system/lib64")
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    lib = os.path.join(dep.package_folder, "lib")
                    if lib not in search:
                        search.append(lib)
            prefix = os.pathsep.join(search) + os.pathsep
            exe = os.path.join(self.cpp.build.bindirs[0], "test_kpeople5")
            self.run(
                'export LD_LIBRARY_PATH="%s$LD_LIBRARY_PATH"; exec "%s"'
                % (prefix, exe),
                env="conanrun",
            )
