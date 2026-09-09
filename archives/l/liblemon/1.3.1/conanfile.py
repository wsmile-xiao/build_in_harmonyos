#!/usr/bin/env python3
"""Conan recipe for LEMON graph algorithms library 1.3.1."""

import os
import re
import shlex
import shutil
import subprocess
import hashlib
import tarfile
from pathlib import Path
from pathlib import PurePosixPath

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LiblemonConan(ConanFile):
    name = "liblemon"
    version = "1.3.1"
    description = "Library for Efficient Modeling and Optimization in Networks"
    license = "BSL-1.0"
    homepage = "https://lemon.cs.elte.hu/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    _upstream_tests = (
        "adaptors_test",
        "arc_look_up_test",
        "bellman_ford_test",
        "bfs_test",
        "bpgraph_test",
        "circulation_test",
        "connectivity_test",
        "counter_test",
        "dfs_test",
        "digraph_test",
        "dijkstra_test",
        "dim_test",
        "edge_set_test",
        "error_test",
        "euler_test",
        "fractional_matching_test",
        "gomory_hu_test",
        "graph_copy_test",
        "graph_test",
        "graph_utils_test",
        "hao_orlin_test",
        "heap_test",
        "kruskal_test",
        "lgf_reader_writer_test",
        "lgf_test",
        "maps_test",
        "matching_test",
        "max_cardinality_search_test",
        "max_clique_test",
        "max_flow_test",
        "min_cost_arborescence_test",
        "min_cost_flow_test",
        "min_mean_cycle_test",
        "nagamochi_ibaraki_test",
        "path_test",
        "planarity_test",
        "radix_sort_test",
        "random_test",
        "suurballe_test",
        "time_measure_test",
        "tsp_test",
        "unionfind_test",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        frozen_archive = self.conf.get(
            "user.ohpcd:frozen_source_archive", default="", check_type=str
        )
        if frozen_archive:
            self._extract_frozen_source(Path(frozen_archive))
            return
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.cache_variables["LEMON_ENABLE_GLPK"] = False
        toolchain.cache_variables["LEMON_ENABLE_ILOG"] = False
        toolchain.cache_variables["LEMON_ENABLE_COIN"] = False
        toolchain.cache_variables["LEMON_ENABLE_SOPLEX"] = False
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if str(self.settings.os) == "OHOS":
            soname_flag = "-Wl,-soname,liblemon.so"
            toolchain.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = soname_flag
            toolchain.cache_variables["CMAKE_SHARED_LINKER_FLAGS_RELEASE"] = soname_flag
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["LEMON_THREADING"] = "Pthread"
        if self.options.get_safe("fPIC") is not None:
            toolchain.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
                self.options.fPIC
            )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._build_upstream_tests()
        if str(self.settings.os) == "OHOS":
            self._sign_upstream_test_closure()
        self._run_upstream_tests()

    def package(self):
        CMake(self).install()
        self._relocate_metadata()
        if str(self.settings.os) == "OHOS":
            for name in ("lgf-gen", "dimacs-to-lgf", "dimacs-solver"):
                self._sign_elf(Path(self.package_folder, "bin", name))
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = [self._library_stem()]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.builddirs = ["share/lemon/cmake"]
        self.cpp_info.set_property("cmake_file_name", "LEMON")
        self.cpp_info.set_property("cmake_target_name", "LEMON::lemon")
        self.cpp_info.set_property("pkg_config_name", "lemon")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    def _build_upstream_tests(self):
        cmake = shutil.which("cmake")
        if not cmake:
            raise ConanInvalidConfiguration("cmake executable is unavailable")
        command = [
            cmake,
            "--build",
            self.build_folder,
            "--target",
            *self._upstream_tests,
            "--parallel",
            "2",
        ]
        self.run(self._serialize(command), env="conanbuild")

    def _extract_frozen_source(self, archive_path):
        if not archive_path.is_file():
            raise ConanInvalidConfiguration(
                f"frozen source archive is missing: {archive_path}"
            )
        expected_sha256 = self.conan_data["sources"]["sha256"]
        actual_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise ConanInvalidConfiguration(
                "frozen source archive SHA-256 mismatch: "
                f"{actual_sha256} != {expected_sha256}"
            )

        extraction_root = Path(self.source_folder, ".frozen-source-extract")
        if extraction_root.exists():
            raise ConanInvalidConfiguration(
                f"frozen source staging path already exists: {extraction_root}"
            )
        extraction_root.mkdir()
        try:
            with tarfile.open(archive_path, "r:gz") as archive:
                members = archive.getmembers()
                top_roots = set()
                for member in members:
                    path = PurePosixPath(member.name)
                    if path.is_absolute() or ".." in path.parts or member.isdev():
                        raise ConanInvalidConfiguration(
                            f"unsafe frozen source archive member: {member.name}"
                        )
                    if path.parts and path.parts[0] not in ("", "."):
                        top_roots.add(path.parts[0])
                if top_roots != {"lemon-1.3.1"}:
                    raise ConanInvalidConfiguration(
                        f"unexpected frozen source archive roots: {sorted(top_roots)}"
                    )
                archive.extractall(extraction_root, filter="data")

            extracted_source = extraction_root / "lemon-1.3.1"
            if not extracted_source.is_dir():
                raise ConanInvalidConfiguration(
                    "frozen source archive did not create lemon-1.3.1"
                )
            for item in extracted_source.iterdir():
                destination = Path(self.source_folder, item.name)
                if destination.exists() or destination.is_symlink():
                    raise ConanInvalidConfiguration(
                        f"source destination already exists: {destination}"
                    )
                shutil.move(str(item), destination)
            extracted_source.rmdir()
        finally:
            if extraction_root.exists():
                shutil.rmtree(extraction_root)

    def _run_upstream_tests(self):
        ctest = shutil.which("ctest")
        if not ctest:
            raise ConanInvalidConfiguration("ctest executable is unavailable")
        environment = Environment()
        if self.options.shared:
            environment.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, "lemon")
            )
        command = [
            ctest,
            "--test-dir",
            self.build_folder,
            "--output-on-failure",
            "--no-tests=error",
        ]
        with environment.vars(self).apply():
            self.run(self._serialize(command), env="conanbuild")

    def _sign_upstream_test_closure(self):
        if self.options.shared:
            library_stem = self._library_stem()
            library_prefix = "" if library_stem.startswith("lib") else "lib"
            candidates = [
                path
                for path in Path(self.build_folder, "lemon").glob(
                    f"{library_prefix}{library_stem}.so*"
                )
                if path.is_file() and not path.is_symlink()
            ]
            if len(candidates) != 1:
                raise ConanInvalidConfiguration(
                    f"expected one real {library_prefix}{library_stem} shared object, found "
                    f"{len(candidates)}"
                )
            self._sign_elf(candidates[0])
        for name in self._upstream_tests:
            self._sign_elf(Path(self.build_folder, "test", name))

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "lemon.pc")
        if not pc_path.is_file():
            raise ConanException("installed lemon.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, pc_count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if pc_count != 1:
            raise ConanException("lemon.pc has no unique prefix field")
        pc_path.write_text(pc_content, encoding="utf-8")

        config_path = Path(
            self.package_folder, "share", "lemon", "cmake", "LEMONConfig.cmake"
        )
        if not config_path.is_file():
            raise ConanException("installed LEMONConfig.cmake is missing")
        config_content = config_path.read_text(encoding="utf-8")
        config_content, include_count = re.subn(
            r'^SET\(LEMON_INCLUDE_DIR ".*" CACHE PATH',
            'SET(LEMON_INCLUDE_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../include" CACHE PATH',
            config_content,
            count=1,
            flags=re.MULTILINE,
        )
        library_name = self._installed_library_name()
        config_content, library_count = re.subn(
            r'^SET\(LEMON_LIBRARY ".*" CACHE FILEPATH',
            'SET(LEMON_LIBRARY "${CMAKE_CURRENT_LIST_DIR}/../../../lib/'
            + library_name
            + '" CACHE FILEPATH',
            config_content,
            count=1,
            flags=re.MULTILINE,
        )
        if include_count != 1 or library_count != 1:
            raise ConanException("LEMONConfig.cmake relocation fields changed")
        config_path.write_text(config_content, encoding="utf-8")

    def _installed_library_name(self):
        if str(self.settings.os) == "Windows":
            return "lemon.lib"
        suffix = ".so" if self.options.shared else ".a"
        library_stem = self._library_stem()
        library_prefix = "" if library_stem.startswith("lib") else "lib"
        return f"{library_prefix}{library_stem}{suffix}"

    def _library_stem(self):
        if str(self.settings.os) == "Windows":
            return "lemon"
        if str(self.settings.os) == "OHOS":
            return "lemon"
        return "emon"

    def _sign_elf(self, executable):
        executable = Path(executable)
        if not executable.is_file():
            raise ConanInvalidConfiguration(
                f"required OHOS ELF is missing: {executable}"
            )
        objcopy = self._resolve_tool("objcopy")
        try:
            readelf = self._resolve_tool("readelf")
        except ConanInvalidConfiguration:
            readelf = self._resolve_tool("readobj")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        temporary = executable.with_name(f"{executable.name}.signing-{os.getpid()}")
        try:
            shutil.copy2(executable, temporary)
            sections = self._read_sections(readelf, temporary)
            if ".codesign" in sections:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(temporary)],
                    check=True,
                )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    str(temporary),
                    "-outFile",
                    str(temporary),
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            signed_sections = self._read_sections(readelf, temporary)
            if ".codesign" not in signed_sections:
                raise ConanException(f"signer did not add .codesign: {executable}")
            os.replace(temporary, executable)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _read_sections(self, readelf, executable):
        if str(self.settings.os) == "OHOS" and Path(readelf).name in {
            "llvm-readobj",
            "llvm-readobj.exe",
        }:
            command = [readelf, "--sections", str(executable)]
        else:
            command = [readelf, "-S", str(executable)]
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def _resolve_tool(self, tool, llvm=True):
        compiler = self._cxx_compiler()
        compiler_dir = os.path.dirname(compiler)
        compiler_name = os.path.basename(compiler)
        suffix = (
            compiler_name[len("clang++") :]
            if compiler_name.startswith("clang++")
            else ""
        )
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidates = [executables.get(tool)]
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(compiler_dir, f"llvm-{tool}{suffix}"),
                        os.path.join(compiler_dir, f"llvm-{tool}"),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        if llvm and suffix:
            candidates.append(f"llvm-{tool}{suffix}")
        if llvm:
            candidates.append(f"llvm-{tool}")
        candidates.append(tool)
        for candidate in candidates:
            if candidate:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
        raise ConanInvalidConfiguration(f"required OHOS tool was not found: {tool}")

    def _cxx_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("cpp") or shutil.which("c++")
        resolved = shutil.which(compiler) if compiler else None
        if not resolved:
            raise ConanInvalidConfiguration("No C++ compiler is configured")
        return resolved

    def _serialize(self, command):
        if str(self.settings.os) == "Windows":
            return subprocess.list2cmdline([str(item) for item in command])
        return shlex.join(str(item) for item in command)
