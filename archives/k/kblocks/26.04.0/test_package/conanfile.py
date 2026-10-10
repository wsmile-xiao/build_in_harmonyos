#!/usr/bin/env python3
"""Conan test_package for kblocks 26.04.0 (application package).

kblocks is a KDE falling blocks GUI game built on KDEGames6. Upstream ships
6 autotests (basic, KBlocksGameLogic, KBlocksItemGroup, KBlocksScene,
KBlocksWin, View-Scene) which run inside the build via ctest
(BUILD_TESTING=ON in the main recipe).

Consumer verification (R34 — must actually exercise the shipped binary):
  1. kblocks exists in the package bin/ directory and is executable
  2. kblocks --version prints the 26.04.0 version string and exits 0
     (KAboutData handles --version before the GUI window is created;
     QT_QPA_PLATFORM=offscreen keeps it headless-safe)
  3. kblocks --help prints help output (exercises Qt + KDE runtime link)
  4. kblocks --author / --license expose the KAboutData metadata resources
  5. [HarmonyOS-specific, non-assertion] shared-library closure load: launches
     the shipped kblocks binary so the OHOS dynamic linker resolves the whole
     DT_NEEDED closure. The published KF6 libraries record relative
     "../../bin/libX.so" entries which OHOS musl resolves from the symlink
     path (not realpath); without patchelf SONAME rewriting the load fails.
     On glibc the same path form resolves trivially, so this case is a real
     gate only on OHOS. Judged by process runtime behaviour (linker resolve
     success), not by matching any specific output text.

Runtime environment follows kgoldrunner 26.04.0 / kfourinline 26.04.0
precedent:
  - relative DT_NEEDED entries baked into the published KF6 packages
    ("../../bin/libKF6*.so") are patched to SONAME-only via patchelf
    (OHOS resolves relative DT_NEEDED from symlink path, not realpath,
    breaking the KF6 multi-package layout)
  - build-machine absolute DT_NEEDED entries get an absolute-NEEDED
    fallback layer
  - /system/lib64 for compatible libc++_shared.so
  - OHOS binary signature refreshed before execution
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class KblocksTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Transitive runtime DT_NEEDED of libKDEGames6 (libkdegames requires
        # set; those packages don't propagate a runenv into the consumer
        # graph — libkdegames test_package precedent):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("karchive/6.18.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kcompletion/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("knewstuff/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        # openal-soft: libKDEGames6.so links OpenAL (sound engine) — not in
        # the published libkdegames runenv, must be declared explicitly in
        # the consumer graph (kgoldrunner 26.04.0 precedent).
        self.requires("openal-soft/1.25.2")

    def _libdirs(self):
        dirs = []
        seen = set()
        for dep in self.dependencies.values():
            if not (dep and dep.package_folder):
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if libdir not in seen and os.path.isdir(libdir):
                seen.add(libdir)
                dirs.append(libdir)
        return dirs

    def _prepare_runtime_links(self):
        """Compatibility symlinks for relative DT_NEEDED entries baked into
        the published KF6 packages (kgoldrunner 26.04.0 precedent)."""
        compat_libs = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                if name.startswith("lib") and (
                    name.endswith(".so") or ".so." in name
                ):
                    compat_libs.setdefault(name, os.path.join(libdir, name))
        for base in (
            os.path.normpath(
                os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
            ),
            os.path.join(self.build_folder, "bin"),
        ):
            os.makedirs(base, exist_ok=True)
            for name, src in compat_libs.items():
                dst = os.path.join(base, name)
                if not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def _fix_relative_needed(self):
        """OHOS resolves relative DT_NEEDED entries from the symlink path
        (not the realpath), which breaks the published KF6 convention of
        "../../bin/libKF6*.so". Patch them to SONAME-only so the OHOS
        dynamic linker resolves them via LD_LIBRARY_PATH."""
        import subprocess

        patchelf = "/data/service/hnp/bin/patchelf"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"

        def elf_needed(path):
            import struct
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
                if sh_type == 3:
                    dynstr = off
                elif sh_type == 6:
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
                        if tag == 1:
                            s = str_off + val
                            e = data.index(b"\x00", s)
                            needed.append(data[s:e].decode("utf-8", "replace"))
                        p += 16
            return needed

        fixes = 0
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if not os.path.isfile(full):
                    continue
                if not (name.endswith(".so") or ".so." in name):
                    continue
                for entry in elf_needed(full):
                    if not entry.startswith("../"):
                        continue
                    soname = os.path.basename(entry)
                    self.output.info(
                        f"patching relative DT_NEEDED {entry} -> {soname} "
                        f"in {name}")
                    subprocess.run(
                        [objcopy, "--remove-section", ".codesign", full],
                        check=True)
                    subprocess.run(
                        [patchelf, "--replace-needed", entry, soname, full],
                        check=True)
                    subprocess.run(
                        [signer, "sign", "-inFile", full, "-outFile", full,
                         "-selfSign", "1"],
                        check=True)
                    fixes += 1
        if fixes:
            self.output.info(
                f"patched {fixes} relative DT_NEEDED entries")

    def _fix_absolute_needed(self):
        """The published KF6/KDEGames6 binaries carry build-machine
        absolute paths in DT_NEEDED. Create missing paths as symlinks
        (kgoldrunner 26.04.0 precedent)."""
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
                if sh_type == 3:
                    dynstr = off
                elif sh_type == 6:
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
                        if tag == 1:
                            s = str_off + val
                            e = data.index(b"\x00", s)
                            needed.append(data[s:e].decode("utf-8", "replace"))
                        p += 16
            return needed

        index = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if os.path.isfile(full) and (
                    name.endswith(".so") or ".so." in name
                ):
                    index.setdefault(name, full)

        fixes = 0
        scan_roots = list(self._libdirs())
        pkg = self.dependencies.get("kblocks")
        pkg_bin = None
        if pkg and pkg.package_folder:
            pkg_bin = os.path.join(pkg.package_folder, "bin")
            if os.path.isdir(pkg_bin):
                scan_roots.append(pkg_bin)
        for root in scan_roots:
            for name in os.listdir(root):
                full = os.path.join(root, name)
                if not os.path.isfile(full):
                    continue
                is_elfish = name.endswith(".so") or ".so." in name
                if root != pkg_bin and not is_elfish:
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
            self.output.info(f"created {fixes} absolute-NEEDED fallback symlinks")

    def _sign(self, path):
        import subprocess
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True)

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["kblocks"]
        kblocks_bin = os.path.join(pkg.package_folder, "bin", "kblocks")
        if not os.path.isfile(kblocks_bin):
            raise ConanException(f"kblocks binary not found: {kblocks_bin}")

        if str(self.settings.os) == "OHOS":
            self._sign(kblocks_bin)
            self._prepare_runtime_links()
            self._fix_relative_needed()
            self._fix_absolute_needed()

        lib_dirs = self._libdirs()
        farm_dir = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        ld_path = os.pathsep.join(["/system/lib64", farm_dir] + lib_dirs)

        plugin_dirs = []
        platforms = []
        for p in self.dependencies.values():
            if p.package_folder:
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    d = os.path.join(p.package_folder, rel)
                    if os.path.isdir(d):
                        plugin_dirs.append(d)
                    pd = os.path.join(d, "platforms")
                    if os.path.isdir(pd):
                        platforms.append(pd)

        env = Environment()
        env.append("LD_LIBRARY_PATH", ld_path)
        env.define("QT_QPA_PLATFORM", "offscreen")
        for d in plugin_dirs:
            env.append("QT_PLUGIN_PATH", d)
        for d in platforms:
            env.append("QT_QPA_PLATFORM_PLUGIN_PATH", d)
        env.define("XDG_RUNTIME_DIR", self.build_folder)
        env.define("HOME", self.build_folder)

        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(os.pathsep)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if platforms:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.pathsep.join(
                platforms
            )
            os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_dirs)

        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        with env.vars(self).apply():
            self.run(
                f'{shlex.quote(shell)} '
                f'{shlex.quote(os.path.join(self.source_folder, "test.sh"))} '
                f'{shlex.quote(kblocks_bin)}',
                cwd=self.build_folder,
            )
        self.output.info("kblocks consumer smoke passed")
