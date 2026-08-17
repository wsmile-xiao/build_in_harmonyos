#!/usr/bin/env python3
"""Conan recipe for vera++ 1.3.0 — CMake project (C++ source code verification tool).

Build system: cmake
License: BSL-1.0
Dependencies: boost/1.84.0, tcl/8.6.14
Adaptation notes:
  - Published boost package does not ship libboost_wave.a (only filesystem/
    iostreams/program_options/regex). vera++ links boost::wave, so this recipe
    compiles libboost_wave.a from the official boost source (12 files in
    libs/wave/src) against the boost package headers, then links it in.
  - The boost package headers already carry the BOOST_SP_NO_PTHREAD_SETCANCELSTATE
    guard (E127: HarmonyOS has no pthread_setcancelstate), so wave compilation
    only needs -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE defined (R8: no platform macro).
  - CMake 4.x removed support for cmake_minimum_required < 3.5; vera++ 1.3.0
    requires 2.8.6, so CMAKE_POLICY_VERSION_MINIMUM=3.5 is set (E103 pattern).
  - Python/Lua rule support is disabled (VERA_PYTHON=OFF, VERA_LUA=OFF); the
    built-in Tcl interpreter (cpptcl) is used for rule scripts.
"""
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class VeraPPConan(ConanFile):
    name = "vera++"
    version = "1.3.0"
    description = "A programmable tool for verification, analysis and transformation of C++ source code"
    license = "BSL-1.0"
    homepage = "https://github.com/verateam/vera"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("tcl/8.6.14")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Boost source is only needed to compile libboost_wave.a (not shipped
        # in the published boost package). Headers used come from the boost
        # package (already patched), not from this source tree.
        get(self, **self.conan_data["boost_sources"], strip_root=True, destination="boost-src")

    def generate(self):
        cmake_deps = CMakeDeps(self)
        cmake_deps.generate()
        tc = CMakeToolchain(self)
        # E103: CMake 4.x compatibility with old cmake_minimum_required
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Keep the Tcl interpreter; disable Python/Lua rule engines
        tc.variables["VERA_PYTHON"] = "OFF"
        tc.variables["VERA_LUA"] = "OFF"
        tc.variables["VERA_USE_SYSTEM_BOOST"] = "ON"

        boost = self.dependencies["boost"]
        tcl = self.dependencies["tcl"]
        tc.variables["Boost_INCLUDE_DIR"] = boost.cpp_info.includedirs[0]
        tc.variables["Boost_LIBRARY_DIR"] = boost.cpp_info.libdirs[0]
        tc.variables["TCL_INCLUDE_PATH"] = tcl.cpp_info.includedirs[0]
        tc.variables["TCL_LIBRARY"] = os.path.join(tcl.cpp_info.libdirs[0], "libtcl8.6.a")
        # libboost_wave.a is compiled in build(); link it explicitly
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            f"-L{os.path.join(self.build_folder, 'wave-lib')} -lboost_wave"
        )
        tc.generate()

    def _compile_wave_lib(self, cxx, include_dir, ar):
        """Compile libboost_wave.a from boost source (12 files in libs/wave/src)."""
        wave_src = os.path.join(self.source_folder, "boost-src", "libs", "wave", "src")
        wave_files = []
        for root, _dirs, files in os.walk(wave_src):
            if "samples" in root or "test" in root:
                continue
            for f in sorted(files):
                if f.endswith(".cpp"):
                    wave_files.append(os.path.join(root, f))
        if not wave_files:
            raise RuntimeError("No boost wave sources found under " + wave_src)

        wave_lib = os.path.join(self.build_folder, "wave-lib")
        os.makedirs(wave_lib, exist_ok=True)
        obj_dir = os.path.join(self.build_folder, "wave-obj")
        os.makedirs(obj_dir, exist_ok=True)

        cxxflags = f"-std=c++17 -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE -I{include_dir}"
        objects = []
        for src in wave_files:
            rel = os.path.relpath(src, wave_src).replace(os.sep, "_").replace(".cpp", ".o")
            obj = os.path.join(obj_dir, rel)
            objects.append(obj)

        def compile_one(src, obj):
            self.run(f"{cxx} {cxxflags} -c {src} -o {obj}")

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(compile_one, wave_files, objects))

        lib_path = os.path.join(wave_lib, "libboost_wave.a")
        self.run(f"{ar} rcs {lib_path} {' '.join(objects)}")
        return lib_path

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compilers from Conan conf, not shell env vars
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compiler_executables, dict):
            cxx = compiler_executables.get("cpp", "clang++")
            cc_bin = compiler_executables.get("c", "clang")
        else:
            cxx, cc_bin = "clang++", "clang"
        ar = shutil.which("llvm-ar") or os.path.join(os.path.dirname(cxx), "llvm-ar") or "ar"

        boost_inc = self.dependencies["boost"].cpp_info.includedirs[0]
        self._compile_wave_lib(cxx, boost_inc, ar)

        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["-j4"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
