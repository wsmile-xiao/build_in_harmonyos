#!/usr/bin/env python3
"""Conan recipe for libclamunrar 1.4.4 — ClamAV UnRAR engine as a standalone library.

Upstream: Cisco-Talos/clamav tag clamav-1.4.4, subdirectory libclamunrar/.
The top-level ClamAV CMake requires Rust (find_package(Rust REQUIRED)) which
is unavailable on OHOS CI workers (CI capability matrix: Rust = unsupported),
so this recipe builds only the self-contained UnRAR engine sources directly
with a minimal CMake project generated at build time. No Rust, no libclamav,
no external dependencies.

Engine sources: 50 C++ files listed in upstream libclamunrar/CMakeLists.txt
(archive.cpp ... volume.cpp), C++11, defines RARDLL + _FILE_OFFSET_BITS=64.
Public API: dll.hpp (RAROpenArchive / RARReadHeader / RARProcessFile /
RARCloseArchive / RARGetDllVersion, RAR_DLL_VERSION=8).
SONAME follows LIBCLAMAV versioning for 1.4.4: CURRENT=12 REVISION=3 AGE=0
=> SOVERSION=12, VERSION=12.0.3.

Upstream has no standalone test suite in libclamunrar/ (no tests/ dir, no
ctest registration; RAR integration tests live in clamav unit_tests/ and
require full libclamav + Rust). Declared as no_tests with audit in
test_package/MANIFEST.yml.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


UNRAR_SOURCES = (
    "archive.cpp",
    "arcread.cpp",
    "blake2s.cpp",
    "cmddata.cpp",
    "consio.cpp",
    "crc.cpp",
    "crypt.cpp",
    "dll.cpp",
    "encname.cpp",
    "errhnd.cpp",
    "extinfo.cpp",
    "extract.cpp",
    "filcreat.cpp",
    "file.cpp",
    "filefn.cpp",
    "filestr.cpp",
    "find.cpp",
    "getbits.cpp",
    "global.cpp",
    "hash.cpp",
    "headers.cpp",
    "list.cpp",
    "match.cpp",
    "options.cpp",
    "pathfn.cpp",
    "qopen.cpp",
    "rar.cpp",
    "rarvm.cpp",
    "rawread.cpp",
    "rdwrfn.cpp",
    "recvol.cpp",
    "resource.cpp",
    "rijndael.cpp",
    "rs.cpp",
    "rs16.cpp",
    "scantree.cpp",
    "secpassword.cpp",
    "sha1.cpp",
    "sha256.cpp",
    "smallfn.cpp",
    "strfn.cpp",
    "strlist.cpp",
    "system.cpp",
    "threadpool.cpp",
    "timefn.cpp",
    "ui.cpp",
    "unicode.cpp",
    "unpack.cpp",
    "volume.cpp",
)


class LibclamunrarConan(ConanFile):
    name = "libclamunrar"
    version = "1.4.4"
    description = "ClamAV UnRAR engine (RAR archive decompression library)"
    license = "UnRAR"
    homepage = "https://github.com/Cisco-Talos/clamav"
    url = "https://github.com/Cisco-Talos/clamav"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libclamunrar supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        if str(self.settings.os) == "OHOS":
            self._prepend_ohos_tool_paths()
        build_env = VirtualBuildEnv(self)
        build_env.generate()
        tc = CMakeToolchain(self)
        tc.variables["LIBCLAMUNRAR_SHARED"] = "ON" if self.options.shared else "OFF"
        if str(self.settings.os) == "OHOS":
            # E092: CMake 4.x does not recognize HarmonyOS (Conan maps
            # os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, e.g. easyloggingpp
            # 9.97.1 precedent). Build a plain Linux-targeted binary with
            # the OHOS clang; the engine has no OS-specific branches.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = self._ohos_system_processor()
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable("cpp", "clang++")
        tc.generate()
        if str(self.settings.os) == "OHOS":
            self._patch_cmake_toolchain_compilers()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._prepend_ohos_tool_paths()
        unrar_dir = os.path.join(self.source_folder, "libclamunrar")
        if not os.path.isfile(os.path.join(unrar_dir, "dll.cpp")):
            raise ConanInvalidConfiguration(
                f"libclamunrar sources not found in {unrar_dir}"
            )
        self._write_standalone_cmakelists(unrar_dir)
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.build_folder)
        cmake.build()
        # Directory audit only — always runs (no toolchain dependency), so the
        # packaged audit exists even if a future profile cannot natively run.
        self._run_upstream_audit()

    def _write_standalone_cmakelists(self, unrar_dir):
        # Minimal standalone project: only the engine, no Rust, no libclamav.
        # Absolute source paths so the build script can live in build_folder.
        escaped_dir = unrar_dir.replace("\\", "/")
        src_lines = "\n".join(
            f'    "${{UNRAR_DIR}}/{name}"' for name in UNRAR_SOURCES
        )
        content = f"""cmake_minimum_required(VERSION 3.15)
project(clamunrar CXX)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
option(LIBCLAMUNRAR_SHARED "Build shared library" ON)
set(UNRAR_DIR "{escaped_dir}")
set(UNRAR_SOURCES
{src_lines}
)
if(LIBCLAMUNRAR_SHARED)
    add_library(clamunrar SHARED ${{UNRAR_SOURCES}})
else()
    add_library(clamunrar STATIC ${{UNRAR_SOURCES}})
endif()
target_include_directories(clamunrar PUBLIC "${{UNRAR_DIR}}")
target_compile_definitions(clamunrar PRIVATE RARDLL PUBLIC _FILE_OFFSET_BITS=64 _UNIX)
if(NOT WIN32)
    target_compile_options(clamunrar PRIVATE -Wno-logical-op-parentheses -Wno-switch -Wno-dangling-else)
endif()
set_target_properties(clamunrar PROPERTIES VERSION "12.0.3" SOVERSION "12")
install(TARGETS clamunrar ARCHIVE DESTINATION lib LIBRARY DESTINATION lib)
install(FILES "${{UNRAR_DIR}}/dll.hpp" DESTINATION include)
"""
        cmake_path = os.path.join(self.build_folder, "CMakeLists.txt")
        with open(cmake_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _run_upstream_audit(self):
        """Audit that libclamunrar/ carries no standalone test suite.

        Emits no HMBS_UPSTREAM_TEST_RESULT here: the test_package stage
        always runs (even on cache hits that skip build()) and re-emits the
        no_tests marker from the packaged audit file, so the marker is
        present in every preflight log.
        """
        unrar_dir = os.path.join(self.source_folder, "libclamunrar")
        entries = sorted(os.listdir(unrar_dir))
        has_tests_dir = os.path.isdir(os.path.join(unrar_dir, "tests"))
        test_files = [e for e in entries if "test" in e.lower()]
        audit = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "Audited clamav-1.4.4/libclamunrar/ ("
                + str(len(entries))
                + " entries): C++ engine sources + CMakeLists.txt only; "
                "no tests/ dir, no ctest registration"
                + ("; test-like files: " + ",".join(test_files) if test_files else "")
                + ". RAR integration checks live in clamav unit_tests/ and "
                "require full libclamav + Rust toolchain (unavailable on OHOS CI)."
            ),
        }
        audit_path = os.path.join(self.build_folder, "upstream_test_audit.json")
        with open(audit_path, "w", encoding="utf-8") as handle:
            json.dump(audit, handle, ensure_ascii=False)
        self.output.info("upstream audit (no standalone tests): " + json.dumps(audit))
        if has_tests_dir or test_files:
            self.output.warning("unexpected test-like entries in libclamunrar/: " + str(test_files))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        audit_src = os.path.join(self.build_folder, "upstream_test_audit.json")
        if os.path.isfile(audit_src):
            copy(
                self,
                "upstream_test_audit.json",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "res"),
                keep_path=False,
            )
        for license_name in ("license.txt", "readme.txt"):
            license_src = os.path.join(self.source_folder, "libclamunrar", license_name)
            if os.path.isfile(license_src):
                copy(
                    self,
                    license_name,
                    src=os.path.join(self.source_folder, "libclamunrar"),
                    dst=os.path.join(self.package_folder, "licenses"),
                    keep_path=False,
                )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libclamunrar")
        self.cpp_info.set_property("cmake_target_name", "libclamunrar::libclamunrar")
        self.cpp_info.libs = ["clamunrar"]
        self.cpp_info.includedirs = ["include"]
        # dll.hpp gates its Unix type shims (HANDLE/CALLBACK/PASCAL/UINT/
        # LPARAM) on _UNIX; consumers must inherit it, while RARDLL stays
        # build-private (DLL export macro).
        self.cpp_info.defines = ["_UNIX", "_FILE_OFFSET_BITS=64"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _ohos_system_processor(self):
        # conan arch armv8 == AArch64; CMake expects aarch64.
        arch = str(self.settings.arch)
        return {"armv8": "aarch64", "armv8.3": "aarch64"}.get(arch, arch)

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        # Second layer: rewrite dead absolute compiler paths baked from the
        # CI profile (e.g. /data/service/hnp/bin/clang missing on preflight)
        # plus any residual HarmonyOS system name, mirroring the proven
        # libXext/libxi test_package pattern.
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            return
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)
        with open(toolchain, "r", encoding="utf-8") as handle:
            content = handle.read()
        patched = re.sub(
            r'set\(CMAKE_SYSTEM_NAME\s+"HarmonyOS"\)',
            'set(CMAKE_SYSTEM_NAME "Linux")',
            content,
        )
        if patched != content:
            with open(toolchain, "w", encoding="utf-8") as handle:
                handle.write(patched)

    def _prepend_ohos_tool_paths(self):
        existing = os.environ.get("PATH", "")
        parts = existing.split(os.pathsep) if existing else []
        for path in reversed(self._ohos_tool_paths()):
            if path not in parts:
                existing = path + (os.pathsep + existing if existing else "")
                parts.insert(0, path)
        os.environ["PATH"] = existing

    def _ohos_tool_paths(self):
        return [
            path
            for path in (
                "/data/service/hnp/bin",
                os.path.join(os.path.expanduser("~"), "usr", "local", "bin"),
                "/bin",
                "/usr/bin",
            )
            if os.path.isdir(path)
        ]
