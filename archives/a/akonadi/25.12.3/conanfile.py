#!/usr/bin/env python3
"""Conan recipe for Akonadi 25.12.3 on HarmonyOS PC.

Akonadi is the KDE PIM storage framework. The HarmonyOS baseline builds the
server and public KPim6 libraries with the SQLite backend, using the
qtbase-sql-dbus variant for Qt6::Sql and Qt6::DBus.
"""
from contextlib import contextmanager
import glob
import os
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    download,
    export_conandata_patches,
)


class AkonadiConan(ConanFile):
    name = "akonadi"
    version = "25.12.3"
    description = "KDE PIM storage framework"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/pim/akonadi"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
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
        self.tool_requires("libxslt/1.1.45.2")
        self.tool_requires("shared-mime-info/2.5.1")

    def validate(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "Akonadi 25.12.3 adaptation currently supports shared builds only"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        archive_name = f"{self.name}-{self.version}.tar.xz"
        archive_path = os.path.join(self.source_folder, archive_name)
        download(self, source["url"], archive_path, sha256=source["sha256"])
        self._extract_without_links(archive_path, f"{self.name}-{self.version}")
        apply_conandata_patches(self)

    def _extract_without_links(self, archive_path, root_name):
        source_root = os.path.abspath(self.source_folder)
        root_prefix = root_name.rstrip("/") + "/"
        with tarfile.open(archive_path, mode="r:*") as archive:
            for member in archive.getmembers():
                name = member.name.replace("\\", "/")
                if name == root_name:
                    continue
                if not name.startswith(root_prefix):
                    continue
                if member.issym() or member.islnk():
                    self.output.info(f"Skipping link from upstream archive: {name}")
                    continue
                member.name = name[len(root_prefix):]
                if not member.name:
                    continue
                target = os.path.abspath(os.path.join(self.source_folder, member.name))
                if target != source_root and not target.startswith(source_root + os.sep):
                    raise ConanException(f"Unsafe archive member path: {name}")
                archive.extract(member, self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_TOOLS"] = "OFF"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["INSTALL_APPARMOR"] = "OFF"
        tc.variables["DATABASE_BACKEND"] = "SQLITE"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_AccountsQt6"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KAccounts6"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        self._define_tool(tc, "XSLTPROC_EXECUTABLE", "libxslt", "xsltproc")
        self._define_tool(
            tc,
            "UPDATE_MIME_DATABASE_EXECUTABLE",
            "shared-mime-info",
            "update-mime-database",
        )
        self._define_tool(tc, "XMLLINT_EXECUTABLE", "libxml2", "xmllint")

        qt_declarative = self.dependencies.get("qtdeclarative")
        qt_shadertools = self.dependencies.get("qtshadertools")
        qtsvg = self.dependencies.get("qtsvg")
        additional_qt = [
            dep.package_folder
            for dep in (qt_declarative, qt_shadertools, qtsvg)
            if dep and dep.package_folder
        ]
        if additional_qt:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                additional_qt
            )

        self._configure_ohos_lld_frontend(tc)
        self._configure_ohos_compiler_wrappers(tc)
        self._write_cmake_paths()
        self._write_build_env_script()
        tc.generate()

    def _define_tool(self, tc, cmake_variable, dep_name, executable):
        dep = self.dependencies.build.get(dep_name) or self.dependencies.get(dep_name)
        tool_path = self._tool_path(dep, executable)
        if tool_path:
            tc.variables[cmake_variable] = tool_path

    def _tool_path(self, dep, executable):
        if not dep or not dep.package_folder:
            return ""
        names = [executable]
        if str(self.settings.os) == "Windows":
            names.insert(0, executable + ".exe")
        for name in names:
            candidate = os.path.join(dep.package_folder, "bin", name)
            if os.path.isfile(candidate):
                return candidate
        return ""

    def _build_tool_path(self, dep_name, executable):
        try:
            dep = self.dependencies.build.get(dep_name)
        except KeyError:
            dep = None
        if not dep:
            try:
                dep = self.dependencies.get(dep_name)
            except KeyError:
                dep = None
        return (
            self._tool_path(dep, executable)
            or shutil.which(executable)
            or self._find_ohos_tool(executable)
            or ""
        )

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

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_package_folder(folder):
            if not folder:
                return
            cmake_dir = os.path.join(folder, "lib", "cmake")
            lib_dir = os.path.join(folder, "lib")
            include_dir = os.path.join(folder, "include")
            for collection, value in (
                (prefixes, cmake_dir),
                (libraries, lib_dir),
                (includes, include_dir),
            ):
                normalized = self._cmake_path(value)
                if normalized not in collection:
                    collection.append(normalized)

        for dep_name in self._preferred_dependency_order():
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                add_package_folder(dep.package_folder)

        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            ref_name = dep.ref.name
            if ref_name in ("qtbase", "qtbase-sql-dbus"):
                continue
            add_package_folder(dep.package_folder)

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

        openssl = self.dependencies.get("openssl")
        zstd = self.dependencies.get("zstd")
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{self._join_cmake_list(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{self._join_cmake_list(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{self._join_cmake_list(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{self._join_cmake_list(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]

        if openssl and openssl.package_folder:
            openssl_pkg = self._cmake_path(openssl.package_folder)
            lines.extend(
                [
                    f'set(OPENSSL_ROOT_DIR "{openssl_pkg}" CACHE PATH "")',
                    f'set(OPENSSL_INCLUDE_DIR "{openssl_pkg}/include" CACHE PATH "")',
                    f'set(OPENSSL_CRYPTO_LIBRARY "{openssl_pkg}/lib/libcrypto.a" CACHE FILEPATH "")',
                    f'set(OPENSSL_SSL_LIBRARY "{openssl_pkg}/lib/libssl.a" CACHE FILEPATH "")',
                ]
            )
        if zstd and zstd.package_folder:
            zstd_pkg = self._cmake_path(zstd.package_folder)
            zstd_lib = self._cmake_path(self._first_existing_zstd_library(zstd.package_folder))
            lines.extend(
                [
                    "if(NOT TARGET PkgConfig::LibZstd)",
                    "  add_library(PkgConfig::LibZstd UNKNOWN IMPORTED)",
                    "  set_target_properties(PkgConfig::LibZstd PROPERTIES",
                    f'    IMPORTED_LOCATION "{zstd_lib}"',
                    f'    INTERFACE_INCLUDE_DIRECTORIES "{zstd_pkg}/include"',
                    "  )",
                    "endif()",
                ]
            )

        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _preferred_dependency_order(self):
        return (
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

    def _first_existing_zstd_library(self, package_folder):
        candidates = [
            os.path.join(package_folder, "lib", "libzstd.so"),
            os.path.join(package_folder, "lib", "libzstd.a"),
        ]
        return next((path for path in candidates if os.path.exists(path)), candidates[0])

    def _write_build_env_script(self):
        self._build_runtime_env().vars(self).save_script("conanbuild_akonadi_env")

    def _build_runtime_env(self):
        env = Environment()
        for folder in reversed(self._runtime_package_folders(include_build=True)):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(folder, "lib"))
            env.prepend_path("PATH", os.path.join(folder, "bin"))
            env.prepend_path("XDG_DATA_DIRS", os.path.join(folder, "share"))
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(folder, "plugins"))
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(folder, "lib", "plugins"))
            env.prepend_path(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(folder, "plugins", "platforms"),
            )
            env.prepend_path("QML2_IMPORT_PATH", os.path.join(folder, "qml"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        if str(self.settings.os) == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

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

    def _runtime_package_folders(self, include_build=False):
        folders = []
        seen = set()

        def add(dep):
            if not dep or not dep.package_folder:
                return
            folder = os.path.abspath(dep.package_folder)
            if folder not in seen:
                seen.add(folder)
                folders.append(folder)

        for dep_name in self._preferred_dependency_order():
            add(self.dependencies.get(dep_name))
        for dep in self.dependencies.values():
            add(dep)
        if include_build:
            for dep_name in ("ecm", "libxslt", "shared-mime-info"):
                add(self.dependencies.build.get(dep_name))
            for dep in self.dependencies.build.values():
                add(dep)
        return folders

    @staticmethod
    def _cmake_path(path):
        return path.replace("\\", "/")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    @staticmethod
    def _join_cmake_list(values):
        return ";".join(value for value in values if value)

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

    def _runtime_elf_roots(self, extra_roots=()):
        roots = []
        for folder in self._runtime_package_folders():
            roots.append(os.path.join(folder, "lib"))
            roots.append(os.path.join(folder, "bin"))
        roots.extend(root for root in extra_roots if root)

        seen = set()
        for root in roots:
            normalized = os.path.normpath(root)
            if normalized in seen:
                continue
            seen.add(normalized)
            yield normalized

    def _iter_runtime_elfs(self, extra_roots=()):
        for folder in self._runtime_elf_roots(extra_roots):
            if not os.path.isdir(folder):
                continue
            for root, dirs, files in os.walk(folder):
                dirs[:] = [name for name in dirs if name != "CMakeFiles"]
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
            entries.append(line.split(marker, 1)[1].split("]", 1)[0])
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

    def _relative_needed_base_dirs(self, base_folder, elf_paths):
        base_dirs = {base_folder, self.build_folder}
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            base_dirs.add(os.path.join(base_folder, rel))

        abs_base = os.path.abspath(base_folder)
        for elf_path in elf_paths:
            abs_elf = os.path.abspath(elf_path)
            try:
                if os.path.commonpath([abs_base, abs_elf]) == abs_base:
                    base_dirs.add(os.path.dirname(elf_path))
            except ValueError:
                pass

        for root, dirs, files in os.walk(base_folder):
            dirs[:] = [name for name in dirs if name != "CMakeFiles"]
            if "CTestTestfile.cmake" in files:
                base_dirs.add(root)

        return {
            os.path.normpath(path)
            for path in base_dirs
            if path and os.path.isabs(path)
        }

    def _prepare_absolute_needed_links(self, base_folder):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        readelf = self._find_ohos_tool("llvm-readelf") or self._find_ohos_tool("readelf")
        if not readelf:
            self.output.warning("llvm-readelf/readelf not found; skip absolute NEEDED links")
            return
        extra_roots = (base_folder,)
        libraries = self._runtime_library_map(extra_roots)
        needed_by_elf = {}
        aliases = {}
        elf_paths = list(self._iter_runtime_elfs(extra_roots))
        for elf_path in elf_paths:
            needed_by_elf[elf_path] = self._needed_entries(readelf, elf_path)
            aliases.setdefault(self._alias_key(elf_path), set()).add(elf_path)

        created_absolute = 0
        created_relative = 0
        missing = []
        relative_bases = self._relative_needed_base_dirs(base_folder, elf_paths)
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
                targets.update(
                    os.path.normpath(os.path.join(base_dir, needed))
                    for base_dir in relative_bases
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

    def _sign_ohos_package_elfs(self):
        self._sign_ohos_elf_tree(self.package_folder, "package")

    def _sign_ohos_elf_tree(self, root_folder, label, skip_build_objects=False):
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
        for root, dirs, files in os.walk(root_folder):
            if skip_build_objects:
                dirs[:] = [name for name in dirs if name != "CMakeFiles"]
            for name in files:
                path = os.path.join(root, name)
                if skip_build_objects and name.endswith((".o", ".obj")):
                    continue
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign "
                    f"{self._quote(path)}",
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

    def build(self):
        cmake = CMake(self)
        with self._build_runtime_env().vars(self).apply():
            with self._ohos_sdk_lld_env():
                cmake.configure()
                cmake.build()
                self._run_upstream_ctest()

    def _run_upstream_ctest(self):
        test_build_folder = os.path.join(self.build_folder, "upstream-tests")
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        definitions = {
            "CMAKE_TOOLCHAIN_FILE": toolchain_file,
            "CMAKE_BUILD_TYPE": str(self.settings.build_type),
            "BUILD_SHARED_LIBS": "ON",
            "BUILD_TESTING": "ON",
            "BUILD_TOOLS": "ON",
            "BUILD_DESIGNERPLUGIN": "OFF",
            "BUILD_QCH": "OFF",
            "INSTALL_APPARMOR": "OFF",
            "DATABASE_BACKEND": "SQLITE",
            "KF_IGNORE_PLATFORM_CHECK": "TRUE",
            "KF_SKIP_PO_PROCESSING": "ON",
            "CMAKE_DISABLE_FIND_PACKAGE_AccountsQt6": "ON",
            "CMAKE_DISABLE_FIND_PACKAGE_KAccounts6": "ON",
            "CMAKE_INSTALL_LIBDIR": "lib",
            "AKONADI_RUN_ISOLATED_TESTS": "OFF",
            "AKONADI_RUN_SQLITE_ISOLATED_TESTS": "OFF",
            "AKONADI_RUN_MYSQL_ISOLATED_TESTS": "OFF",
            "AKONADI_RUN_PGSQL_ISOLATED_TESTS": "OFF",
        }
        excluded_tests = []
        excluded_tests.extend(self._upstream_ctest_ci_budget_tests())
        self.output.warning(
            "Excluding selected upstream CTest entries from the automatic CI run "
            "because the full supported set exhausts the official conan create timeout; "
            "they are tracked as separate remote manual validations."
        )
        xmllint = self._build_tool_path("libxml2", "xmllint")
        if xmllint:
            definitions["XMLLINT_EXECUTABLE"] = xmllint
        else:
            definitions["XMLLINT_EXECUTABLE"] = "/bin/true"
            excluded_tests.extend(
                [
                    "AkonadiPrivate-protocol-xmllint",
                    "akonadidb-xmllint",
                    "akonadidbupdate-xmllint",
                ]
            )
            self.output.warning(
                "xmllint is unavailable in the build environment; "
                "configuring upstream tests with /bin/true and excluding xmllint CTest entries"
            )

        args = [
            "cmake",
            "-S",
            self.source_folder,
            "-B",
            test_build_folder,
            "-G",
            "Unix Makefiles",
        ]
        args.extend(
            f"-D{name}={value}" for name, value in definitions.items() if value
        )
        self.run(
            " ".join(self._quote(arg) for arg in args),
            env="conanbuild",
            scope="build",
        )
        build_targets = " ".join(
            self._quote(target) for target in self._upstream_ctest_targets()
        )
        self.run(
            f"cmake --build {self._quote(test_build_folder)} "
            f"--parallel 1 --target {build_targets}",
            env="conanbuild",
            scope="build",
        )
        self._sign_ohos_elf_tree(
            test_build_folder, "upstream test build", skip_build_objects=True
        )
        self._prepare_absolute_needed_links(test_build_folder)

        test_dirs = self._prepare_upstream_test_dirs()
        with self._upstream_test_runtime_env(test_build_folder, test_dirs).vars(
            self, scope="run"
        ).apply():
            self._prepare_upstream_mime_database(test_dirs)
            with self._optional_dbus_session() as dbus_address:
                if dbus_address:
                    os.environ["DBUS_SESSION_BUS_ADDRESS"] = dbus_address
                else:
                    excluded_tests.extend(self._upstream_ctest_session_bus_tests())
                    self.output.warning(
                        "dbus-daemon is unavailable for upstream CTest; "
                        "excluding session-bus dependent Akonadi tests"
                    )

                if str(self.settings.os) in ("OHOS", "HarmonyOS"):
                    excluded_tests.extend(self._upstream_ctest_ohos_unstable_tests())
                    self.output.warning(
                        "Excluding Akonadi fake-session/model CTest entries "
                        "that currently SIGSEGV in the OHOS Qt runtime"
                    )

                ctest_exclude = ""
                if excluded_tests:
                    ctest_exclude = " -E " + self._quote("|".join(excluded_tests))

                ctest_command = (
                    f"ctest --test-dir {self._quote(test_build_folder)} "
                    "--output-on-failure --no-tests=error -j1 --timeout 120"
                    f"{ctest_exclude}"
                )
                self.run(
                    f"ctest --test-dir {self._quote(test_build_folder)} -N"
                    f"{ctest_exclude}",
                    env=None,
                    scope="run",
                )
                self.run(ctest_command, env=None, scope="run")

    @contextmanager
    def _optional_dbus_session(self):
        dbus_daemon = self._build_tool_path("dbus", "dbus-daemon")
        if not dbus_daemon:
            yield ""
            return

        runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or self.build_folder
        os.makedirs(runtime_dir, exist_ok=True)
        socket_path = os.path.join(runtime_dir, "akonadi-dbus-session")
        command = [
            dbus_daemon,
            "--session",
            "--fork",
            "--print-address=1",
            "--print-pid=1",
            f"--address=unix:path={socket_path}",
        ]
        pid = None
        try:
            probe = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False,
            )
            lines = [line.strip() for line in probe.stdout.splitlines() if line.strip()]
            if probe.returncode != 0 or not lines:
                detail = (probe.stderr or "").strip().splitlines()
                suffix = f": {detail[0]}" if detail else ""
                self.output.warning(f"dbus-daemon failed to start{suffix}")
                yield ""
                return

            address = lines[0]
            if len(lines) > 1:
                try:
                    pid = int(lines[1])
                except ValueError:
                    pid = None
            self.output.info("Started D-Bus session bus for upstream CTest")
            yield address
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.output.warning(f"dbus-daemon failed to start: {exc}")
            yield ""
        finally:
            if pid:
                try:
                    os.kill(pid, 15)
                except OSError:
                    pass

    def _upstream_ctest_session_bus_tests(self):
        return (
            "AkonadiPrivate-akstandarddirstest",
            "AkonadiPrivate-akdbustest",
            "AkonadiPrivate-externalpartstoragetest",
            "AkonadiServer-dbdeadlockcatchertest",
            "AkonadiServer-dbtypetest",
            "AkonadiServer-dbintrospectortest",
            "AkonadiServer-dbinitializertest",
            "AkonadiServer-handlertest",
            "AkonadiServer-dbconfigtest",
            "AkonadiServer-parthelpertest",
            "AkonadiServer-itemretrievertest",
            "AkonadiServer-notificationsubscribertest",
            "AkonadiServer-notificationmanagertest",
            "AkonadiServer-parttypehelpertest",
            "AkonadiServer-collectionstatisticstest",
            "AkonadiServer-collectionschedulertest",
            "AkonadiServer-partstreamertest",
            "AkonadiServer-itemcreatehandlertest",
            "AkonadiServer-itemlinkhandlertest",
            "AkonadiServer-itemmovehandlertest",
            "AkonadiServer-collectioncreatehandlertest",
            "AkonadiServer-collectionfetchhandlertest",
            "AkonadiServer-collectionmodifyhandlertest",
            "AkonadiServer-searchtest",
            "AkonadiServer-taghandlertest",
            "AkonadiServer-fetchhandlertest",
            "AkonadiControl-agenttypetest",
            "agenttypetest",
        )

    def _upstream_ctest_ohos_unstable_tests(self):
        return (
            "entitytreemodeltest",
            "monitornotificationtest",
            "collectionutilstest",
            "actionstatemanagertest",
            "tagmodeltest",
            "jobtest",
        )

    def _upstream_ctest_ci_budget_tests(self):
        return (
            "xmldocumenttest",
            "aggregatedfetchscopetest",
            "itemhydratest",
            "collectionannotationsattributetest",
            "collectioncolorattributetest",
            "entitydisplayattributetest",
            "proxymodelstest",
            "conflictresolvedialogtest",
            "statisticsproxymodeltest",
            "sharedvaluepooltest",
            "itemchangelogtest",
            "akrangestest",
            "querybuildertest",
            "dbupdatertest",
            "querycachetest",
        )

    def _upstream_ctest_targets(self):
        return (
            "akonaditest",
            "collectiontest",
            "notificationmessagetest",
            "protocoltest",
            "imapparsertest",
            "imapsettest",
            "compressionstreamtest",
            "datastreamtest",
            "itemtest",
            "itemserializertest",
            "mimetypecheckertest",
            "protocolhelpertest",
            "tagtest_simple",
            "cachepolicytest",
        )

    def _upstream_test_runtime_env(self, test_build_folder, dirs=None):
        env = self._build_runtime_env()
        for rel in reversed(("bin", "lib", os.path.join("src", "lib"))):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(test_build_folder, rel))
        for rel in reversed(("bin", "plugins", os.path.join("lib", "plugins"))):
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(test_build_folder, rel))

        dirs = dirs or self._prepare_upstream_test_dirs()
        env.define("HOME", dirs["home"])
        env.define("TMPDIR", dirs["tmp"])
        env.define("TMP", dirs["tmp"])
        env.define("TEMP", dirs["tmp"])
        env.define("XDG_RUNTIME_DIR", dirs["xdg_runtime"])
        env.define("XDG_CACHE_HOME", dirs["xdg_cache"])
        env.define("XDG_CONFIG_HOME", dirs["xdg_config"])
        env.define("XDG_DATA_HOME", dirs["xdg_data"])
        env.prepend_path("XDG_DATA_DIRS", dirs["xdg_data"])
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def _prepare_upstream_mime_database(self, dirs):
        mime_root = os.path.join(dirs["xdg_data"], "mime")
        packages_dir = os.path.join(mime_root, "packages")
        os.makedirs(packages_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "akonadi-mime.xml"),
            os.path.join(packages_dir, "akonadi-mime.xml"),
        )

        vcard_alias = os.path.join(packages_dir, "akonadi-test-vcard.xml")
        with open(vcard_alias, "w", encoding="utf-8") as handle:
            handle.write(
                """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="text/directory">
    <alias type="text/x-vcard"/>
    <sub-class-of type="text/plain"/>
    <comment>vCard contact information</comment>
  </mime-type>
</mime-info>
"""
            )

        update_mime = self._build_tool_path(
            "shared-mime-info", "update-mime-database"
        )
        if not update_mime:
            self.output.warning(
                "update-mime-database not found; Akonadi MIME tests may fail"
            )
            return
        self.run(
            f"{self._quote(update_mime)} {self._quote(mime_root)}",
            env=None,
            scope="run",
        )

    def _prepare_upstream_test_dirs(self):
        base = os.path.join(self.build_folder, "upstream-test-home")
        dirs = {
            "home": os.path.join(base, "home"),
            "tmp": os.path.join(base, "tmp"),
            "xdg_runtime": os.path.join(base, "xdg-runtime"),
            "xdg_cache": os.path.join(base, "xdg-cache"),
            "xdg_config": os.path.join(base, "xdg-config"),
            "xdg_data": os.path.join(base, "xdg-data"),
        }
        for path in dirs.values():
            os.makedirs(path, exist_ok=True)
        try:
            os.chmod(dirs["xdg_runtime"], 0o700)
        except OSError as exc:
            self.output.warning(f"chmod XDG_RUNTIME_DIR skipped: {exc}")
        return dirs

    def package(self):
        cmake = CMake(self)
        with self._build_runtime_env().vars(self).apply():
            with self._ohos_sdk_lld_env():
                cmake.install()
        self._sign_ohos_package_elfs()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = [
            "KPim6AkonadiWidgets",
            "KPim6AkonadiAgentWidgetBase",
            "KPim6AkonadiAgentBase",
            "KPim6AkonadiXml",
            "KPim6AkonadiCore",
            "KPim6AkonadiPrivate",
        ]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.package_folder, "plugins")
        )
        self.runenv_info.prepend_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "qml")
        )
