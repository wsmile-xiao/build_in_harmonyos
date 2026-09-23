#!/usr/bin/env python3
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KNewStuffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qt_extra = []
        for dep_name in ("qtdeclarative", "qtshadertools"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
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

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._prepare_runtime_links()
        env = Environment()
        runtime_dirs = [
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "bin")),
        ]
        for runtime_dir in runtime_dirs:
            env.prepend_path("LD_LIBRARY_PATH", runtime_dir)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
                env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        env.define("TMPDIR", test_tmp)
        env.define("TEMP", test_tmp)
        env.define("TMP", test_tmp)
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_knewstuff")
        with env.vars(self).apply():
            self.run(test_exe, cwd=self.cpp.build.bindirs[0])

    def _prepare_runtime_links(self):
        runtime_dirs = [
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "bin")),
        ]
        for runtime_dir in runtime_dirs:
            os.makedirs(runtime_dir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if not libdir or not os.path.isdir(libdir):
                continue
            for src in glob.glob(os.path.join(libdir, "lib*.so*")):
                for runtime_dir in runtime_dirs:
                    dst = os.path.join(runtime_dir, os.path.basename(src))
                    if os.path.exists(dst):
                        continue
                    shutil.copy2(src, dst)
        self._prepare_needed_compatibility_links(runtime_dirs)

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
