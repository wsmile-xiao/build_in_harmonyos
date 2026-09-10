#!/usr/bin/env python3
"""Conan recipe — msdfgen 1.13 (OpenHarmony PC aarch64).

msdfgen is Chlumsky Viktor's multi-channel signed distance field generator.
Upstream builds four CMake targets:

  - msdfgen-core — core MSDF/MT generation, no external deps
  - msdfgen-ext  — extensions: font import (FreeType), image import/export
                   (libpng), text shape-description parsing (tinyxml2)
  - msdfgen-full — combined interface target (ext + core)
  - msdfgen      — the CLI tool

Upstream expects vcpkg-style target names Freetype::Freetype / PNG::PNG,
while this repository's freetype/libpng Conan packages export
freetype::freetype / libpng::libpng. The bridge is done in generate()
via CMakeDeps.set_property (cmake_target_name + cmake_file_name), which
avoids patching upstream sources.

tinyxml2::tinyxml2 already matches upstream, so no bridge is needed there.

On OHOS, shared libraries must carry a .codesign section to be loadable;
signing follows libpng 1.6.58.2's _resolve_tool pattern (compiler-dir
relative resolution, no hardcoded /data/service/hnp/bin requirement).

Options (from upstream CMakeLists.txt, verified against v1.13 tag):
  - MSDFGEN_USE_OPENMP        -> OFF (desktop OpenMP runtime, not needed)
  - MSDFGEN_USE_SKIA          -> OFF (heavy desktop dep, core-safe)
  - MSDFGEN_USE_VCPKG         -> OFF (no vcpkg toolchain)
  - MSDFGEN_BUILD_STANDALONE  -> ON  (deliver the CLI)
  - MSDFGEN_INSTALL           -> ON  (install libs + headers + cmake config)
  - MSDFGEN_USE_CPP11         -> ON  (public header MSDFGEN_USE_CPP11)
  - MSDFGEN_CORE_ONLY         -> OFF (ext is where FreeType lives; core MSDF
                                  generation stays enabled either way)
  - MSDFGEN_DISABLE_PNG       -> OFF (PNG output is core CLI functionality)
  - MSDFGEN_DISABLE_SVG       -> OFF (tinyxml2 shape-description import is a
                                  core CLI input path; upstream names the
                                  option MSDFGEN_DISABLE_SVG)
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class MsdfgenConan(ConanFile):
    name = "msdfgen"
    version = "1.13"
    description = (
        "Multi-channel signed distance field generator (library + CLI tool)"
    )
    license = "MIT"
    homepage = "https://github.com/Chlumsky/msdfgen"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        copy(self, "*.patch", src=self.recipe_folder, dst=self.export_sources_folder)

    requires_list = ("freetype/2.14.3", "libpng/1.6.58.2", "tinyxml2/11.0.0")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "msdfgen supports OHOS armv8 only"
            )

    def requirements(self):
        # tinyxml2 11.0.0: the repository's 10.0.0 recipe hardcodes a
        # signature-tool path check that blocks local consumption; 11.0.0
        # removed that check and has a prebuilt OHOS package on ohpcd.
        self.requires("freetype/2.14.3")
        self.requires("libpng/1.6.58.2")
        self.requires("tinyxml2/11.0.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        # ── target-name bridge: upstream CMake find_package(Freetype) /
        #    find_package(PNG) expect Freetype::Freetype / PNG::PNG, but the
        #    repository's Conan packages export freetype::freetype /
        #    libpng::libpng. tinyxml2::tinyxml2 already matches upstream.
        deps.set_property("freetype", "cmake_target_name", "Freetype::Freetype")
        deps.set_property("freetype", "cmake_file_name", "Freetype")
        deps.set_property("libpng", "cmake_target_name", "PNG::PNG")
        deps.set_property("libpng", "cmake_file_name", "PNG")
        deps.generate()

        tc = CMakeToolchain(self)
        # Keep RPATH clean of host paths (verified in the OHOS test).
        tc.variables["CMAKE_INSTALL_RPATH"] = ""
        tc.variables["CMAKE_BUILD_RPATH"] = ""
        tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = "FALSE"
        # CMake has no HarmonyOS platform module, so it never defines
        # CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG and silently drops the
        # VERSION/SOVERSION target properties set by our patch. Restore the
        # soname rule (note the trailing comma: CMake appends the value
        # directly, e.g. -Wl,-soname,libmsdfgen-core.so.1). Verified on
        # CMake 4.1.2 / HarmonyOS PC.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # Upstream CMakeLists declares its option()s BEFORE project() (line
        # 4-14 vs line 75). CMake executes the toolchain file only when
        # project() declares languages, so toolchain set(... CACHE ...) runs
        # after the options already initialized the cache with upstream
        # defaults — silently ignoring our values. Passing -D on the command
        # line via cmake.configure(variables=...) takes precedence over
        # option() initialization, which is the correct channel here.
        cmake.configure(
            variables={
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "MSDFGEN_USE_OPENMP": "OFF",
                "MSDFGEN_USE_SKIA": "OFF",
                "MSDFGEN_USE_VCPKG": "OFF",
                "MSDFGEN_BUILD_STANDALONE": "ON",
                "MSDFGEN_INSTALL": "ON",
                "MSDFGEN_USE_CPP11": "ON",
                "MSDFGEN_CORE_ONLY": "OFF",
                "MSDFGEN_DISABLE_PNG": "OFF",
                "MSDFGEN_DISABLE_SVG": "OFF",
            }
        )
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_shared_libraries()

    def package_info(self):
        # Upstream install layout (verified in v1.13 CMakeLists.txt):
        #   include/msdfgen{,-ext}.h + include/msdfgen/{core,ext}/*.h
        #   lib/libmsdfgen-core(.so) + libmsdfgen-ext(.so)
        #   bin/msdfgen (CLI)
        #   lib/cmake/msdfgen/* (exported msdfgen:: targets)
        self.cpp_info.set_property("cmake_file_name", "msdfgen")
        self.cpp_info.set_property("cmake_target_name", "msdfgen::msdfgen")
        self.cpp_info.libs = ["msdfgen-ext", "msdfgen-core"]
        self.cpp_info.bindirs = ["bin"]
        # Consumers include <msdfgen/msdfgen.h> or <msdfgen.h>; both are
        # installed by upstream (global include unless
        # MSDFGEN_INSTALL_NO_GLOBAL_INCLUDE).
        self.cpp_info.includedirs = ["include"]
        # msdfgen-ext pulls in freetype/png/tinyxml2 symbols (image save,
        # font glyph import, shape-description parsing). Those are direct
        # requirements of consumers linking msdfgen-ext, so expose them.
        self.cpp_info.requires = ["freetype::freetype", "libpng::libpng", "tinyxml2::tinyxml2"]

    # ── OHOS signing ──────────────────────────────────────────────────────

    def _sign_ohos_shared_libraries(self):
        # Sign every real ELF file (regular file, not a symlink). With the
        # SOVERSION patch the install tree contains libmsdfgen-core.so.1.13
        # plus .so.1/.so symlinks; only the real file gets a .codesign
        # section and the symlinks keep pointing at it.
        candidates = []
        for sub in ("lib", "bin"):
            folder = Path(self.package_folder, sub)
            if not folder.is_dir():
                continue
            for path in sorted(folder.iterdir()):
                if path.is_symlink() or not path.is_file():
                    continue
                with open(path, "rb") as fh:
                    if fh.read(4) != b"\x7fELF":
                        continue
                candidates.append(path)
        if not candidates:
            raise ConanException("no ELF artifacts found to sign")
        for path in candidates:
            self._sign_elf(path)

    def _sign_elf(self, executable):
        executable = Path(executable)
        if not executable.is_file():
            raise ConanInvalidConfiguration(
                f"required OHOS ELF is missing: {executable}"
            )
        objcopy = self._resolve_tool("objcopy")
        readelf = self._resolve_tool("readelf")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        temporary = executable.with_name(
            f"{executable.name}.signing-{os.getpid()}"
        )
        try:
            shutil.copy2(executable, temporary)
            sections = subprocess.run(
                [readelf, "-SW", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
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
            signed_sections = subprocess.run(
                [readelf, "-SW", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if signed_sections.count(".codesign") != 1:
                raise ConanException(f"signer did not add .codesign: {executable}")
            os.chmod(temporary, (os.stat(temporary).st_mode & 0o777) | 0o755)
            os.replace(temporary, executable)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _resolve_tool(self, tool, llvm=True):
        # Resolve LLVM/binary tools relative to the configured compiler
        # (libpng 1.6.58.2 pattern) — no hardcoded /data/service/hnp/bin.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or shutil.which("cc")
        compiler_dir = os.path.dirname(shutil.which(compiler) or compiler) if compiler else ""
        compiler_name = os.path.basename(compiler) if compiler else ""
        suffix = (
            compiler_name[len("clang"):]
            if compiler_name.startswith("clang")
            else ""
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
