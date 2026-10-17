#!/usr/bin/env python3
"""Conan test_package for kwalletmanager 26.04.0.

Consumer-side verification for an application package (upstream registers
no test suite — N=0):

* Part 1 (R34): execute the installed kwalletmanager5 binary with
  --version and --help under QT_QPA_PLATFORM=offscreen; both take the
  KAboutData/QCommandLineParser early-exit path (no wallet backend, no
  event loop) and must report the 26.04.0 version.
* Part 2: verify the installed metadata contract — desktop file
  (org.kde.kwalletmanager.desktop), appstream metadata, the generated
  D-Bus service file, plus the key Exec entry ("kwalletmanager5").
* Part 3: verify the KDEInstallDirs single-prefix layout (bin/ ELF
  present and plausible).

The runtime environment mirrors the kgoldrunner 26.04.0 / libkgapi 26.04.0
precedents: every dependency lib dir (including transitive ones behind
cmake_find_mode=none packages — gettext's libintl.so.8 behind ki18n,
libxkbcommon/expat behind qtbase, qtsvg behind kiconthemes) on
LD_LIBRARY_PATH, /system/lib64 for libc++_shared.so, compatibility
symlinks for relative DT_NEEDED entries baked into the published KF6
binaries, fallback symlinks for stale absolute DT_NEEDED paths, offscreen
QPA, isolated HOME.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class KwalletmanagerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Same Qt6 anchor as the recipe: qtbase-sql-dbus/6.11.1 (complete
        # DBus module). The consumer test only needs QtCore, but requiring
        # the anchor keeps the test graph identical to the build graph.
        self.requires("qtbase-sql-dbus/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qtbase-sql-dbus uses cmake_find_mode=none: write
        # conan_cmakedeps_paths manually (kgoldrunner / audiocd precedent).
        lines = []
        qt_sql_dbus = self.dependencies.get("qtbase-sql-dbus")
        if qt_sql_dbus and qt_sql_dbus.package_folder:
            pkg = qt_sql_dbus.package_folder
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

    # ------------------------------------------------------------------
    # Runtime environment helpers (kgoldrunner 26.04.0 test precedent)
    # ------------------------------------------------------------------

    def _collect_transitive_libdirs(self):
        """Every package folder reachable in the test graph (direct +
        transitive) that carries a lib/ directory — including transitive
        requirements that no cmake config surfaces (gettext's libintl
        behind ki18n, libxkbcommon/expat behind qtbase, qtsvg behind
        kiconthemes)."""
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
        the published KF6 packages (e.g. kconfiggui's libKF6ConfigGui.so
        needs '../../bin/libKF6ConfigCore.so' relative to the process cwd —
        kgoldrunner 26.04.0 / audiocd 26.04.3 precedent). The OHOS musl
        loader resolves path-style NEEDED entries from the process CWD,
        not from LD_LIBRARY_PATH."""
        import shutil

        compat_libs = {}
        for libdir in self._collect_transitive_libdirs():
            for name in os.listdir(libdir):
                if name.endswith(".so") or ".so." in name:
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
                if not os.path.exists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def _fix_absolute_needed(self):
        """The published KF6 binaries carry build-machine absolute paths in
        DT_NEEDED (e.g. libKF6IconThemes.so behind kconfigwidgets refers
        to .../.cache/conan2/p/kicon<hash>/p/lib/...). The OHOS musl
        loader resolves path-style NEEDED entries literally; on a fresh
        worker those directories do not exist. Create the missing paths as
        symlinks to the real libraries found in the dependency packages
        (kgoldrunner 26.04.0 precedent)."""
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
            e_shnum = struct.unpack_from(
                "<H" if is_le else ">H", data, 0x3C)[0]
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
        for libdir in self._collect_transitive_libdirs():
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if os.path.isfile(full) and (
                    name.endswith(".so") or ".so." in name
                ):
                    index.setdefault(name, full)

        fixes = 0
        for libdir in self._collect_transitive_libdirs():
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

    def _sign(self, path):
        import subprocess
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True)

    # ------------------------------------------------------------------

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        pkg = self.dependencies.get(self.tested_reference_str)
        if not pkg or not pkg.package_folder:
            raise ConanException("tested package not in graph")
        exe = os.path.join(pkg.package_folder, "bin", "kwalletmanager5")
        share = os.path.join(pkg.package_folder, "share")
        if not os.path.isfile(exe):
            raise ConanException(f"installed binary missing: {exe}")

        if str(self.settings.os) == "OHOS":
            self._sign(exe)
            self._prepare_runtime_links()
            self._fix_absolute_needed()

        test_env = Environment()
        for libdir in self._collect_transitive_libdirs():
            test_env.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("KWM_TEST_BIN", exe)
        test_env.define("KWM_TEST_SHARE_DIR", share)
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", test_home)

        cmd = os.path.join(self.cpp.build.bindirs[0],
                           "kwalletmanager_consumer_test")
        with test_env.vars(self).apply():
            self.run(f"{shlex.quote(cmd)}", env="conanrun")
            self.output.info("consumer test passed")
