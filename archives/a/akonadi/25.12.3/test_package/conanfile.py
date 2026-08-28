#!/usr/bin/env python3
"""Conan test_package for akonadi 25.12.3."""
from contextlib import contextmanager
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class AkonadiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtshadertools/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("dbus/1.14.10")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("kitemmodels/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kwindowsystem/6.18.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("kitemviews/6.18.0")
        self.requires("kcodecs/6.18.0")
        self.requires("karchive/6.19.0")
        self.requires("lzma/5.6.2")
        self.requires("libxml2/2.15.3")
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        self._configure_ohos_lld_frontend(tc)
        self._configure_ohos_compiler_wrappers(tc)
        tc.generate()
        self._write_cmake_paths()
        VirtualRunEnv(self).generate()
        self._runtime_env().vars(self, scope="run").save_script("akonadi_test_runenv")

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_folder(folder):
            if not folder:
                return
            for collection, value in (
                (prefixes, os.path.join(folder, "lib", "cmake")),
                (libraries, os.path.join(folder, "lib")),
                (includes, os.path.join(folder, "include")),
            ):
                normalized = self._cmake_path(value)
                if normalized not in collection:
                    collection.append(normalized)

        tested_name = self.tested_reference_str.split("/")[0]
        for dep_name in self._preferred_dependency_order(tested_name):
            dep = self._dependency_by_name(dep_name)
            if dep and dep.package_folder:
                add_folder(dep.package_folder)

        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            if dep.ref.name in ("qtbase", "qtbase-sql-dbus"):
                continue
            add_folder(dep.package_folder)

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            for rel in ("cmake", "modules", "find-modules", "kde-modules"):
                path = self._cmake_path(os.path.join(ecm_share, rel))
                if rel == "cmake":
                    prefixes.append(path)
                modules.append(path)

        qt_sql = self.dependencies.get("qtbase-sql-dbus")
        if qt_sql and qt_sql.package_folder:
            modules.append(
                self._cmake_path(
                    os.path.join(qt_sql.package_folder, "lib", "cmake", "Qt6", "platforms")
                )
            )

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{self._join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{self._join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{self._join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{self._join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _dependency_by_name(self, name):
        try:
            dep = self.dependencies.get(name)
        except KeyError:
            dep = None
        if dep is not None:
            return dep
        for candidate in self.dependencies.values():
            ref = getattr(candidate, "ref", None)
            if ref and ref.name == name:
                return candidate
        return None

    def _preferred_dependency_order(self, tested_name):
        return (
            tested_name,
            "qtbase-sql-dbus",
            "qtdeclarative",
            "qtshadertools",
            "qtsvg",
            "kconfig",
            "kconfigwidgets",
            "kcoreaddons",
            "ki18n",
            "kiconthemes",
            "kitemmodels",
            "kwidgetsaddons",
            "kxmlgui",
            "kcrash",
            "kwindowsystem",
            "kcolorscheme",
            "kguiaddons",
            "kitemviews",
            "kcodecs",
            "karchive",
            "lzma",
            "libxml2",
            "dbus",
            "openssl",
            "zstd",
        )

    @staticmethod
    def _cmake_path(path):
        return path.replace("\\", "/")

    @staticmethod
    def _join(values):
        return ";".join(value for value in values if value)

    def _configure_ohos_compiler_wrappers(self, tc):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return

        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        cc = compilers.get("c") or os.environ.get("CC") or "/data/service/hnp/bin/clang"
        cxx = (
            compilers.get("cpp")
            or os.environ.get("CXX")
            or "/data/service/hnp/bin/clang++"
        )
        wrapper_dir = os.path.join(self.generators_folder, "ohos-compiler-wrappers")
        os.makedirs(wrapper_dir, exist_ok=True)
        cc_wrapper = os.path.join(wrapper_dir, "clang")
        cxx_wrapper = os.path.join(wrapper_dir, "clang++")
        lld_wrapper = os.path.join(wrapper_dir, "ld.lld")
        sdk_llvm_lib = self._usable_ohos_sdk_llvm_libdir(required=False)
        self._write_ohos_lld_wrapper(lld_wrapper, sdk_llvm_lib)
        self._write_ohos_compiler_wrapper(cc_wrapper, cc, sdk_llvm_lib)
        self._write_ohos_compiler_wrapper(cxx_wrapper, cxx, sdk_llvm_lib)
        compiler_block = tc.blocks["compilers"].values
        compiler_block.setdefault("compilers", {})
        compiler_block["compilers"]["C"] = self._cmake_path(cc_wrapper)
        compiler_block["compilers"]["CXX"] = self._cmake_path(cxx_wrapper)

    def _configure_ohos_lld_frontend(self, tc):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return

        ld_lld = "/data/service/hnp/bin/ld.lld"
        tc.extra_exelinkflags.append(f"-fuse-ld={ld_lld}")
        tc.extra_sharedlinkflags.append(f"-fuse-ld={ld_lld}")

    def _write_ohos_compiler_wrapper(self, wrapper_path, compiler, sdk_llvm_lib):
        compiler = str(compiler).strip('"')
        sdk_llvm_lib = str(sdk_llvm_lib).strip('"')
        script = f"""#!/bin/sh
compiler="{compiler}"
sdk_llvm_lib="{sdk_llvm_lib}"
system_ld_lld="/data/service/hnp/bin/ld.lld"
wrapper_dir="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P || dirname "$0")"
lld_wrapper="$wrapper_dir/ld.lld"
compiler_real="$(readlink -f "$compiler" 2>/dev/null || realpath "$compiler" 2>/dev/null || printf '%s' "$compiler")"
compiler_dir="$(dirname "$compiler_real")"
derived_lib="$(dirname "$compiler_dir")/lib"
prepend_unique_ld_library_path() {{
    libdir="$1"
    new_path="$libdir"
    old_ifs="$IFS"
    IFS=:
    for part in ${{LD_LIBRARY_PATH:-}}
    do
        [ -n "$part" ] || continue
        [ "$part" = "$libdir" ] && continue
        new_path="$new_path:$part"
    done
    IFS="$old_ifs"
    export LD_LIBRARY_PATH="$new_path"
}}
for libdir in \\
    "$sdk_llvm_lib" \\
    "$derived_lib" \\
    /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib \\
    /data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib
do
    [ -d "$libdir" ] || continue
    [ -e "$libdir/libxml2.so.16" ] || continue
    prepend_unique_ld_library_path "$libdir"
    break
done
is_link=1
for arg in "$@"
do
    case "$arg" in
        -c|-S|-E|-M|-MM|-MG|-MP|-MD|-MMD|-print-*|--version|-v)
            is_link=0
            ;;
    esac
done
if [ "$is_link" = "1" ]; then
    if [ -x "$system_ld_lld" ]; then
        exec "$compiler" "-fuse-ld=$system_ld_lld" "$@"
    fi
    exec "$compiler" "-fuse-ld=$lld_wrapper" "$@"
fi
exec "$compiler" "$@"
"""
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
        try:
            os.chmod(wrapper_path, 0o755)
        except OSError as exc:
            self.output.warning(f"chmod {wrapper_path} skipped: {exc}")

    def _write_ohos_lld_wrapper(self, wrapper_path, sdk_llvm_lib):
        sdk_llvm_lib = str(sdk_llvm_lib).strip('"')
        fallback_lld = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/bin/lld"
        )
        script = f"""#!/bin/sh
sdk_llvm_lib="{sdk_llvm_lib}"
fallback_lld="{fallback_lld}"
prepend_unique_ld_library_path() {{
    libdir="$1"
    new_path="$libdir"
    old_ifs="$IFS"
    IFS=:
    for part in ${{LD_LIBRARY_PATH:-}}
    do
        [ -n "$part" ] || continue
        [ "$part" = "$libdir" ] && continue
        new_path="$new_path:$part"
    done
    IFS="$old_ifs"
    export LD_LIBRARY_PATH="$new_path"
}}
for libdir in \\
    "$sdk_llvm_lib" \\
    /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib \\
    /data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib
do
    [ -d "$libdir" ] || continue
    [ -e "$libdir/libxml2.so.16" ] || continue
    lld="$(dirname "$libdir")/bin/lld"
    [ -x "$lld" ] || continue
    prepend_unique_ld_library_path "$libdir"
    exec "$lld" -flavor gnu "$@"
done
exec "$fallback_lld" -flavor gnu "$@"
"""
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
        try:
            os.chmod(wrapper_path, 0o755)
        except OSError as exc:
            self.output.warning(f"chmod {wrapper_path} skipped: {exc}")

    def build(self):
        cmake = CMake(self)
        with self._ohos_sdk_lld_env():
            cmake.configure()
            self.run(
                f"cmake --build {self._quote(self.build_folder)} --parallel 1",
                env="conanbuild",
                scope="build",
            )

    def test(self):
        test_bin = self._test_binary_path()
        loader_compat_dirs = self._prepare_loader_compat_links(test_bin)
        self._prepare_absolute_needed_links()
        runtime_env = self._runtime_env(loader_compat_dirs)
        with runtime_env.vars(self, scope="run").apply():
            self._log_runtime_environment(test_bin)
            self.run(self._quote(test_bin), env=None, scope="run")
            self.run(
                "ctest --output-on-failure --no-tests=error -j1",
                cwd=self.build_folder,
                env=None,
                scope="run",
            )

    def _runtime_env(self, loader_compat_dirs=None):
        env = VirtualRunEnv(self).environment()
        for folder in reversed(loader_compat_dirs or []):
            env.prepend_path("LD_LIBRARY_PATH", folder)
        for folder in reversed(self._runtime_package_folders()):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(folder, "lib"))
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(folder, "plugins"))
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(folder, "lib", "plugins"))
            env.prepend_path(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(folder, "plugins", "platforms"),
            )
            env.prepend_path("QML2_IMPORT_PATH", os.path.join(folder, "qml"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def _runtime_package_folders(self):
        folders = []
        seen = set()

        def add(dep):
            if not dep or not dep.package_folder:
                return
            folder = os.path.abspath(dep.package_folder)
            if folder not in seen:
                seen.add(folder)
                folders.append(folder)

        tested_name = self.tested_reference_str.split("/")[0]
        for dep_name in self._preferred_dependency_order(tested_name):
            add(self._dependency_by_name(dep_name))
        for dep in self.dependencies.values():
            add(dep)
        return folders

    def _prepend_ohos_sdk_llvm_lib(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return

        llvm_lib = self._usable_ohos_sdk_llvm_libdir(required=True)
        if not llvm_lib:
            return

        parts = [
            part
            for part in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)
            if part
        ]
        normalized_llvm = os.path.normpath(llvm_lib)
        parts = [
            part for part in parts if os.path.normpath(part) != normalized_llvm
        ]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join([llvm_lib] + parts)
        self.output.info(
            "Prepending OHOS SDK LLVM lib to LD_LIBRARY_PATH for lld: "
            f"{llvm_lib}"
        )

    @contextmanager
    def _ohos_sdk_lld_env(self):
        old_ld_path = os.environ.get("LD_LIBRARY_PATH")
        self._prepend_ohos_sdk_llvm_lib()
        try:
            yield
        finally:
            if old_ld_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_ld_path

    def _ohos_sdk_llvm_lib_candidates(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        compiler = (
            compilers.get("cpp")
            or compilers.get("c")
            or os.environ.get("CXX")
            or os.environ.get("CC")
            or "/data/service/hnp/bin/clang++"
        )
        compiler = str(compiler).strip('"')
        candidates = []
        if compiler:
            try:
                resource_dir = subprocess.check_output(
                    [compiler, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                if resource_dir:
                    candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass

            compiler_dir = os.path.dirname(os.path.realpath(compiler))
            derived_lib = os.path.join(os.path.dirname(compiler_dir), "lib")
            candidates.append(derived_lib)

        candidates.append(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        )
        candidates.extend(
            sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        )
        return list(dict.fromkeys(candidates))

    def _usable_ohos_sdk_llvm_libdir(self, required):
        for candidate in self._ohos_sdk_llvm_lib_candidates():
            if not os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                continue
            candidate = os.path.realpath(candidate)
            lld = os.path.join(os.path.dirname(candidate), "bin", "lld")
            probe_env = os.environ.copy()
            old_ld_path = probe_env.get("LD_LIBRARY_PATH", "")
            probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (candidate, old_ld_path) if part
            )
            try:
                probe = subprocess.run(
                    [lld, "-flavor", "gnu", "--version"],
                    env=probe_env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                self.output.warning(f"OHOS SDK lld probe skipped for {lld}: {exc}")
                continue
            if probe.returncode == 0:
                return candidate
            self.output.warning(
                "OHOS SDK lld probe failed for "
                f"{lld}: {probe.stderr.strip()!r}"
            )

        if required:
            raise ConanException(
                "Cannot locate a usable OHOS SDK llvm/lib containing "
                "libxml2.so.16 for lld"
            )
        return ""

    def _test_binary_path(self):
        bindir = self.cpp.build.bindirs[0] if self.cpp.build.bindirs else "."
        if not os.path.isabs(bindir):
            bindir = os.path.join(self.build_folder, bindir)
        return os.path.abspath(os.path.join(bindir, "test_akonadi"))

    def _log_runtime_environment(self, test_bin):
        self.output.info(f"Runtime test binary: {test_bin}")
        tested_name = self.tested_reference_str.split("/")[0]
        tested_dep = self._dependency_by_name(tested_name)
        if tested_dep and tested_dep.package_folder:
            libdir = os.path.join(tested_dep.package_folder, "lib")
            self.output.info(f"Akonadi runtime libdir: {libdir}")
            if os.path.isdir(libdir):
                libs = sorted(
                    name for name in os.listdir(libdir)
                    if name.startswith("libKPim6Akonadi")
                )
                self.output.info(
                    "Akonadi runtime libs: " + (", ".join(libs) or "<none>")
                )
        ld_paths = [
            part for part in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)
            if part
        ]
        self.output.info(
            "LD_LIBRARY_PATH leading entries: "
            + (os.pathsep.join(ld_paths[:8]) or "<empty>")
        )

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

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
        candidates.extend(
            [
                os.path.join("/data/service/hnp/bin", name),
                os.path.join("/storage/Users/currentUser/usr/local/bin", name),
            ]
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _runtime_library_map(self):
        libraries = {}
        for folder in self._runtime_package_folders():
            libdir = os.path.join(folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                path = os.path.join(libdir, name)
                if os.path.isfile(path):
                    libraries.setdefault(name, path)
        return libraries

    def _iter_runtime_elfs(self):
        for folder in self._runtime_package_folders():
            libdir = os.path.join(folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for root, _, files in os.walk(libdir):
                for name in files:
                    path = os.path.join(root, name)
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
            if marker not in line:
                continue
            needed = line.split(marker, 1)[1].split("]", 1)[0]
            entries.append(needed)
        return entries

    @staticmethod
    def _is_conan_cache_needed_path(needed):
        return os.path.isabs(needed) and "/.cache/conan2/" in needed.replace("\\", "/")

    @staticmethod
    def _is_relative_needed_path(needed):
        normalized = needed.replace("\\", "/")
        return not os.path.isabs(needed) and "/" in normalized

    @staticmethod
    def _alias_key(path):
        return os.path.realpath(path)

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

    def _prepare_absolute_needed_links(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        readelf = self._find_ohos_tool("llvm-readelf") or self._find_ohos_tool("readelf")
        if not readelf:
            self.output.warning("llvm-readelf/readelf not found; skip absolute NEEDED links")
            return
        libraries = self._runtime_library_map()
        needed_by_elf = {}
        aliases = {}
        for elf_path in self._iter_runtime_elfs():
            needed_by_elf[elf_path] = self._needed_entries(readelf, elf_path)
            aliases.setdefault(self._alias_key(elf_path), set()).add(elf_path)

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
                aliases.setdefault(self._alias_key(source), set()).add(needed)
                if self._link_needed_library(source, needed):
                    created_absolute += 1

        for elf_path, entries in needed_by_elf.items():
            elf_aliases = set(aliases.get(self._alias_key(elf_path), {elf_path}))
            elf_aliases.add(elf_path)
            for needed in entries:
                if not self._is_relative_needed_path(needed):
                    continue
                source = libraries.get(os.path.basename(needed))
                if not source:
                    missing.append(needed)
                    continue
                targets = {
                    os.path.normpath(os.path.join(os.path.dirname(alias), needed))
                    for alias in elf_aliases
                    if os.path.isabs(alias)
                }
                targets.add(os.path.normpath(os.path.join(self.build_folder, needed)))
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

    def _prepare_loader_compat_links(self, test_bin):
        target_dirs = [
            os.path.dirname(test_bin),
            os.path.normpath(
                os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
            ),
        ]
        for target_dir in target_dirs:
            os.makedirs(target_dir, exist_ok=True)

        tested_name = self.tested_reference_str.split("/")[0]
        tested_dep = self._dependency_by_name(tested_name)
        libdir = (
            os.path.join(tested_dep.package_folder, "lib")
            if tested_dep and tested_dep.package_folder
            else ""
        )
        if not os.path.isdir(libdir):
            return target_dirs
        for name in os.listdir(libdir):
            if not name.startswith("libKPim6Akonadi"):
                continue
            source = os.path.join(libdir, name)
            for target_dir in target_dirs:
                target = os.path.join(target_dir, name)
                if os.path.lexists(target):
                    continue
                try:
                    os.symlink(source, target)
                except OSError:
                    shutil.copy2(source, target)
        return target_dirs
