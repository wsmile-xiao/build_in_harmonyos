#!/usr/bin/env python3
"""Conan test_package for kuickshow 0.11.0.

Consumer-side verification for an application package (upstream registers
no test suite — N=0):

* Part 1 (R34): execute the installed kuickshow binary with --version
  under QT_QPA_PLATFORM=offscreen and assert the 0.11.0 version string.
* Part 2: the Imlib palette data contract (share/kuickshow/im_palette.pal:
  64 lines, each "0xR 0xG 0xB" hex triplets).
* Part 3: the application data contract (share/kuickshow/pics/: the 9
  files from pics/CMakeLists.txt).
* Part 4: the desktop integration contract (org.kde.kuickshow.desktop,
  hicolor icons 16/22/32, kuickshow.categories logging categories).

The runtime environment mirrors the kgoldrunner 26.04.0 precedent:
relative DT_NEEDED entries baked into the published KF6 packages are
resolved through compatibility symlinks, the OHOS loader gets
/system/lib64 for libc++_shared.so, and every dependency lib dir lands on
LD_LIBRARY_PATH.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class KuickshowTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qtbase uses cmake_find_mode=none: write conan_cmakedeps_paths
        # manually (kgoldrunner 26.04.0 precedent).
        lines = []
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
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
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with build_env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _collect_transitive_libdirs(self):
        """Every package folder reachable in the test graph (direct +
        transitive) that carries a lib/ directory."""
        libdirs = []
        seen = set()
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            lib = os.path.join(dep.package_folder, "lib")
            if lib not in seen and os.path.isdir(lib):
                seen.add(lib)
                libdirs.append(lib)
        return libdirs

    def _prepare_runtime_links(self):
        """Compatibility symlinks for relative DT_NEEDED entries baked into
        the published KF6 packages (audiocd 26.04.3 / kgoldrunner
        precedent: e.g. libKF6KIOFileWidgets.so needs '../../bin/...'
        relative to the process cwd)."""
        compat_libs = {}
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if name.endswith(".so") or name.endswith(".so.6"):
                    compat_libs[name] = os.path.join(libdir, name)
        exe_dir = os.path.dirname(
            os.path.join(self.build_folder, self.cpp.build.bindirs[0])
        )
        for base in (
            os.path.normpath(os.path.join(exe_dir, os.pardir, os.pardir, "bin")),
            os.path.normpath(os.path.join(exe_dir, os.pardir, "bin")),
            os.path.join(self.build_folder, "bin"),
        ):
            os.makedirs(base, exist_ok=True)
            for name, src in compat_libs.items():
                dst = os.path.join(base, name)
                if name.startswith("libKF6") and not os.path.exists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def _fix_absolute_needed(self):
        """The published KF6 binaries carry build-machine absolute paths in
        DT_NEEDED. The OHOS musl loader resolves path-style NEEDED entries
        literally with no LD_LIBRARY_PATH fallback; create the missing
        paths as symlinks to the real libraries found in the dependency
        packages (kgoldrunner 26.04.0 precedent)."""
        import struct

        def elf_needed(path):
            """Minimal ELF DT_NEEDED extractor (no readelf dependency)."""
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
        pkg = self.dependencies.get(self.tested_reference_str)
        if not pkg or not pkg.package_folder:
            raise ConanException("tested package not in graph")
        exe = os.path.join(pkg.package_folder, "bin", "kuickshow")
        data = os.path.join(pkg.package_folder, "share", "kuickshow")
        if not os.path.isfile(exe):
            raise ConanException(f"installed binary missing: {exe}")
        if not os.path.isdir(data):
            raise ConanException(f"installed app data missing: {data}")

        if str(self.settings.os) == "OHOS":
            self._sign(exe)
            self._prepare_runtime_links()
            self._fix_absolute_needed()

        test_env = Environment()
        for libdir in self._collect_transitive_libdirs():
            test_env.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("KS_TEST_BIN", exe)
        test_env.define("KS_TEST_DATA_DIR", data)
        test_env.define("KS_TEST_PREFIX", pkg.package_folder)
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        test_env.define("HOME", test_home)

        cmd = os.path.join(self.cpp.build.bindirs[0],
                           "kuickshow_consumer_test")
        with test_env.vars(self).apply():
            self.run(f"{shlex.quote(cmd)}", env="conanrun")
            self.output.info("consumer test passed")

    def _sign(self, path):
        import subprocess
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True)
