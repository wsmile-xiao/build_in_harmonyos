#!/usr/bin/env python3
"""Conan recipe for fairy-stockfish 14 — Makefile-based build system.

Fairy-Stockfish is a UCI/XBoard chess engine supporting many chess variants.
Build system: custom Makefile (not autotools/cmake).
Source layout: src/ subdirectory in the GitHub archive.
This recipe enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class FairystockfishConan(ConanFile):
    name = "fairy-stockfish"
    version = "14"
    description = "Fairy-Stockfish is a UCI/XBoard chess engine supporting many chess variants"
    license = "GPL-3.0"
    homepage = "https://github.com/fairy-stockfish/Fairy-Stockfish"
    url = ""  # CI fills this

    # R26: Terminal tools must be statically linked
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,  # R26: BUILD_SHARED_LIBS=OFF equivalent
    }

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No external dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF)
        # Set up compiler environment for HarmonyOS (clang only, no gcc symlink)
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.define("BUILD_SHARED_LIBS", "OFF")
        env.define("CFLAGS", "-fPIC -O2")
        env.define("CXXFLAGS", "-fPIC -O2")
        # ncurses headers location
        inc_dir = os.path.join(os.path.expanduser("~"), "usr", "local", "include")
        lib_dir = os.path.join(os.path.expanduser("~"), "usr", "local", "lib")
        if os.path.isdir(inc_dir):
            env.append("CFLAGS", f"-I{inc_dir}")
            env.append("CXXFLAGS", f"-I{inc_dir}")
        if os.path.isdir(lib_dir):
            env.append("LDFLAGS", f"-L{lib_dir}")
        # R26: static linking flags
        env.append("LDFLAGS", "-static-libstdc++")
        envvars = env.vars(self)
        envvars.save_script("conan_fairy_stockfish_env")

    def build(self):
        # Source files are in src/ subdirectory in the GitHub archive
        src_dir = os.path.join(self.source_folder, "src")
        # Apply patches from source_folder root (patch uses src/Makefile paths)
        apply_conandata_patches(self)
        # Fallback: ensure -latomic is removed and -static-libstdc++ is added
        # (in case apply_conandata_patches fails to find the patch file)
        makefile = os.path.join(src_dir, "Makefile")
        if os.path.isfile(makefile):
            with open(makefile, "r") as f:
                content = f.read()
            if "-latomic" in content:
                content = content.replace("LDFLAGS += -latomic",
                    "# -latomic removed for HarmonyOS/aarch64\n\t\t# LDFLAGS += -latomic")
            if "-static-libstdc++" not in content:
                # Add after the clang CXXFLAGS line
                content = content.replace(
                    "CXXFLAGS += -pedantic -Wextra -Wshadow",
                    "CXXFLAGS += -pedantic -Wextra -Wshadow\n\t# R26: static link C++ runtime for HarmonyOS\n\tLDFLAGS += -static-libstdc++",
                    1)
            with open(makefile, "w") as f:
                f.write(content)
        # Determine ARCH from Conan settings
        arch_str = str(self.settings.arch)
        if arch_str in ("armv8", "armv8.3", "aarch64"):
            make_arch = "armv8"
        elif arch_str.startswith("armv7"):
            make_arch = "armv7-neon"
        else:
            make_arch = "general-64"
        # Build with Makefile (COMP=clang since system only has clang)
        self.run(f"cd {src_dir} && make build ARCH={make_arch} COMP=clang -j2")

    def package(self):
        # fairy-stockfish produces a single binary: stockfish (in src/)
        src_dir = os.path.join(self.source_folder, "src")
        copy(self, "stockfish", src_dir, os.path.join(self.package_folder, "bin"))
        # Copy variants.ini configuration file
        copy(self, "variants.ini", src_dir,
             os.path.join(self.package_folder, "share", "fairy-stockfish"), keep_path=False)

    def package_info(self):
        # fairy-stockfish is a terminal tool (binary), not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
