#!/usr/bin/env python3
"""Conan test_package for ksystemlog 26.04.0 (application package).

ksystemlog is a GUI application (the KDE system log viewer, QApplication
main window). Upstream registers a real test suite (autotests/: 4
ecm_add_test entries - logModeFactoryTest, systemAnalyzerTest,
kernelAnalyzerTest, kioLogFileReaderTest) which is exercised on-device
with BUILD_TESTING=ON during adaptation (results in notes.md and
reports/test-report.md: 4/4 passed). The conan test_package performs the
consumer-verification runtime smoke of the shipped executable
(kfourinline 26.04.0 / kgoldrunner 26.04.0 pattern):

  1. the binary exists in the package bin/ directory
  2. ksystemlog --version prints the 26.04.0 version string and exits 0
     (QCommandLineParser/KAboutData handle --version before the GUI main
     window is created; QT_QPA_PLATFORM=offscreen keeps it headless-safe)
  3. ksystemlog --help prints the usage banner ("System Logs Viewer by
     KDE") and exits 0 (command-line parsing exercises the full
     KAboutData/KXmlGui initialization path up to the point where the GUI
     main loop would start)

Runtime environment (kfourinline 26.04.0 precedent):
  - relative DT_NEEDED entries baked into the published KF6 packages
    ("../../bin/libKF6*.so" / "../../bin/libzstd.so.1") are resolved
    through compatibility symlink farms at <build>/bin and
    <build>/../../bin (the OHOS musl loader resolves path-style NEEDED
    entries relative to the process cwd, no LD_LIBRARY_PATH fallback)
  - build-machine absolute DT_NEEDED entries (the published KF6 6.14.0
    packages carry "$HOME/.cache/conan2/p/<pkg>/p/lib/libKF6*.so" paths
    from the release worker) get an absolute-NEEDED fallback layer: the
    missing paths are created as symlinks to the real libraries found in
    the dependency packages (the OHOS musl loader resolves path-style
    NEEDED entries literally, no LD_LIBRARY_PATH fallback)
  - /system/lib64 for the compatible libc++_shared.so
  - the OHOS binary signature is refreshed before execution (freshly
    built executables need a .codesign section to be executable)
The assertions live in test.sh (POSIX sh, augustus-game pattern).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class KsystemlogTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Full transitive runtime DT_NEEDED closure of the ksystemlog
        # binary and the published KF6 6.14.0 packages (their recipes do
        # not propagate a runenv into the consumer graph, so they must be
        # declared here for the lib-dir collection - kfourinline
        # test_package precedent).
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.14.0")
        self.requires("kconfigwidgets/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("kcrash/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("karchive/6.14.0")
        self.requires("kitemviews/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("kcompletion/6.14.0")
        self.requires("ktextwidgets/6.14.0")
        self.requires("kio/6.14.0")
        self.requires("kxmlgui/6.14.0")

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
        """Compatibility symlink farms for relative DT_NEEDED entries baked
        into the published KF6 packages ("../../bin/libKF6*.so" and
        "../../bin/libzstd.so.1" relative to the process cwd - kfourinline
        26.04.0 / kgoldrunner 26.04.0 precedent). Provide <build>/bin and
        <build>/../../bin farms; every symlink name variant of every
        dependency library (real files AND their .so/.so.N symlink
        aliases, dereferenced) is farmed - the karchive NEEDED entry
        libzstd.so.1 needs the symlink-variant names too."""
        compat_libs = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                if name.startswith("lib") and (
                    name.endswith(".so") or ".so." in name
                ):
                    full = os.path.join(libdir, name)
                    real = (
                        os.path.realpath(full)
                        if os.path.islink(full)
                        else full
                    )
                    compat_libs.setdefault(name, real)
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
        """The published KF6 6.14.0 binaries carry build-machine absolute
        paths in DT_NEEDED (e.g. libKF6KIOCore.so needs
        $HOME/.cache/conan2/p/kio<hash>/p/lib/libKF6Service.so; the
        release worker used a $HOME/.cache/conan2 layout while fresh
        environments may use a different cache root). The OHOS musl loader
        resolves path-style NEEDED entries literally with no
        LD_LIBRARY_PATH fallback, and on a fresh worker those directories
        do not exist. Create the missing paths as symlinks to the real
        libraries found in the dependency packages (kfourinline 26.04.0
        precedent)."""
        import struct

        def elf_needed(path):
            """Minimal ELF DT_NEEDED extractor (no readelf dependency).
            The .dynstr section is located via the SHT_DYNAMIC section's
            sh_link (multiple SHT_STRTAB sections exist: .dynstr AND
            .shstrtab - picking the first SHT_STRTAB would pick the wrong
            table and yield truncated strings)."""
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
            if e_shoff + e_shnum * e_shentsize > len(data):
                return []

            def sh_field(i, fmt, byteoff):
                off = e_shoff + i * e_shentsize + byteoff
                if off + struct.calcsize(fmt) > len(data):
                    return None
                return struct.unpack_from(
                    "<" + fmt if is_le else ">" + fmt, data, off)[0]

            # locate the dynamic section and its string table (sh_link)
            dyn_idx, dyn_off, dyn_size = None, None, None
            for i in range(e_shnum):
                if sh_field(i, "H", 4) == 6:  # SHT_DYNAMIC
                    dyn_idx = i
                    dyn_off = sh_field(i, "Q", 0x18)
                    dyn_size = sh_field(i, "Q", 0x20)
                    break
            if dyn_idx is None:
                return []
            dynstr_off = sh_field(dyn_idx, "I", 0x28)  # sh_link -> index
            if dynstr_off is None or dynstr_off >= e_shnum:
                return []
            dynstr = sh_field(dynstr_off, "Q", 0x18)
            if dynstr is None:
                return []
            needed = []
            p, end = dyn_off, dyn_off + dyn_size
            while p + 16 <= end and p + 16 <= len(data):
                tag, val = struct.unpack_from(
                    "<QQ" if is_le else ">QQ", data, p)
                if tag == 0:
                    break
                if tag == 1:  # DT_NEEDED
                    s = dynstr + val
                    e = data.find(b"\x00", s)
                    if e == -1:
                        break
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
        # executables (their DT_NEEDED also carry build-machine absolute
        # paths: the linking machine resolved the KF6 deps into its own
        # cache layout).
        scan_roots = list(self._libdirs())
        pkg = self.dependencies.get("ksystemlog")
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

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["ksystemlog"]
        gui = os.path.join(pkg.package_folder, "bin", "ksystemlog")
        if not os.path.isfile(gui):
            raise ConanException(f"ksystemlog binary not found: {gui}")

        if str(self.settings.os) == "OHOS":
            self._sign(gui)
            self._prepare_runtime_links()
            self._fix_absolute_needed()

        lib_dirs = self._libdirs()
        farm_dir = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
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
        self.output.info("ksystemlog runtime smoke passed")
