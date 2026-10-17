#!/usr/bin/env python3
"""Conan test_package for ktuberling 26.04.0 (application package).

ktuberling is a GUI game (QApplication). Upstream registers no test suite
(N=0: no tests/, autotests/ or add_test() in the 26.04.0 tarball), so the
consumer verification is a runtime smoke of the shipped executable
(kfourinline 26.04.0 / kgoldrunner 26.04.0 pattern):

  1. the binary exists in the package bin/ directory
  2. ktuberling --version prints the 26.04.0 version string and exits 0
     (KAboutData::setupCommandLine wires --version before the GUI main
     window is created; QT_QPA_PLATFORM=offscreen keeps it headless-safe)

Runtime environment (kgoldrunner 26.04.0 precedent):
  - relative DT_NEEDED entries baked into the published KF6 packages
    ("../../bin/libKF6*.so") are resolved through compatibility symlinks
  - build-machine absolute DT_NEEDED entries get an absolute-NEEDED
    fallback layer: the missing paths are created as symlinks to the real
    libraries found in the dependency packages (the OHOS musl loader
    resolves path-style NEEDED entries literally, no LD_LIBRARY_PATH
    fallback)
  - /system/lib64 for the compatible libc++_shared.so
  - the OHOS binary signature is refreshed before execution (freshly built
    executables need a .codesign section to be executable)
The assertion lives in test.sh (POSIX sh, augustus-game pattern).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class KtuberlingTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Transitive runtime DT_NEEDED of libKDEGames6/libKDEGames6Private
        # and libKF6KIOCore (the libkdegames/kio requires set; those
        # packages don't propagate a runenv into the consumer graph, so
        # they must be declared here for the LD_LIBRARY_PATH collection -
        # libkdegames test_package precedent):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("qtmultimedia/6.11.1")
        self.requires("karchive/6.18.0")
        self.requires("kauth/6.18.0")
        self.requires("kbookmarks/6.18.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kcompletion/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("kio/6.14.0")
        self.requires("kitemviews/6.18.0")
        self.requires("kjobwidgets/6.18.0")
        self.requires("knewstuff/6.18.0")
        self.requires("kservice/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kwindowsystem/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("solid/6.18.0")
        self.requires("openal-soft/1.25.2")
        self.requires("libsndfile/1.2.2")

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
        the published KF6 packages ("../../bin/libKF6*.so" relative to the
        process cwd — audiocd 26.04.3 / libkcddb / kgoldrunner 26.04.0
        precedent)."""
        compat_libs = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                if name.startswith("lib") and (
                    name.endswith(".so") or ".so." in name
                ):
                    compat_libs.setdefault(name, os.path.join(libdir, name))
        # the relative path is resolved from cwd (the test runs from the
        # build folder): provide <build>/../../bin and <build>/bin farms
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

    def _fix_absolute_needed(self):
        """The published KF6/KDEGames6 binaries carry build-machine
        absolute paths in DT_NEEDED (e.g. libKF6XmlGui.so needs
        .../p/kicon<hash>/p/lib/libKF6IconThemes.so, libKDEGames6.so needs
        .../p/b/kicon<hash>/...). The OHOS musl loader resolves path-style
        NEEDED entries literally with no LD_LIBRARY_PATH fallback, and on a
        fresh worker those directories do not exist. Create the missing
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

        # index: soname -> real file, from every dependency package libdir
        index = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if os.path.isfile(full) and (
                    name.endswith(".so") or ".so." in name
                ):
                    index.setdefault(name, full)

        fixes = 0
        # scan every dependency libdir AND the tested package's own bin/
        # executable (its DT_NEEDED also carry build-machine absolute
        # paths: the linking machine resolved the KF6 deps into its own
        # cache layout).
        scan_roots = list(self._libdirs())
        pkg = self.dependencies.get("ktuberling")
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
                            try:
                                os.symlink(source, entry)
                                fixes += 1
                            except OSError:
                                # 部分主机沙箱域禁止 symlink 系统调用（本机
                                # cmd-pkgs python3 实测 EACCES，CI 的
                                # /data/app/bin/python3 不受限，softlink
                                # 先例 kfourinline/kgoldrunner 全绿）；退化为
                                # 实文件拷贝，与 _prepare_runtime_links 的
                                # copy2 兑底同款。
                                shutil.copy2(source, entry)
                                fixes += 1
                    except OSError as e:
                        self.output.warning(
                            f"cannot create NEEDED fallback {entry}: {e}")
        if fixes:
            self.output.info(
                "created %d absolute-NEEDED compatibility links" % fixes)

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
        pkg = self.dependencies["ktuberling"]
        gui = os.path.join(pkg.package_folder, "bin", "ktuberling")
        if not os.path.isfile(gui):
            raise ConanException(f"ktuberling binary not found: {gui}")

        farm_dir = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        if str(self.settings.os) == "OHOS":
            self._sign(gui)
            self._prepare_runtime_links()
            self._fix_absolute_needed()

        lib_dirs = self._libdirs()
        ld_path = os.pathsep.join(["/system/lib64", farm_dir] + lib_dirs)

        # Qt platform plugins (offscreen) live in the qtbase package
        # (plugins/platforms or lib/plugins/platforms).
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

        # conan's self.run() may spawn a fresh shell environment that
        # drops the appended loader vars; persist them via os.environ so
        # the subprocess inherits them (khealthcertificate 26.04.3
        # precedent, belt-and-braces with env.vars above).
        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(os.pathsep)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if platforms:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.pathsep.join(
                platforms
            )
            os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_dirs)

        # test.sh uses POSIX shell syntax (augustus-game pattern; avoids
        # binding to a bash install path on the target device).
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        with env.vars(self).apply():
            self.run(
                f'{shlex.quote(shell)} '
                f'{shlex.quote(os.path.join(self.source_folder, "test.sh"))} '
                f'{shlex.quote(gui)}',
                cwd=self.build_folder,
            )
        self.output.info("ktuberling runtime smoke passed")
