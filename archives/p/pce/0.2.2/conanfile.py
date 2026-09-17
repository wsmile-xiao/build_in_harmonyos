#!/usr/bin/env python3
"""Conan recipe — pce 0.2.2 (Autotools)"""

import os
import re
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PceConan(ConanFile):
    name = "pce"
    version = "0.2.2"
    description = "Collection of microcomputer emulators (IBM PC, Mac Plus, RC759 and simulators)"
    license = "GPL-2.0-only"
    homepage = "http://www.hampa.ch/pce/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("pce/0.2.2 supports only Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("pce/0.2.2 on OHOS supports only armv8 (aarch64)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-x",
            "--without-sdl",
            "--disable-readline",
            "--disable-tun",
            "--disable-sound-oss",
        ])
        # Upstream e68000 objects rely on common-symbol semantics
        # (multiple definition of e68_ea_tab with -fno-common on
        # GCC 10+ / clang 15, see Homebrew formula note).
        tc.extra_cflags.append("-fcommon")
        if self.settings.os == "OHOS":
            # Bundled config.sub (2013-02-12) already knows aarch64
            # and linux-gnu but not linux-ohos, so use the standard
            # linux-gnu triplet for a native OHOS build. This keeps
            # host_os matched as Linux-like without requiring a patch.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def _expected_bins(self):
        return [
            "pce-ibmpc",
            "pce-macplus",
            "pce-rc759",
            "pce-sim405",
            "pce-sim6502",
            "pce-simarm",
            "pce-sims32",
        ]

    def _find_file(self, root, name):
        """Search *name* under *root* (build or source tree)."""
        if not root or not os.path.isdir(root):
            return None
        direct = os.path.join(root, name)
        if os.path.isfile(direct):
            return direct
        for dirpath, _dirnames, filenames in os.walk(root):
            if name in filenames:
                return os.path.join(dirpath, name)
        return None

    def _patch_configure_umask(self, configure_path):
        """HMDFS workaround: strip ``umask 077`` from AS_TMPDIR temp-dir creation.

        HMDFS refuses writes into ``mktemp -d`` dirs created as drwx--S---
        (0700 + setgid), so ``config.status`` aborts with
        ``can't create ./confXXXXXX/subs1.awk: Permission denied``.
        Removing the ``umask 077 &&`` prefix lets mktemp use the default
        umask so the temp dir stays writable. Covers both ``umask`` and
        autoconf's ``umash`` misspelling, mktemp and mkdir paths.
        """
        with open(configure_path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        patched, n_mktemp = re.subn(
            r"um(?:ask|ash) 077 && mktemp -d", "mktemp -d", text)
        patched, n_mkdir = re.subn(
            r"um(?:ask|ash) 077 && mkdir", "mkdir", patched)
        if n_mktemp == 0 and n_mkdir == 0:
            # Fall back to a plain token replacement so the generated
            # config.status template (which embeds the same umask) is
            # still fixed even if the AS_TMPDIR phrasing differs.
            if "umask 077" in patched:
                patched = patched.replace("umask 077", "umask 022")
                n_mktemp = 1
            else:
                self.output.warning(
                    "configure has no AS_TMPDIR 'umask 077' pattern; "
                    "HMFS workaround not applied")
                return
        with open(configure_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(patched)
        self.output.info(
            "patched configure AS_TMPDIR: removed 'umask 077 && ' "
            "for HMFS writable tmpdir (mktemp:%d, mkdir:%d)"
            % (n_mktemp, n_mkdir))

    def _setup_hmbs_tmpdir(self):
        """[readonly_tmp] /tmp is read-only on HMDFS; keep Autoconf and all
        child processes on the HMBS-provided writable tmpdir. Only the
        temp-file root is redirected; no test is skipped or removed."""
        hmbs_tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not hmbs_tmp or hmbs_tmp == "/tmp":
            hmbs_tmp = self.build_folder
        try:
            os.makedirs(hmbs_tmp, exist_ok=True)
        except OSError:
            hmbs_tmp = self.build_folder
            os.makedirs(hmbs_tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = hmbs_tmp
        # Use HMBS-injected /bin/sh for any re-exec; Autotools helper
        # inherits this environment.
        os.environ["SHELL"] = os.environ.get("SHELL") or "/bin/sh"
        os.environ["CONFIG_SHELL"] = os.environ.get("CONFIG_SHELL") or os.environ["SHELL"]
        return hmbs_tmp

    def build(self):
        apply_conandata_patches(self)
        self._setup_hmbs_tmpdir()
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            try:
                current_mode = os.stat(configure_path).st_mode
                os.chmod(configure_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError:
                self.output.warning("chmod +x configure ignored (HMBS_CAP_CHMOD=0)")
            # [unsafe_local_mktemp] minimal fix: drop 'umask 077' so the
            # mktemp/mkdir tmpdir is writable. Deliberately NOT a mktemp
            # exit-1 shim: with HMBS_CAP_CHMOD=0 the shim is not executable
            # and the mkdir fallback itself carries 'umask 077', so the shim
            # route cannot work (buildtorrent/avahi precedent).
            self._patch_configure_umask(configure_path)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Diagnose empty-BIN installs: list what the build tree produced.
        # Upstream BIN is src/arch/*/pce-*; if configure disabled every
        # emulator (BIN empty) make still exits 0 and `make install`
        # creates an empty bin dir, which the old test reported as
        # 7/7 missing. Log the evidence here so the next preflight shows
        # whether binaries were built but not installed, or not built.
        for name in self._expected_bins():
            hit = self._find_file(self.build_folder, name)
            if hit is None and self.build_folder != self.source_folder:
                hit = self._find_file(self.source_folder, name)
            if hit is not None:
                try:
                    size = os.path.getsize(hit)
                except OSError:
                    size = -1
                self.output.info("built %s -> %s (%s bytes)" % (name, hit, size))
            else:
                self.output.warning("built %s: NOT FOUND under build/source tree" % name)

    def package(self):
        self._setup_hmbs_tmpdir()
        autotools = Autotools(self)
        autotools.install()
        # Fallback: upstream `make install` only installs $(BIN). If the
        # toolchain prefix/DESTDIR handling ever leaves bin empty while
        # the build tree holds the linked emulators, copy them manually.
        # Only the install location is repaired; no test is skipped.
        bindir = os.path.join(self.package_folder, "bin")
        try:
            os.makedirs(bindir, exist_ok=True)
        except OSError:
            pass
        for name in self._expected_bins():
            dst = os.path.join(bindir, name)
            if os.path.isfile(dst) and os.path.getsize(dst) > 0:
                continue
            src = self._find_file(self.build_folder, name)
            if src is None and self.build_folder != self.source_folder:
                src = self._find_file(self.source_folder, name)
            if src is None:
                self.output.warning(
                    "package fallback: %s not found in build tree, kept missing" % name)
                continue
            try:
                shutil.copy2(src, dst)
            except OSError as exc:
                self.output.warning(
                    "package fallback copy %s failed: %s" % (name, exc))
                continue
            try:
                mode = os.stat(dst).st_mode
                os.chmod(dst, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError:
                self.output.warning(
                    "chmod +x %s ignored (HMBS_CAP_CHMOD=0)" % name)
            self.output.info("package fallback installed %s from %s" % (name, src))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
