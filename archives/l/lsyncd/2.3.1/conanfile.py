#!/usr/bin/env python3
"""Conan recipe for lsyncd 2.3.1 — Live Syncing Daemon.

lsyncd (Live Syncing Daemon) monitors local directory changes (via inotify)
and syncs them to remote destinations using rsync/rsyncssh. It is configured
through Lua scripts.

Build system: CMake
Dependencies: Lua 5.3.6 (built from source: host interpreter + target liblua.a)

Note: cmd-pkgs prebuilt Lua tarballs returned HTTP 404, so Lua is built from
the official lua.org source during the build() step. The host interpreter
runs bin2carray.lua (code generator), and the target liblua.a links into
the lsyncd binary.
"""
import hashlib
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


# Lua 5.3.6 source (build dependency — not available in Conan repo or cmd-pkgs)
LUA_URL = "https://www.lua.org/ftp/lua-5.3.6.tar.gz"
LUA_SHA256 = "fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60"


class LsyncdConan(ConanFile):
    name = "lsyncd"
    version = "2.3.1"
    description = "Live Syncing Daemon - monitors local dirs and syncs via rsync"
    license = "GPL-2.0"
    homepage = "https://github.com/axkibe/lsyncd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lsyncd only supports Linux/OHOS, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Lua is built from source in build() — not available as Conan package
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Support offline local CI simulation: when LSYNCD_OFFLINE_SRC points
        # to a local tarball, use it instead of downloading from github.
        # On CI this env var is unset, so conandata.yml url is used.
        offline_src = os.environ.get("LSYNCD_OFFLINE_SRC")
        if offline_src and os.path.isfile(offline_src):
            self.output.warning(
                f"Using offline source tarball without SHA256 verification: {offline_src} "
                "(LSYNCD_OFFLINE_SRC is for local dev only; CI uses conandata.yml url with sha256)"
            )
            self.output.info(f"Using offline source tarball: {offline_src}")
            file_url = "file:///" + offline_src.replace("\\", "/").lstrip("/")
            get(self, url=file_url, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def _get_target_cc(self):
        """Get target C compiler from Conan conf (R33: no hardcoded env vars)."""
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("c") or "clang"

    def _get_host_cc(self):
        """Get host C compiler for building host Lua tools (code generator).

        The host compiler must produce binaries that run on the BUILD machine.
        - Native build (build os == target os): use Conan conf compiler (R33).
        - Cross build (build os != target os): use a native compiler from PATH
          (gcc/clang/cc), NOT the cross-compiler from Conan conf, whose output
          cannot run on the build machine.
        """
        if self.settings_build.os == "Windows":
            return "gcc"
        # Native build: Conan conf compiler runs natively on the build machine
        if str(self.settings_build.os) == str(self.settings.os):
            comp_execs = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            return comp_execs.get("c") or "clang"
        # Cross-compilation: find a native compiler on the build machine.
        # Do NOT use tools.build:compiler_executables — that returns the TARGET
        # cross-compiler whose output cannot run on the x86_64 build machine.
        for candidate in ("gcc", "clang", "cc"):
            path = shutil.which(candidate)
            if path:
                return path
        return "gcc"

    def _get_target_ar(self):
        """Get target archiver (llvm-ar from OHOS SDK)."""
        cc = self._get_target_cc()
        cc_dir = os.path.dirname(cc)
        if cc_dir:
            ar = os.path.join(cc_dir, "llvm-ar")
            if os.path.isfile(ar):
                return ar
        return "llvm-ar"

    def _get_target_ranlib(self):
        """Get target ranlib (llvm-ranlib from OHOS SDK)."""
        cc = self._get_target_cc()
        cc_dir = os.path.dirname(cc)
        if cc_dir:
            ranlib = os.path.join(cc_dir, "llvm-ranlib")
            if os.path.isfile(ranlib):
                return ranlib
        return "llvm-ranlib"

    def _get_target_cflags(self):
        """Get extra CFLAGS for target cross-compilation (--target + --sysroot).

        Lua is built with make (not CMake), so CMakeToolchain does not inject
        target/sysroot for it. We must pass them explicitly via MYCFLAGS.
        On CI (Linux worker + OHOS-adapted Conan) these are usually redundant
        but harmless; on local Windows simulation they are required.
        """
        cflags = []
        if str(self.settings.os) == "OHOS":
            arch = str(self.settings.arch)
            if arch in ("armv8", "armv8.3", "aarch64"):
                cflags.append("--target=aarch64-linux-ohos")
            elif arch == "x86_64":
                cflags.append("--target=x86_64-linux-ohos")
            else:
                self.output.warning(f"Unknown OHOS arch '{arch}'; no --target flag added")
            sysroot = self.conf.get("tools.build:sysroot", default=None)
            if sysroot:
                cflags.append(f"--sysroot={sysroot}")
        return " ".join(cflags)

    def _download_lua(self):
        """Download and extract Lua 5.3.6 source to build folder."""
        lua_dir = os.path.join(self.build_folder, "lua-5.3.6")
        if os.path.isdir(os.path.join(lua_dir, "src")):
            self.output.info(f"Lua 5.3.6 source already exists at {lua_dir}")
            return lua_dir

        archive_path = os.path.join(self.build_folder, "lua-5.3.6.tar.gz")
        self.output.info(f"Downloading Lua 5.3.6 from {LUA_URL}...")
        # Use curl — CI workers may lack Python ssl module for HTTPS
        self.run(f'curl -L -sS --fail -o "{archive_path}" "{LUA_URL}"')

        # Verify SHA256
        h = hashlib.sha256()
        with open(archive_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        actual = h.hexdigest()
        if actual != LUA_SHA256:
            raise ConanInvalidConfiguration(
                f"Lua source SHA256 mismatch: expected {LUA_SHA256}, got {actual}"
            )

        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(self.build_folder)
        self.output.info(f"Lua 5.3.6 source extracted to {lua_dir}")
        return lua_dir

    def _build_lua(self, lua_dir):
        """Build host Lua tools and target liblua.a."""
        lua_src = os.path.join(lua_dir, "src")
        # Host executables need .exe suffix on Windows so cmd.exe (used by
        # CMake's add_custom_command) can invoke them. CI (Linux) uses no suffix.
        exe_ext = ".exe" if self.settings_build.os == "Windows" else ""
        host_lua_saved = os.path.join(lua_dir, f"host-lua{exe_ext}")
        host_luac_saved = os.path.join(lua_dir, f"host-luac{exe_ext}")

        # Step 1: Build host lua interpreter with host cc
        # (needed to run bin2carray.lua code generator during lsyncd build)
        # NOTE: Do NOT use -DLUA_USE_LINUX — it pulls in readline/readline.h
        # which is not installed on CI workers. We only need to run scripts,
        # not interactive line editing.
        # R33: host cc from Conan conf (OHOS CI has no 'cc' command, only clang)
        host_cc = self._get_host_cc()
        self.output.info(f"Building host Lua tools with {host_cc} for code generation...")
        self.run(f'make -C "{lua_src}" CC="{host_cc}" MYCFLAGS="" lua luac')
        shutil.copy2(os.path.join(lua_src, f"lua{exe_ext}"), host_lua_saved)
        shutil.copy2(os.path.join(lua_src, f"luac{exe_ext}"), host_luac_saved)
        self.output.info(f"Host Lua tools saved to {host_lua_saved} and {host_luac_saved}")

        # Step 2: Clean and rebuild liblua.a with target cross-compiler
        # (this liblua.a links into the lsyncd binary for the target arch)
        self.output.info(f"Building target liblua.a (for {self.settings.arch})...")
        self.run(f'make -C "{lua_src}" clean')
        target_cc = self._get_target_cc()
        target_ar = self._get_target_ar()
        target_ranlib = self._get_target_ranlib()
        target_cflags = self._get_target_cflags()
        self.run(
            f'make -C "{lua_src}" CC="{target_cc}" '
            f'AR="{target_ar} rcs" RANLIB="{target_ranlib}" '
            f'MYCFLAGS="-fPIC {target_cflags}" liblua.a'
        )
        self.output.info("Target liblua.a built successfully")

        return host_lua_saved, host_luac_saved, lua_src, os.path.join(lua_src, "liblua.a")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WITH_INOTIFY"] = True
        tc.variables["WITH_FSEVENTS"] = False
        lua_dir = os.path.join(self.build_folder, "lua-5.3.6")
        lua_src = os.path.join(lua_dir, "src")
        tc.variables["LUA_INCLUDE_DIR"] = lua_src
        tc.variables["LUA_LIBRARIES"] = os.path.join(lua_src, "liblua.a")
        # Match the host-lua/host-luac filenames written by _build_lua()
        # (.exe suffix on Windows, none on Linux/CI).
        exe_ext = ".exe" if self.settings_build.os == "Windows" else ""
        tc.variables["LUA_EXECUTABLE"] = os.path.join(lua_dir, f"host-lua{exe_ext}")
        tc.variables["LUA_COMPILER"] = os.path.join(lua_dir, f"host-luac{exe_ext}")
        # Force lld linker on OHOS to avoid MinGW ld (no sysroot support) on
        # local Windows simulation. CI (Linux) clang already defaults to lld.
        if str(self.settings.os) == "OHOS":
            ld_flags = "-fuse-ld=lld"
            cur_exe = tc.variables.get("CMAKE_EXE_LINKER_FLAGS", "")
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = f"{cur_exe} {ld_flags}".strip()
            cur_sh = tc.variables.get("CMAKE_SHARED_LINKER_FLAGS", "")
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = f"{cur_sh} {ld_flags}".strip()
        tc.generate()

    def build(self):
        # Build Lua from source (cmd-pkgs unavailable; Lua not in Conan repo)
        lua_dir = self._download_lua()
        self._build_lua(lua_dir)

        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # lsyncd is a CLI daemon tool — binary in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
