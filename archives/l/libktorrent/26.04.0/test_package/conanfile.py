#!/usr/bin/env python3
"""Conan test_package for libktorrent 26.04.0.

Consumer-side verification for a library package:

* links KTorrent6 through its installed CMake config
  (find_package(KTorrent6 CONFIG REQUIRED)) and exercises the public API:
  - bt::GetVersionString() / bt::SetClientInfo() (version.h)
  - bencode round-trip (BEncoder + BDecoder + BDictNode)
  - SHA-1 hashing (SHA1Hash::generate)
Headless and network-free (no QApplication needed for these entry points).
"""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibktorrentTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # KTorrent6Config.cmake find_dependency chains: KF6Archive/KF6Config/
        # KF6KIO/Qt6Core/Qt6Network/Boost/LibGMP/OpenSSL — surface the ones
        # whose cmake configs the consumer test's find_package walk reaches.
        self.requires("qtbase/6.11.1")
        self.requires("karchive/6.26.0", options={"shared": True})
        self.requires("kconfig/6.26.0", options={"shared": True})
        self.requires("kio/6.26.0", options={"shared": True})
        self.requires("kcrash/6.26.0", options={"shared": True})
        self.requires("ki18n/6.26.0", options={"shared": True})
        self.requires("solid/6.26.0", options={"shared": True})
        self.requires("boost/1.90.0.3")
        self.requires("gmp/6.3.0.1")
        self.requires("libgcrypt/1.12.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qtbase / libktorrent use cmake_find_mode=none: write
        # conan_cmakedeps_paths manually (kgoldrunner 26.04.0 precedent).
        lines = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                pkg = dep.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
                bindir = os.path.join(pkg, "bin")
                if os.path.isdir(bindir):
                    lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{bindir}")')
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            import glob as _glob
            for llvm_lib in sorted(
                _glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with build_env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _fix_absolute_needed(self):
        """The published KF6 binaries carry build-machine absolute paths in
        DT_NEEDED (e.g. libKF6Crash.so needs .../.cache/conan2/p/kcore*/p/
        lib/libKF6CoreAddons.so). The OHOS musl loader resolves path-style
        NEEDED entries literally with no LD_LIBRARY_PATH fallback, and those
        directories only exist on the worker that built the package. Create
        the missing paths as symlinks to the real libraries found in the
        dependency packages (kgoldrunner 26.04.0 precedent)."""
        import struct

        def elf_needed(path):
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                return []
            if data[:4] != b"\x7fELF" or data[4] != 2:
                return []
            is_le = data[5] == 1
            e_shoff = struct.unpack_from("<Q" if is_le else ">Q", data, 0x28)[0]
            e_shentsize = struct.unpack_from(
                "<H" if is_le else ">H", data, 0x3A)[0]
            e_shnum = struct.unpack_from("<H" if is_le else ">H", data, 0x3C)[0]
            needed = []
            dynstr = None
            for i in range(e_shnum):
                off = e_shoff + i * e_shentsize
                if off + e_shentsize > len(data):
                    break
                sh_type = struct.unpack_from(
                    "<I" if is_le else ">I", data, off + 4)[0]
                if sh_type == 3:  # SHT_STRTAB
                    dynstr = off
                elif sh_type == 6:  # SHT_DYNAMIC
                    d_off = struct.unpack_from(
                        "<Q" if is_le else ">Q", data, off + 0x18)[0]
                    d_size = struct.unpack_from(
                        "<Q" if is_le else ">Q", data, off + 0x20)[0]
                    if dynstr is None:
                        continue
                    str_off = struct.unpack_from(
                        "<Q" if is_le else ">Q", data, dynstr + 0x18)[0]
                    p = d_off
                    end = d_off + d_size
                    while p + 16 <= end and p + 16 <= len(data):
                        tag, val = struct.unpack_from(
                            "<QQ" if is_le else ">QQ", data, p)
                        if tag == 0:
                            break
                        if tag == 1:  # DT_NEEDED
                            s = str_off + val
                            e = data.index(b"\x00", s)
                            needed.append(data[s:e].decode("utf-8", "replace"))
                        p += 16
            return needed

        index = {}
        libdirs = []
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir) and libdir not in libdirs:
                libdirs.append(libdir)
                for name in os.listdir(libdir):
                    full = os.path.join(libdir, name)
                    if os.path.isfile(full) and (
                        name.endswith(".so") or ".so." in name
                    ):
                        index.setdefault(name, full)

        fixes = 0
        for libdir in libdirs:
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if not os.path.isfile(full) or not (
                    name.endswith(".so") or ".so." in name
                ):
                    continue
                for entry in elf_needed(full):
                    if not entry.startswith("/"):
                        continue
                    if os.path.exists(entry):
                        continue
                    base = os.path.basename(entry)
                    source = index.get(base)
                    if not source:
                        continue
                    try:
                        os.makedirs(os.path.dirname(entry), exist_ok=True)
                        if not os.path.lexists(entry):
                            os.symlink(source, entry)
                            fixes += 1
                    except OSError as e:
                        self.output.warning(
                            f"cannot create NEEDED fallback {entry}: {e}")
        if fixes:
            self.output.info(
                f"created {fixes} absolute-NEEDED compatibility symlinks")

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if str(self.settings.os) == "OHOS":
            self._fix_absolute_needed()
        test_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib):
                    test_env.prepend_path("LD_LIBRARY_PATH", lib)
        if str(self.settings.os) == "OHOS":
            import glob as _glob
            for llvm_lib in sorted(
                _glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                test_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_package")
        with test_env.vars(self).apply():
            self.run(shlex.quote(cmd), env="conanrun")
            self.output.info("consumer test passed")
