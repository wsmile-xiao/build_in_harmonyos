#!/usr/bin/env python3
"""Conan recipe for libkdegames 26.04.0 on HarmonyOS PC (aarch64).

libkdegames is the shared library used by KDE games (kfourinline, etc.).
Upstream 26.04.0 is a Qt6/KF6 based CMake project (ECM toolchain).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation (po/
    processing requires a full gettext toolchain not needed for the library)
  - BUILD_SVG_CHECKS=OFF (default) so carddecks SVG processing only needs
    gzip; svgcleaner/7zip stay optional and are not used
  - Dependencies resolved from the ohpcd registry: qtbase 6.11.1.1,
    qtdeclarative 6.11.1 (Qt6::Qml/Quick), qtsvg 6.11.1 (Qt6::Svg),
    KF6 6.18.0 framework set + kdnssd 6.29.0, openal-soft 1.25.2,
    libsndfile 1.2.2, ecm 6.26.0 (tool_requires)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake written manually because qtbase (and the
    other KF6 packages) use cmake_find_mode=none, which prevents CMakeDeps
    from adding their lib/cmake dirs to CMAKE_PREFIX_PATH
  - Upstream ctest suite (tests/ + src/private/tests/, BUILD_TESTING=ON)
    is executed inside the build with an offscreen Qt platform and a
    sandboxed XDG/HOME tree
"""
import os
import glob
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibkdegamesConan(ConanFile):
    name = "libkdegames"
    version = "26.04.0"
    description = (
        "KDE games shared library - common code for KDE games "
        "(KGameRenderer, KGameTheme, highscore framework, kgamedialog, audio)"
    )
    license = "LGPL-2.0-only"
    homepage = "https://invent.kde.org/games/libkdegames"
    url = "https://invent.kde.org/games/libkdegames"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtsvg/6.11.1")
        # karchive: force the 6.18.0 line for the whole graph. The newest
        # kiconthemes/6.18.0 recipe revision requires karchive/6.19.0, which
        # conflicts with knewstuff/6.18.0 (karchive/6.18.0). Override pins the
        # compatible 6.18.0 so the KF6 6.18 closure stays consistent.
        self.requires("karchive/6.18.0", override=True)
        self.requires("kcolorscheme/6.18.0")
        self.requires("kcompletion/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kdnssd/6.29.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("knewstuff/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("openal-soft/1.25.2")
        self.requires("libsndfile/1.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # po/ catalog processing is not needed for the library itself.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        qt_extra = []
        for dep_name in ("qtdeclarative", "qtshadertools", "qtsvg"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

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

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
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
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(test_tmp, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("TMPDIR", test_tmp)
        test_env.define("TEMP", test_tmp)
        test_env.define("TMP", test_tmp)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        self._prepare_ctest_runtime_links()
        self._prepare_needed_compatibility_links((self.build_folder,))
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
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

    def _runtime_elf_roots(self, extra_roots=()):
        roots = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                roots.append(os.path.join(dep.package_folder, "lib"))
                roots.append(os.path.join(dep.package_folder, "bin"))
        roots.extend(root for root in extra_roots if root)

        seen = set()
        for root in roots:
            normalized = os.path.normpath(root)
            if normalized in seen:
                continue
            seen.add(normalized)
            yield normalized

    def _runtime_library_map(self, extra_roots=()):
        libraries = {}
        for root in self._runtime_elf_roots(extra_roots):
            if not os.path.isdir(root):
                continue
            for current, dirs, files in os.walk(root):
                dirs[:] = [name for name in dirs if name != "CMakeFiles"]
                for name in files:
                    path = os.path.join(current, name)
                    if os.path.isfile(path) and (".so" in name or name.startswith("lib")):
                        libraries.setdefault(name, path)
        return libraries

    def _iter_runtime_elfs(self, extra_roots=()):
        for root in self._runtime_elf_roots(extra_roots):
            if not os.path.isdir(root):
                continue
            for current, dirs, files in os.walk(root):
                dirs[:] = [name for name in dirs if name != "CMakeFiles"]
                for name in files:
                    path = os.path.join(current, name)
                    if self._is_elf(path):
                        yield path

    def _needed_entries(self, readelf, elf_path):
        try:
            probe = subprocess.run(
                [readelf, "-d", elf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
        except OSError as exc:
            self.output.warning(f"readelf failed for {elf_path}: {exc}")
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
    def _is_conan_cache_needed_path(needed):
        return os.path.isabs(needed) and "/.cache/conan2/" in needed.replace("\\", "/")

    @staticmethod
    def _is_relative_needed_path(needed):
        return not os.path.isabs(needed) and "/" in needed.replace("\\", "/")

    def _link_needed_library(self, source, target):
        if os.path.lexists(target):
            try:
                if os.path.exists(target) and os.path.samefile(source, target):
                    return False
            except OSError:
                pass
            if os.path.exists(target) and not os.path.islink(target):
                return False
            os.unlink(target)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            os.symlink(source, target)
        except OSError:
            shutil.copy2(source, target)
        return True

    def _prepare_needed_compatibility_links(self, extra_roots=()):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        readelf = self._find_ohos_tool("llvm-readelf") or self._find_ohos_tool("readelf")
        if not readelf:
            self.output.warning("llvm-readelf/readelf not found; skip NEEDED links")
            return

        libraries = self._runtime_library_map(extra_roots)
        elf_paths = list(self._iter_runtime_elfs(extra_roots))
        needed_by_elf = {
            elf_path: self._needed_entries(readelf, elf_path)
            for elf_path in elf_paths
        }

        created_absolute = 0
        created_relative = 0
        missing = []
        for entries in needed_by_elf.values():
            for needed in entries:
                if not self._is_conan_cache_needed_path(needed):
                    continue
                source = libraries.get(os.path.basename(needed))
                if not source:
                    missing.append(needed)
                    continue
                if self._link_needed_library(source, needed):
                    created_absolute += 1

        relative_bases = {os.path.abspath(root) for root in extra_roots if root}
        relative_bases.add(os.path.abspath(self.build_folder))
        # Upstream test executables run with cwd = their CMakeLists dir
        # (e.g. build/src/private/tests). Their DT_NEEDED entries like
        # "../../bin/libKDEGames6.so" resolve relative to that cwd, i.e. to
        # build/src/bin/. Provide compatibility links there as well.
        for rel in ("src", "tests", os.path.join("src", "private")):
            relative_bases.add(
                os.path.abspath(os.path.join(self.build_folder, rel, "bin"))
            )
        relative_bases.add(
            os.path.abspath(os.path.join(self.build_folder, os.pardir, "bin"))
        )
        for elf_path, entries in needed_by_elf.items():
            for needed in entries:
                if not self._is_relative_needed_path(needed):
                    continue
                source = libraries.get(os.path.basename(needed))
                if not source:
                    missing.append(needed)
                    continue
                targets = {
                    os.path.normpath(os.path.join(os.path.dirname(elf_path), needed))
                }
                targets.update(
                    os.path.normpath(os.path.join(base, needed))
                    for base in relative_bases
                )
                for target in targets:
                    if self._link_needed_library(source, target):
                        created_relative += 1

        if created_absolute or created_relative:
            self.output.info(
                "Prepared NEEDED compatibility links: "
                f"{created_absolute} absolute, {created_relative} relative"
            )
        if missing:
            self.output.warning(
                "Missing sources for NEEDED entries: "
                + ", ".join(sorted(set(missing))[:8])
            )

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()

    def package_info(self):
        # The project installs its own KDEGames6Config.cmake with proper
        # dependency tracking (find_dependency on Qt6/KF6). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KDEGames6", "KDEGames6Private"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.package_folder, "plugins")
        )
        self.runenv_info.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.package_folder, "lib", "plugins")
        )
        self.runenv_info.prepend_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "qml")
        )
