#!/usr/bin/env python3
"""Conan recipe for ataqv 1.3.1 — ATAC-seq QC toolkit.

Build system: Makefile (not cmake/autotools).
Produces: ataqv CLI binary + helper scripts + web resources.

Dependencies: htslib, boost (filesystem/iostreams/chrono), ncurses, zlib.
Note: The conan boost package's iostreams library lacks zlib support,
so we compile boost iostreams source files locally with the conan zlib.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, mkdir, save, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AtaqvConan(ConanFile):
    name = "ataqv"
    version = "1.3.1"
    description = "A toolkit for QC and visualization of ATAC-seq results"
    license = "GPL-3.0"
    homepage = "https://github.com/ParkerLab/ataqv"
    url = "https://github.com/ParkerLab/ataqv"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*", "sources/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("htslib/1.24-r0")
        self.requires("boost/1.91.0.1.1")
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cxx(self):
        """Get C++ compiler from Conan configuration (R33 compliant)."""
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        return compilers.get("cpp", "clang++")

    def _dep_dirs(self, name):
        """Return (includedirs, libdirs) for a dependency."""
        dep = self.dependencies[name]
        agg = dep.cpp_info.aggregated_components()
        return agg.includedirs[0], agg.libdirs[0]

    def build(self):
        apply_conandata_patches(self)
        cxx = self._get_cxx()

        # Dependency paths from Conan
        boost_inc, boost_lib = self._dep_dirs("boost")
        htslib_inc, htslib_lib = self._dep_dirs("htslib")
        zlib_inc, zlib_lib = self._dep_dirs("zlib")
        ncurses_inc, ncurses_lib = self._dep_dirs("ncurses")
        xz_inc, xz_lib = self._dep_dirs("xz")
        libdeflate_inc, libdeflate_lib = self._dep_dirs("libdeflate")

        # --- Build boost iostreams with zlib support ---
        # The conan boost package's iostreams was built without zlib;
        # compile the boost iostreams source files locally.
        iostreams_src = os.path.join(self.source_folder, "sources", "boost_iostreams")
        obj_files = []
        for src in ("zlib.cpp", "gzip.cpp"):
            src_path = os.path.join(iostreams_src, src)
            obj_path = os.path.join(self.build_folder, f"iostreams_{src.replace('.cpp', '.o')}")
            self.run(
                f"{cxx} -std=c++11 -O3 -fPIC "
                f"-I{boost_inc} -I{zlib_inc} "
                f"-c {src_path} -o {obj_path}"
            )
            obj_files.append(obj_path)

        iostreams_lib = os.path.join(self.build_folder, "libboost_iostreams.a")
        self.run(f"llvm-ar rcs {iostreams_lib} {' '.join(obj_files)}")

        # --- Create ncurses symlink ---
        # Makefile uses -lncurses; conan ncurses provides libncursesw.a
        ncurses_symlink = os.path.join(ncurses_lib, "libncurses.a")
        ncursesw_path = os.path.join(ncurses_lib, "libncursesw.a")
        if os.path.exists(ncursesw_path) and not os.path.exists(ncurses_symlink):
            os.symlink("libncursesw.a", ncurses_symlink)

        # --- Generate Version.hpp ---
        cpp_dir = os.path.join(self.source_folder, "src", "cpp")
        version_hpp = os.path.join(cpp_dir, "Version.hpp")
        save(self, version_hpp,
             f"//\n// Copyright 2015 Stephen Parker\n//\n"
             f"// Licensed under Version 3 of the GPL or any later version\n//\n\n"
             f'#define VERSION "{self.version}"\n')

        # --- Compile ataqv source files ---
        source_files = ["ataqv", "Features", "HTS", "IO", "Metrics", "Peaks", "Utils"]
        obj_dir = os.path.join(self.build_folder, "obj")
        mkdir(self, obj_dir)

        include_flags = (
            f"-I{cpp_dir} -I{zlib_inc} -I{ncurses_inc} "
            f"-I{boost_inc} -I{htslib_inc}"
        )
        cxx_flags = (
            "-std=c++11 -pthread -O3 -g -pedantic -Wall -Wextra "
            "-Wwrite-strings -Wstrict-overflow -fno-strict-aliasing -fPIC"
        )

        for src in source_files:
            src_path = os.path.join(cpp_dir, f"{src}.cpp")
            obj_path = os.path.join(obj_dir, f"{src}.o")
            self.run(f"{cxx} {cxx_flags} {include_flags} -c {src_path} -o {obj_path}")

        # --- Link ataqv binary ---
        ataqv_bin = os.path.join(self.build_folder, "ataqv")
        all_objs = " ".join(os.path.join(obj_dir, f"{s}.o") for s in source_files)
        lib_flags = (
            f"-L{boost_lib} -L{htslib_lib} -L{zlib_lib} "
            f"-L{ncurses_lib} -L{xz_lib} -L{libdeflate_lib}"
        )
        ldlibs = (
            "-lboost_filesystem -lboost_chrono "
            "-lhts -ldeflate -llzma -lz -lncurses -lpthread"
        )

        # R32: settings.os check for OHOS platform
        if self.settings.os in ("Linux", "OHOS"):
            # Link with rpath for shared libraries
            rpath_flags = (
                f"-Wl,-rpath,{boost_lib} -Wl,-rpath,{htslib_lib} "
                f"-Wl,-rpath,{zlib_lib} -Wl,-rpath,{ncurses_lib} "
                f"-Wl,-rpath,{xz_lib} -Wl,-rpath,{libdeflate_lib}"
            )
            self.run(
                f"{cxx} -o {ataqv_bin} {all_objs} {iostreams_lib} "
                f"{lib_flags} {ldlibs} {rpath_flags}"
            )
        else:
            self.run(
                f"{cxx} -o {ataqv_bin} {all_objs} {iostreams_lib} "
                f"{lib_flags} {ldlibs}"
            )

    def package(self):
        # Copy the ataqv binary
        copy(self, "ataqv", self.build_folder, os.path.join(self.package_folder, "bin"))

        # Copy helper scripts
        scripts_dir = os.path.join(self.source_folder, "src", "scripts")
        for script in os.listdir(scripts_dir):
            copy(self, script, scripts_dir, os.path.join(self.package_folder, "bin"))

        # Copy web resources
        web_dir = os.path.join(self.source_folder, "src", "web")
        copy(self, "*", web_dir, os.path.join(self.package_folder, "share", "ataqv", "web"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
