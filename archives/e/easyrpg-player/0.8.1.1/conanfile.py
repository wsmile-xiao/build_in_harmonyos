#!/usr/bin/env python3
"""Conan recipe for easyrpg-player 0.8.1.1 — RPG Maker 2000/2003 game interpreter.

Build system: CMake
Dependencies (via Conan ohpcd): zlib, icu4c, inih
Dependencies (via cmd-pkgs): sdl2, pixman, freetype, libpng, expat, libogg
Dependencies (built from source): fmt (not on ohpcd or cmd-pkgs)
liblcf is built from source via PLAYER_BUILD_LIBLCF=ON
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EasyRpgPlayerConan(ConanFile):
    name = "easyrpg-player"
    version = "0.8.1.1"
    description = "Interpreter for RPG Maker 2000/2003 games"
    license = "MIT"
    homepage = "https://easyrpg.org"
    url = "https://github.com/EasyRPG/Player"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Only dependencies available on ohpcd conan remote
        self.requires("zlib/1.3.1")
        self.requires("icu4c/77")
        self.requires("inih/r58")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download liblcf source for PLAYER_BUILD_LIBLCF
        liblcf_dir = os.path.join(self.source_folder, "lib", "liblcf")
        os.makedirs(liblcf_dir, exist_ok=True)
        get(self, **self.conan_data["liblcf_sources"], strip_root=True,
            destination=liblcf_dir)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["PLAYER_BUILD_EXECUTABLE"] = "ON"
        tc.variables["PLAYER_BUILD_LIBLCF"] = "ON"
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "OFF"
        # Enable CMake to find cmd-pkgs in ~/usr/local despite toolchain restrictions
        tc.variables["PLAYER_FIND_ROOT_PATH_APPEND"] = "ON"
        # cmd-pkgs install prefix for non-conan dependencies
        cmd_prefix = os.path.join(os.path.expanduser("~"), "usr", "local")
        tc.variables["CMAKE_PREFIX_PATH"] = cmd_prefix
        # Allow CMake to search both conan root and system paths
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.generate()

    def build(self):
        # Install non-conan dependencies via cmd-pkgs
        self._install_cmd_pkgs()
        # Build fmt from source (not on ohpcd or cmd-pkgs)
        self._build_fmt_from_source()
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _install_cmd_pkgs(self):
        """Install prebuilt packages not available via Conan."""
        prefix = os.path.join(os.path.expanduser("~"), "usr", "local")
        pkgs = [
            ("sdl2", "2.30.0", "lib/libSDL2.so"),
            ("pixman", "0.46.4", "lib/libpixman-1.so"),
            ("freetype", "2.14.3", "lib/libfreetype.a"),
            ("libpng", "1.6.43", "lib/liblibpng16_static.a"),
            ("expat", "2.7.1", "lib/libexpat.so"),
            ("libogg", "1.3.5", "lib/libogg.a"),
        ]
        for name, version, check in pkgs:
            if os.path.exists(os.path.join(prefix, check)):
                continue

            url = (
                f"https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
                f"/releases/download/pkgs/{name}-{version}-ohos-aarch64.tar.gz"
            )
            tmpdir = os.path.join(self.build_folder, f"cmd-pkgs-{name}")
            os.makedirs(tmpdir, exist_ok=True)
            os.makedirs(prefix, exist_ok=True)

            self.run(f'curl -fSL -o "{tmpdir}/{name}.tar.gz" "{url}"')
            self.run(f'tar xzf "{tmpdir}/{name}.tar.gz" -C "{tmpdir}"')
            self.run(f'cp -r "{tmpdir}"/* "{prefix}/" 2>/dev/null || true')
            shutil.rmtree(tmpdir, ignore_errors=True)

        # Fix libpng symlinks (cmd-pkgs ships as liblibpng16_static.a)
        libpng_static = os.path.join(prefix, "lib", "liblibpng16_static.a")
        if os.path.exists(libpng_static):
            for link_name in ("libpng.a", "libpng16.a"):
                link_path = os.path.join(prefix, "lib", link_name)
                if not os.path.exists(link_path):
                    os.symlink("liblibpng16_static.a", link_path)

        # Fix pixman symlinks (cmd-pkgs ships as libpixman-1.so.0.46.4)
        pixman_so = os.path.join(prefix, "lib", "libpixman-1.so.0.46.4")
        if os.path.exists(pixman_so):
            for link_name in ("libpixman-1.so", "libpixman-1.so.0"):
                link_path = os.path.join(prefix, "lib", link_name)
                if not os.path.exists(link_path):
                    os.symlink("libpixman-1.so.0.46.4", link_path)

    def _build_fmt_from_source(self):
        """Build fmt library from source (not available on ohpcd or cmd-pkgs)."""
        prefix = os.path.join(os.path.expanduser("~"), "usr", "local")
        fmt_check = os.path.join(prefix, "lib", "libfmt.a")
        if os.path.exists(fmt_check):
            return

        fmt_url = (
            "https://ghfast.top/https://github.com/"
            "fmtlib/fmt/archive/refs/tags/8.1.1.tar.gz"
        )
        fmt_dir = os.path.join(self.build_folder, "fmt-src")
        os.makedirs(fmt_dir, exist_ok=True)

        self.run(f'curl -fSL -o "{fmt_dir}/fmt.tar.gz" "{fmt_url}"')
        self.run(f'tar xzf "{fmt_dir}/fmt.tar.gz" -C "{fmt_dir}" --strip-components=1')

        build_dir = os.path.join(fmt_dir, "build")
        os.makedirs(build_dir, exist_ok=True)
        self.run(
            f'cd "{build_dir}" && cmake .. '
            f'-DCMAKE_BUILD_TYPE=Release '
            f'-DCMAKE_INSTALL_PREFIX="{prefix}" '
            f'-DFMT_TEST=OFF -DFMT_DOC=OFF '
            f'-DBUILD_SHARED_LIBS=OFF'
        )
        self.run(f'cd "{build_dir}" && make -j1 && make install')
        shutil.rmtree(fmt_dir, ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
