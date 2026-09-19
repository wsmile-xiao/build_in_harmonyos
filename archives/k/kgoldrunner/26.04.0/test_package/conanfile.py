#!/usr/bin/env python3
"""Conan test_package for kgoldrunner 26.04.0.

Consumer-side verification for an application package (upstream registers
no test suite — N=0):

* Part 1 (R34): execute the installed kgoldrunner binary with --version
  under QT_QPA_PLATFORM=offscreen and assert the 26.04 version string.
* Part 2: parse every installed gamedata game_*.txt file against the
  upstream KGoldrunner text format contract (header + level markers +
  28x20 grids) — the data the game engine consumes at runtime.
* Part 3: deep-verify level 1 of the first game (grid geometry 28x20).

The runtime environment mirrors the audiocd 26.04.3 precedent: relative
DT_NEEDED entries baked into the published KF6 packages are resolved
through compatibility symlinks, the OHOS loader gets /system/lib64 for
libc++_shared.so, and openal-soft/libsndfile (transitive requirements of
libkdegames behind libKDEGames6.so) are located through the dependency
graph and appended to LD_LIBRARY_PATH.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class KgoldrunnerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        # openal-soft is required by libKDEGames6.so (NEEDED libopenal.so.1)
        # but is not surfaced through the tested package's direct dependency
        # view; require it explicitly so its lib dir lands in the runtime
        # environment (version pinned to libkdegames' requirement).
        self.requires("openal-soft/1.25.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qtbase uses cmake_find_mode=none: write conan_cmakedeps_paths
        # manually (audiocd 26.04.3 precedent).
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
        # the tested package's own dependency closure (openal-soft,
        # libsndfile behind libkdegames) — walked via the recipe's
        # dependency tree if visible, else via the KF6 relative-NEEDED
        # compatibility links below.
        return libdirs

    def _prepare_runtime_links(self):
        """Compatibility symlinks for relative DT_NEEDED entries baked into
        the published KF6 packages (kconfig's libKF6ConfigGui.so needs
        '../../bin/libKF6ConfigCore.so' relative to the process cwd —
        audiocd 26.04.3 / libkcddb precedent)."""
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
        # the relative path is resolved from cwd; the test runs from the
        # build folder, so provide <build>/../../bin and <build>/bin
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
        DT_NEEDED (e.g. libKF6XmlGui.so needs .../p/kicon<hash>/p/lib/
        libKF6IconThemes.so, libKDEGames6.so needs .../p/b/kicon<hash>/...).
        The OHOS musl loader resolves path-style NEEDED entries literally
        with no LD_LIBRARY_PATH fallback, and on a fresh worker those
        directories do not exist (kiconthemes may be rebuilt from source
        with a different build-folder hash). Create the missing paths as
        symlinks to the real libraries found in the dependency packages.
        """
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

        # index: soname -> real file, from every dependency package libdir
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
        exe = os.path.join(pkg.package_folder, "bin", "kgoldrunner")
        # KDEInstallDirs puts the game data under share/kgoldrunner/system
        # (gamedata/CMakeLists.txt installs into the "system" collection).
        data = os.path.join(pkg.package_folder, "share", "kgoldrunner",
                            "system")
        if not os.path.isfile(exe):
            raise ConanException(f"installed binary missing: {exe}")
        if not os.path.isdir(data):
            raise ConanException(f"installed gamedata missing: {data}")

        if str(self.settings.os) == "OHOS":
            self._sign(exe)
            self._prepare_runtime_links()
            self._fix_absolute_needed()

        test_env = Environment()
        for libdir in self._collect_transitive_libdirs():
            test_env.prepend_path("LD_LIBRARY_PATH", libdir)
        # openal-soft behind libkdegames: libKDEGames6.so NEEDs
        # libopenal.so.1. Find it through every visible package folder.
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            for subdir in ("lib",):
                libdir = os.path.join(dep.package_folder, subdir)
                if os.path.isdir(libdir) and any(
                    f.startswith("libopenal") for f in os.listdir(libdir)
                ):
                    test_env.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("KGR_TEST_BIN", exe)
        test_env.define("KGR_TEST_DATA_DIR", data)
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        test_env.define("HOME", test_home)

        cmd = os.path.join(self.cpp.build.bindirs[0],
                           "kgoldrunner_consumer_test")
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
