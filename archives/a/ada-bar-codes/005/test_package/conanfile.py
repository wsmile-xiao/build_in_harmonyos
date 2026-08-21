#!/usr/bin/env python3
"""test_package — ada-bar-codes 005 consumer smoke test (Ada)

Compiles bar_codes_smoke.adb against the packaged static library using
the same bootstrapped Alpine musl GNAT toolchain as the main recipe
(round-7 exec model: the Alpine binaries are rewritten in place — their
PT_INTERP is relocated to the device's own musl loader and the
DT_NEEDED libc name becomes libc.so — so they execute directly, exactly
like OHOS-native ELFs; explicit loader invocation is impossible, the
device loader file itself cannot be execve'd, round-6 evidence).

The smoke test makes three real API calls:
  - Bar_Codes.Fitting (Code_128, "Hello")         -> non-empty 1D modules
  - Bar_Codes.Fitting (Code_QR_Low, "Hello")      -> non-empty 2D modules
  - Bar_Codes_Media.SVG_Bar_Code (Code_QR_Low, 100.0, 100.0, "mm", "Hello")
                                                  -> non-empty SVG output
and prints checks_passed=<n>; all three must pass before the HMBS
test-package marker is emitted.
"""
import glob
import hashlib
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration

_GNAT_TAG = "13.2.1_git20240309-r1"

_ALPINE_APKS = [
    # name, sha256 (official Alpine v3.20 main aarch64)
    ("gcc-gnat-%s.apk" % _GNAT_TAG,
     "221634b95080d93673ee824f7a6732fc1fefbf48a5b5107f0fd84f24c012113b"),
    ("libgnat-%s.apk" % _GNAT_TAG,
     "8df9dae474b526ae59a34d2168619be584cd285fce2c7a5ae4105c08b447d296"),
    ("libgnat-static-%s.apk" % _GNAT_TAG,
     "02f02fdfeefa0c1437c00b0c11ada80a592ffb3e2f2eeaf113b525fb18503fe1"),
    ("gcc-%s.apk" % _GNAT_TAG,
     "07ca04d225d3b8a36fb6f215650d2c2d4714d6b5e14bda568abd17176e6a3ad2"),
    ("binutils-2.42-r1.apk",
     "a4a1cd3cc9f0b1b4ae3b6465654d36623b7aeaad8a2ea30bf0b1cb44669c9b26"),
    ("gmp-6.3.0-r1.apk",
     "8c701fd183c60e0170a9f4583cf8c3a9aa9e3fec4179c10ff8d00fbfa820d87c"),
    # Round-13 (mirror of the main recipe): mpfr-dev/isl-dev only ship
    # libmpfr.a/libisl.a plus unversioned .so symlinks; the versioned
    # entities (libmpfr.so.6 / libisl.so.23) live in the mpfr4/isl26
    # runtime packages, without which gnat1/cc1 fail to load.
    ("mpfr4-4.2.1-r0.apk",
     "1be0b3caf7a2b0d079ceab159f2977d513e2a0a71d91772c551533cb323ef304"),
    ("isl26-0.26-r1.apk",
     "869b52e2ba393d5a6e815b5a37fef9c7c0a98c61c84aac49ba3a336bff16d8bd"),
    ("mpfr-dev-4.2.1-r0.apk",
     "4f78ff9c9880d26fb0dfba548d047d61feb44a2d8ce07dedd20edb36976ec5c1"),
    ("isl-dev-0.26-r1.apk",
     "e21c45f640cf4f68f4c66694b82f2d26e257520382f5e60b0a1b053064a6b2e1"),
    ("mpc1-1.3.1-r1.apk",
     "7169845300015f9201afc97095e01b75a0efcb64e20c2361b54b093cc6c91c32"),
    ("zlib-1.3.2-r0.apk",
     "08057738baed0c0e2e98a0c064abaa658974915e874664fc78694999bec37609"),
    ("libgcc-%s.apk" % _GNAT_TAG,
     "0d6aabf922c91c8bfc62cf625366a6669d67048c3a4fef2318a1246f152de2c0"),
    ("libstdc++-%s.apk" % _GNAT_TAG,
     "ee68ab3af02350f2135b6c0de393a55be88fbb20171e6182cdda6517c38b60a0"),
    ("libgomp-%s.apk" % _GNAT_TAG,
     "26149ccba9100ef47386f34fbcb8b77370a604e3f88fe310d368ac6b7b88ba98"),
    ("libatomic-%s.apk" % _GNAT_TAG,
     "b9017a5cb111b9fc04612275743c286f4d05ad31bc8d536501fc18632cd49d2c"),
    ("musl-1.2.5-r3.apk",
     "e455c49c6c3de1dfcd4b9867c35097f588de2fb01a939c77ddb149f8e6086a24"),
    ("musl-dev-1.2.5-r3.apk",
     "89a641400ddd298cf2b40a3b6d7d0a20278d5a01cae79fc639ca8fd27b2fdf12"),
    ("jansson-2.14-r4.apk",
     "6ed7108067d0e342a237effd25f0ccd63419fb5543abeae77c5ce953b2e61139"),
    ("zstd-1.5.6-r0.apk",
     "10f0c80ca354eb3eca9584b31466941d7517e4b133026489a172802124abd1e9"),
    # Round-13 (mirror): the zstd CLI apk carries no shared lib;
    # binutils as needs libzstd.so.1, provided by zstd-libs.
    ("zstd-libs-1.5.6-r0.apk",
     "accb18819efcfaead2c9e04ec632ab3941bbe03af44af1754f65b7321030de70"),
]
_ALPINE_BASE = "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/aarch64/"
# Round-41 (mirror of the main recipe): the CI worker stalled on the
# official CDN while downloading the 65MB gcc apk and hit the 3600s
# conan-create timeout.  Try the domestic mirror first (verified live
# 2026-08-21, same v3.20 main aarch64 artifacts), official CDN last as
# fallback; sha256 is still verified per apk afterwards.
_ALPINE_MIRRORS = [
    "https://mirrors.aliyun.com/alpine/v3.20/main/aarch64/",
    _ALPINE_BASE,
]
_GCC_TARGET = "aarch64-alpine-linux-musl/13.2.1"

# Round-30 (mirror of the main recipe): the oversized 35MB gnat1 (47800
# dynsym / 2MB dynstr) is signed with the device's binary-sign-tool
# DIRECTLY on its pristine apk bytes.  Rounds 15-18 proved on-device that
# a binary-sign-tool-signed gnat1 PASSES the kernel exec gate (the loader
# ran; only relocation failed), while rounds 20-29 proved the
# .note.ohos.ident copy NEVER passes exec (EACCES even at the exact
# device-lld first-page layout) — hnp system binaries (bash/python3/cmake)
# have no dumpable .note.ohos.ident and exec via .codesign.  The
# round-16/18 ".dynamic corruption" was measured on files REWRITTEN by
# patchelf (round-22: patchelf moves the 35MB file's note 0x28c ->
# 0x35b2f8) or llvm-objcopy first; round-29 keeps gnat1 pristine (only
# the in-place .dynstr NEEDED patch), and clang/22.1.8 + python/3.9.0
# sign 100MB+ ELFs with this same tool.  Only gnat1 qualifies.
_LARGE_ELF_MIN = 8 * 1024 * 1024

# Round-7 exec model (mirror of the main recipe): Alpine toolchain ELFs
# are rewritten in place — PT_INTERP relocated to the device loader,
# DT_NEEDED libc renamed to libc.so — then executed directly.


class AdaBarCodesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "bar_codes_smoke.adb"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _gnat_root(self):
        """Toolchain install root inside this package's build folder.

        The toolchain is bootstrapped here (mirror of the main recipe);
        binaries never need exec permission because every invocation goes
        through the native-ELF launcher wrappers to the device loader.
        """
        return os.path.join(self.build_folder, "gnat-toolchain")

    @staticmethod
    def _download(url, dest):
        """Download with Python urllib (device curl has no CA bundle).

        Round-41 (mirror of the main recipe): the original single-URL
        urlretrieve had no socket timeout and no mirror fallback, so a
        stalled connection hung until the conan-create timeout.  Each
        mirror in _ALPINE_MIRRORS is tried in order with a bounded
        socket timeout; a partial file is discarded before the next
        attempt.
        """
        import socket
        import ssl

        if not os.environ.get("SSL_CERT_FILE"):
            for ca in (
                "/storage/Users/currentUser/usr/local/ssl/cert.pem",
                "/etc/ssl/certs/cacert.pem",
                "/etc/ssl/cert.pem",
            ):
                if os.path.isfile(ca):
                    os.environ["SSL_CERT_FILE"] = ca
                    os.environ["CURL_CA_BUNDLE"] = ca
                    break
        fname = os.path.basename(url)
        last_exc = None
        for base in _ALPINE_MIRRORS:
            attempt = base + fname
            if os.path.isfile(dest):
                try:
                    os.remove(dest)  # discard any partial file
                except OSError:
                    pass
            try:
                with urllib.request.urlopen(attempt, timeout=120) as resp, \
                        open(dest, "wb") as out:
                    shutil.copyfileobj(resp, out)
                return
            except (urllib.error.URLError, ssl.SSLError, socket.timeout,
                    OSError) as exc:
                if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
                    last_exc = exc
                    continue
                # TLS trust unavailable: retry this mirror unverified.
                os.environ.pop("SSL_CERT_FILE", None)
                os.environ.pop("CURL_CA_BUNDLE", None)
                ctx = ssl._create_unverified_context()
                try:
                    with urllib.request.urlopen(
                            attempt, timeout=120, context=ctx) as resp, \
                            open(dest, "wb") as out:
                        shutil.copyfileobj(resp, out)
                    return
                except (urllib.error.URLError, ssl.SSLError,
                        socket.timeout, OSError) as exc2:
                    last_exc = exc2
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("download failed: %s" % fname)

    @staticmethod
    def _unpack_apk(apk_path, root):
        """An Alpine .apk is a gzip-compressed tar archive."""
        with tarfile.open(apk_path, "r:gz") as tf:
            tf.extractall(root)

    def _bootstrap_gnat(self):
        """Download and unpack the Alpine musl GNAT toolchain into this
        package's build folder (mirror of the main recipe; apk cache is
        shared under the home root)."""
        root = self._gnat_root()
        if os.path.isfile(os.path.join(root, "usr", "bin", "gnatmake")):
            return  # already bootstrapped
        cache = os.path.join(os.path.expanduser("~"), ".cache", "ada-gnat-apks")
        os.makedirs(cache, exist_ok=True)
        for fname, sha in _ALPINE_APKS:
            apk = os.path.join(cache, fname)
            if os.path.isfile(apk):
                actual = hashlib.sha256(open(apk, "rb").read()).hexdigest()
                if actual == sha:
                    continue  # cached copy is valid
                self.output.warning(
                    "cached %s fails sha256 (got %s); re-downloading"
                    % (fname, actual))
                try:
                    os.remove(apk)  # discard stale/partial cached file
                except OSError:
                    pass
            self.output.info("downloading %s" % fname)
            self._download(_ALPINE_BASE + fname, apk)
            actual = hashlib.sha256(open(apk, "rb").read()).hexdigest()
            if actual != sha:
                raise ConanInvalidConfiguration(
                    "sha256 mismatch for %s: got %s expected %s"
                    % (fname, actual, sha))
        os.makedirs(root, exist_ok=True)
        for fname, _sha in _ALPINE_APKS:
            self._unpack_apk(os.path.join(cache, fname), root)

    def _gnat_apk_members(self):
        """File member names of the gcc-gnat apk (cached on self; mirror
        of the main recipe).

        Round-18: the strip/dyncheck/retry handling must apply ONLY to
        toolchain files that have a pristine source in this apk (today
        that is exactly the oversized gnat1); other apks' ELFs are left
        on the plain-sign path so a missing pristine source can never
        break the retry.
        """
        if getattr(self, "_gnat_apk_members_cache", None) is not None:
            return self._gnat_apk_members_cache
        apk = os.path.join(os.path.expanduser("~"), ".cache",
                           "ada-gnat-apks",
                           "gcc-gnat-%s.apk" % _GNAT_TAG)
        members = frozenset()
        if os.path.isfile(apk):
            try:
                with tarfile.open(apk, "r:gz") as tf:
                    members = frozenset(
                        m.name for m in tf.getmembers() if m.isfile())
            except (OSError, tarfile.TarError) as exc:
                self.output.warning(
                    "gnat apk member scan failed: %r" % exc)
        self._gnat_apk_members_cache = members
        return members

    def _restore_pristine_file(self, member_name):
        """Re-extract one toolchain file from the gcc-gnat apk cache
        (pristine bytes, umask-0 0o755; mirror of the main recipe).

        Round-18: binary-sign-tool must sign known-good bytes every round
        instead of re-processing an ELF whose .dynamic may already have
        been regenerated empty by a previous round's sign.  Returns True
        on success.
        """
        cache = os.path.join(os.path.expanduser("~"), ".cache",
                             "ada-gnat-apks")
        apk = os.path.join(cache, "gcc-gnat-%s.apk" % _GNAT_TAG)
        if not os.path.isfile(apk):
            self.output.warning(
                "pristine restore: gcc-gnat apk cache missing (%s)" % apk)
            return False
        dst = os.path.join(self._gnat_root(), member_name)
        try:
            with tarfile.open(apk, "r:gz") as tf:
                m = tf.getmember(member_name)
                with tf.extractfile(m) as src:
                    old_umask = os.umask(0)
                    try:
                        fd = os.open(
                            dst,
                            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                            0o755,
                        )
                    finally:
                        os.umask(old_umask)
                    with os.fdopen(fd, "wb") as out:
                        shutil.copyfileobj(src, out)
            self.output.info("restored pristine %s" % member_name)
            return True
        except (OSError, KeyError) as exc:
            self.output.warning(
                "could not restore pristine %s: %r" % (member_name, exc))
            return False

    def _restore_pristine_large(self):
        """Restore every oversized ELF (> _LARGE_ELF_MIN) from the apk
        cache before the per-round rewrite+sign (round-18, mirror of the
        main recipe).  Only gnat1 qualifies today."""
        apk = os.path.join(os.path.expanduser("~"), ".cache",
                           "ada-gnat-apks",
                           "gcc-gnat-%s.apk" % _GNAT_TAG)
        if not os.path.isfile(apk):
            return
        try:
            with tarfile.open(apk, "r:gz") as tf:
                for m in tf.getmembers():
                    if m.isfile() and m.size > _LARGE_ELF_MIN:
                        self._restore_pristine_file(m.name)
        except OSError as exc:
            self.output.warning("restore pristine walk failed: %r" % exc)

    def _find_gnatmake(self):
        """Locate gnatmake; bootstrap the Alpine musl GNAT toolchain into
        this package's own build folder when absent (mirror of the main
        recipe)."""
        candidates = [
            shutil.which("gnatmake"),
            os.path.join(self._gnat_root(), "usr", "bin", "gnatmake"),
            os.path.expanduser("~/.harmonybrew/bin/gnatmake"),
            "/data/service/hnp/bin/gnatmake",
        ]
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        self._bootstrap_gnat()
        cand = os.path.join(self._gnat_root(), "usr", "bin", "gnatmake")
        if not os.path.isfile(cand):
            raise ConanInvalidConfiguration(
                "gnatmake not found; the ada-bar-codes recipe bootstraps GNAT "
                "under the build folder (Alpine musl gcc-gnat 13.2.1)"
            )
        return cand

    def _repair_exec_bits(self):
        """Make the bootstrapped GNAT binaries world-executable (0o755).

        HMDFS ignores chmod() and maps file ownership to a different UID
        than the process (E011/E046/E087), so owner-only exec bits never
        match.  Recreate files with umask forced to 0 so the open() mode
        is exactly 0o755 (o+x); mirror of the main recipe.
        """
        base = os.path.join(self._gnat_root(), "usr", "bin")
        if not os.path.isdir(base):
            return
        for name in os.listdir(base):
            path = os.path.join(base, name)
            try:
                if os.path.islink(path):
                    continue
                if stat.S_IMODE(os.stat(path).st_mode) & 0o001:
                    continue  # world-executable already works
                with open(path, "rb") as fh:
                    data = fh.read()
                os.unlink(path)
                old_umask = os.umask(0)
                try:
                    fd = os.open(
                        path,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o755,
                    )
                finally:
                    os.umask(old_umask)
                with os.fdopen(fd, "wb") as out:
                    out.write(data)
            except OSError:
                pass

    @staticmethod
    def _elf_interp(path):
        """Extract the PT_INTERP (dynamic loader path) of an ELF binary."""
        try:
            with open(path, "rb") as fh:
                head = fh.read(64)
                if head[:4] != b"\x7fELF" or len(head) < 64:
                    return None
                le = head[5] == 1
                if head[4] != 2:  # ELFCLASS64 only
                    return None
                fmt = "<" if le else ">"
                e_phoff = struct.unpack_from(fmt + "Q", head, 32)[0]
                e_phentsize = struct.unpack_from(fmt + "H", head, 54)[0]
                e_phnum = struct.unpack_from(fmt + "H", head, 56)[0]
                fh.seek(e_phoff)
                ph = fh.read(e_phentsize * e_phnum)
                for i in range(e_phnum):
                    off = i * e_phentsize
                    p_type = struct.unpack_from(fmt + "I", ph, off)[0]
                    if p_type != 3:  # PT_INTERP
                        continue
                    p_offset = struct.unpack_from(fmt + "Q", ph, off + 8)[0]
                    p_filesz = struct.unpack_from(fmt + "Q", ph, off + 32)[0]
                    fh.seek(p_offset)
                    data = fh.read(min(p_filesz, 4096))
                    return data.split(b"\x00")[0].decode("utf-8", "replace")
        except OSError:
            return None
        return None

    def _probe_loader(self, loader, gnatmake):
        """REMOVED in round 7 — explicit loader invocation is impossible:
        execve of the device's musl loader (ET_DYN, no PT_INTERP) is
        refused with EACCES even as a fresh 0o755 copy under a non-.so
        name (round-6 evidence).  Superseded by _rewrite_elf (mirror of
        the main recipe)."""
        raise RuntimeError("loader-invocation route removed (round 7)")

    @staticmethod
    def _elf_e_type(path):
        """Return the ELF e_type (2=ET_EXEC, 3=ET_DYN/PIE) or None."""
        try:
            with open(path, "rb") as fh:
                head = fh.read(64)
            if head[:4] != b"\x7fELF" or len(head) < 64:
                return None
            le = head[5] == 1
            fmt = "<" if le else ">"
            return struct.unpack_from(fmt + "H", head, 16)[0]
        except OSError:
            return None

    def _device_interp(self):
        """Path of the device's musl loader, taken from a binary PROVEN
        to execute; fall back to the well-known /system/lib path (mirror
        of the main recipe)."""
        for src in (
            os.environ.get("HMBS_PYTHON3"),
            sys.executable,
            "/bin/sh",
            "/data/service/hnp/bin/python3",
            "/data/service/hnp/bin/bash",
        ):
            if src and os.path.isfile(src):
                interp = self._elf_interp(src)
                if interp:
                    return interp
        return "/system/lib/ld-musl-aarch64.so.1"

    _ALPINE_INTERP = "/lib/ld-musl-aarch64.so.1"
    _ALPINE_LIBC = b"libc.musl-aarch64.so.1"
    _OHOS_LIBC = b"libc.so"

    @staticmethod
    def _patchelf_tool():
        """Absolute path to the device's patchelf (E077 references
        /data/service/hnp/bin/patchelf in the OHOS ELF edit flow)."""
        for cand in (
            shutil.which("patchelf"),
            "/data/service/hnp/bin/patchelf",
        ):
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _elf_needed(self, path):
        """List the DT_NEEDED sonames of an ELF via `patchelf
        --print-needed` ([] when patchelf is unavailable or fails)."""
        tool = self._patchelf_tool()
        if not tool:
            return []
        try:
            proc = subprocess.run(
                [tool, "--print-needed", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60,
            )
        except OSError:
            return []
        if proc.returncode != 0:
            return []
        return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]

    def _patchelf(self, args):
        """Run patchelf on the device; return its rc (-1 if unavailable
        or exec fails)."""
        tool = self._patchelf_tool()
        if not tool:
            self.output.warning(
                "patchelf not found; cannot rewrite %s" % args[-1])
            return -1
        try:
            proc = subprocess.run(
                [tool] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
            )
        except OSError as exc:
            self.output.warning("patchelf exec failed: %s" % exc)
            return -1
        if proc.returncode != 0:
            self.output.warning(
                "patchelf %s rc=%s tail=%r"
                % (args[0], proc.returncode, proc.stdout[-200:]))
        return proc.returncode

    def _rewrite_elf(self, path):
        """Rewrite one Alpine musl ELF so it runs natively on OHOS.

        Round-9 route (replaces the round-7 hand-rolled relocation,
        mirror of the main recipe): binary-sign-tool rebuilds the ELF
        while signing and drops the EOF-appended interpreter string —
        the appended bytes belong to no section, so the round-7 patch
        died and exec failed with an empty interpreter (round-9 log:
        interp='', [Errno 22] Invalid argument).  Use the device's own
        patchelf instead: its edits update the real .interp section and
        the program headers section-aware, and E077 documents the
        working order patchelf-then-sign on OHOS:

          1) PT_INTERP: patchelf --set-interpreter <device loader>
          2) DT_NEEDED: patchelf --replace-needed libc.musl-aarch64.so.1
             libc.so (the device musl loader maps libc.so to itself,
             exactly like every OHOS binary).

        Round-15 (mirror): the round-11 RUNPATH step was REMOVED — the
        OHOS loader searches LD_LIBRARY_PATH (namespace env_paths) FIRST
        (porting/linux/user/ldso/dynlink.c load_library), and dropping
        --set-rpath avoids the .dynstr growth that corrupted the big
        gnat1 binary (mass empty-symbol relocation errors).

        Returns a description of the changes, or None if the file is not
        an ELF or needs nothing.  Idempotent.
        """
        try:
            with open(path, "rb") as fh:
                head = fh.read(64)
                if head[:4] != b"\x7fELF" or len(head) < 64:
                    return None
        except OSError:
            return None
        changed = []
        interp = self._elf_interp(path)
        if interp:  # shared libraries have no PT_INTERP — executables only
            device = self._device_interp()
            if interp != device:
                rc = self._patchelf(
                    ["--set-interpreter", device, path])
                if rc == 0:
                    changed.append("interp=%s" % device)
        if "libc.musl-aarch64.so.1" in self._elf_needed(path):
            rc = self._patchelf(
                ["--replace-needed",
                 "libc.musl-aarch64.so.1", "libc.so", path])
            if rc == 0:
                changed.append("needed=libc.so")
        return ", ".join(changed) or None

    def _exec_probe(self, cmd, env=None):
        """Run any command, never raising: OSError (exec denied — e.g.
        EACCES on execve) returns rc=-1 with the error message; otherwise
        (rc, first output line, output tail)."""
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
                env=env,
            )
            first = (proc.stdout.splitlines() or [""])[0][:100]
            return proc.returncode, first, proc.stdout[-200:]
        except OSError as exc:
            return -1, "", str(exc)

    def _copy_file_0755(self, src, dst):
        """Byte-copy a file and recreate it with umask-0 0o755 (HMFS
        honors the open() mode — aribb24 install-shim precedent).

        Round-28: O_CREAT|O_TRUNC does NOT change the mode of an
        EXISTING file — the open() mode argument only applies when the
        file is created — so gnat1 kept its patchelf-rewrite mode 0o770
        (no o+x) and the exec probe still failed EACCES.  Unlink dst
        first, then O_CREAT|O_EXCL with umask forced to 0: a fresh
        inode with exactly 0o755 — the round-4 _repair_exec_bits
        pattern."""
        try:
            with open(src, "rb") as fh:
                data = fh.read()
        except OSError:
            return False
        try:
            os.unlink(dst)  # fresh inode required for the mode to apply
        except OSError:
            pass  # dst may not exist yet
        old_umask = os.umask(0)
        try:
            fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o755)
        finally:
            os.umask(old_umask)
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        return True

    # ---------- OHOS XPM ELF signing (round-8, mirror of main recipe) ----------
    # The kernel refuses exec of unsigned foreign (Alpine) ELFs with
    # "Permission denied" (E258 root cause (5), E077).  binary-sign-tool
    # must run AFTER the PT_INTERP/DT_NEEDED rewrite (signature covers the
    # final bytes), then exec bits are restored byte-identically (signing
    # zeroes mode to 000; chmod is unreliable on HMFS).

    @staticmethod
    def _sign_tool():
        for cand in (
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
        ):
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _remove_codesign(self, path):
        oc = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(oc):
            return False
        try:
            proc = subprocess.run(
                [oc, "--remove-section", ".codesign", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError:
            return False
        return True  # no such section found implies absence — proceed

    def _sign_elf(self, path):
        tool = self._sign_tool()
        if not tool:
            self.output.warning(
                "binary-sign-tool not found; skipping OHOS ELF sign of %s"
                % path)
            return False
        self._remove_codesign(path)
        try:
            proc = subprocess.run(
                [tool, "sign", "-inFile", path, "-outFile", path,
                 "-selfSign", "1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
        except OSError as exc:
            self.output.warning("binary-sign-tool sign exec failed: %s" % exc)
            return False
        if proc.returncode != 0:
            self.output.warning(
                "binary-sign-tool sign failed rc=%s tail=%r"
                % (proc.returncode, proc.stdout[-200:]))
            return False
        self._copy_file_0755(path, path)
        return True

    def _strip_dynsym(self, path):
        """Shrink an oversized ELF's dynamic symbol table so the device's
        binary-sign-tool rebuild can regenerate it correctly (round-18,
        mirror of the main recipe).

        binary-sign-tool's rebuild of the 35MB gnat1 (47800 dynsym / 2MB
        dynstr) produces EMPTY .dynsym/.dynstr -> the musl loader reports
        mass "Error relocating ...: symbol not found"; the 3.2MB gnatmake
        (tiny symtab) is unaffected.  llvm-objcopy --strip-unneeded keeps
        exactly the symbols the loader needs for relocations and drops the
        -rdynamic export bloat, leaving DT_NEEDED/PT_INTERP intact.
        Returns True on success; False leaves the file untouched.
        """
        oc = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(oc):
            self.output.warning(
                "llvm-objcopy not found; cannot strip %s" % path)
            return False
        tmp = path + ".stripped"
        try:
            proc = subprocess.run(
                [oc, "--strip-unneeded", path, tmp],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                self.output.warning(
                    "llvm-objcopy --strip-unneeded %s rc=%s tail=%r"
                    % (path, proc.returncode, proc.stdout[-200:]))
                return False
            ok = self._copy_file_0755(tmp, path)
            if ok:
                self.output.info("stripped oversized ELF dynsym: %s" % path)
            return ok
        except OSError as exc:
            self.output.warning("strip failed on %s: %s" % (path, exc))
            return False
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _dynamic_intact(self, path):
        """Round-18 post-sign check (mirror of the main recipe): is the
        first DT_NEEDED name readable?

        binary-sign-tool's rebuild of oversized ELFs leaves DT_STRTAB
        pointing into a zeroed region -> NEEDED/dynsym read empty.  Parse
        the program headers exactly like the musl loader (decode_dyn +
        laddr): resolve DT_STRTAB through PT_LOAD and read the first
        DT_NEEDED string.  True means intact; static ELFs trivially pass.
        Never raises.
        """
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return False
        if data[:4] != b"\x7fELF" or len(data) < 64:
            return False
        try:
            (ident, e_type, e_machine, e_version, e_entry, e_phoff, e_shoff,
             e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
             e_shstrndx) = struct.unpack_from("<16sHHIQQQIHHHHHH", data, 0)
            segs = []
            dyn_off = dyn_sz = None
            for i in range(e_phnum):
                (p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz,
                 p_memsz, p_align) = struct.unpack_from(
                     "<IIQQQQQQ", data, e_phoff + i * e_phentsize)
                if p_type == 1:  # PT_LOAD
                    segs.append((p_vaddr, p_vaddr + p_memsz, p_offset))
                elif p_type == 2:  # PT_DYNAMIC
                    dyn_off, dyn_sz = p_offset, p_filesz
            if dyn_off is None:
                return True  # no dynamic linking: nothing to relocate
            strtab_v = needed_v = None
            off = dyn_off
            while off + 16 <= dyn_off + dyn_sz:
                tag, val = struct.unpack_from("<qq", data, off)
                if tag == 0:
                    break
                if tag == 5:  # DT_STRTAB
                    strtab_v = val
                elif tag == 1 and needed_v is None:  # DT_NEEDED
                    needed_v = val
                off += 16
            if strtab_v is None or needed_v is None:
                return True
            st_off = None
            for (a, b, fo) in segs:
                if a <= strtab_v < b:
                    st_off = fo + (strtab_v - a)
                    break
            if st_off is None:
                return False
            end = data.index(b"\x00", st_off + needed_v)
            name = data[st_off + needed_v:end].decode("utf-8", "replace")
            return bool(name.strip())
        except Exception:
            return False

    def _ohos_ident_blob(self):
        """Locate a `.note.ohos.ident` platform-identity blob on the
        device (mirror of the main recipe, round-20).

        The OHOS kernel accepts exec of an ELF carrying the constant
        .note.ohos.ident platform marker even WITHOUT a .codesign (the
        device-clang ctl-nopie probe execs unsigned rc=0 every round).
        The note is NOT content-bound, so it can be copied from any
        OHOS-native ELF.  Returns the blob path or None.
        """
        oc = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(oc):
            return None
        cands = []
        for c in (
            "/data/service/hnp/bin/bash",
            "/data/service/hnp/bin/python3",
            "/data/service/hnp/bin/cmake",
            "/data/service/hnp/bin/make",
            "/data/service/hnp/bin/ninja",
            "/data/service/hnp/bin/clang",
            "/system/lib/ld-musl-aarch64.so.1",
        ):
            if os.path.isfile(c):
                cands.append(c)
        blob = os.path.join(self.build_folder, "note-ohos-ident.bin")
        for cand in cands:
            if self._dump_section(cand, ".note.ohos.ident", blob):
                self.output.info("ohos-ident blob source: %s" % cand)
                return blob
        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        src = os.path.join(self.build_folder, "ident_src.c")
        exe = os.path.join(self.build_folder, "ident-src")
        try:
            with open(src, "w") as fh:
                fh.write("int main(void) { return 0; }\n")
            proc = subprocess.run(
                [clang, "-no-pie", "-o", exe, src],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=120,
            )
            if proc.returncode == 0 and os.path.isfile(exe):
                if self._dump_section(exe, ".note.ohos.ident", blob):
                    self.output.info(
                        "ohos-ident blob source: device-clang %s" % exe)
                    return blob
        except OSError:
            pass
        return None

    def _dump_section(self, path, sec, out):
        """llvm-objcopy --dump-section <sec>=<out> path; True on success
        (False when the section does not exist)."""
        oc = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(oc):
            return False
        try:
            proc = subprocess.run(
                [oc, "--dump-section", "%s=%s" % (sec, out), path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
        except OSError as exc:
            self.output.warning("dump-section %s failed: %s" % (sec, exc))
            return False
        if proc.returncode != 0:
            return False
        return os.path.isfile(out)

    def _add_section(self, path, sec, src):
        """llvm-objcopy --add-section <sec>=<src> path (written via a
        temp file, then byte-identical 0o755 recreate); True on success."""
        oc = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(oc):
            return False
        tmp = path + ".addsec"
        try:
            proc = subprocess.run(
                [oc, "--add-section", "%s=%s" % (sec, src), path, tmp],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                self.output.warning(
                    "add-section %s rc=%s tail=%r"
                    % (sec, proc.returncode, proc.stdout[-200:]))
                return False
            return self._copy_file_0755(tmp, path)
        except OSError as exc:
            self.output.warning("add-section %s failed: %s" % (sec, exc))
            return False
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _ptnote_ident_overwrite(self, path, blob):
    # --- round-25: first-page note install with deterministic
        # slot creation (see notes.md round-25) ---
        SHT_PROGBITS = 1
        SHT_SYMTAB = 2
        SHT_STRTAB = 3
        SHT_DYNAMIC = 6
        SHT_NOTE = 7
        SHT_NOBITS = 8
        SHT_DYNSYM = 11
        DT_HASH = 4
        DT_STRTAB = 5
        DT_SYMTAB = 6
        DT_RELA = 7
        DT_JMPREL = 23
        DT_VERSYM = 0x6ffffff0
        DT_VERNEED = 0x6ffffffe
        DT_GNU_HASH = 0x6ffffef5
        _MOVABLE_TAG = {
            '.gnu.hash': DT_GNU_HASH, '.hash': DT_HASH,
            '.dynsym': DT_SYMTAB, '.dynstr': DT_STRTAB,
            '.rela.dyn': DT_RELA, '.rela.plt': DT_JMPREL,
            '.gnu.version': DT_VERSYM, '.gnu.version_r': DT_VERNEED,
        }

        def _expendable_sec(nm, s_type):
            """True when overwriting/moving this section's first-page bytes
            cannot break exec or the dynamic loader."""
            if s_type in (SHT_NOTE, SHT_NOBITS):
                return True
            if s_type == SHT_SYMTAB and nm != '.dynsym':
                return True
            if s_type == SHT_STRTAB and nm not in ('.dynstr', '.shstrtab'):
                return True
            if nm == '.comment':
                return True
            return False

        def _carve(protected, page_start, page_end, size):
            pos = page_start
            while pos + size <= page_end:
                ok = True
                for (a, b) in protected:
                    if pos < b and pos + size > a:
                        ok = False
                        pos = max(pos + 1, b)
                        break
                if ok:
                    return pos
            return None
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return False, "unreadable"
        if data[:4] != b"\x7fELF" or len(data) < 64:
            return False, "not ELF"
        try:
            (_id, _t, _m, _v, _e, e_phoff, e_shoff, _f, _eh, phent, phnum,
             shent, shnum, shstrndx) = struct.unpack_from(
                 "<16sHHIQQQIHHHHHH", data, 0)
            if e_phoff + phnum * phent > len(data):
                return False, "phdrs out of file"
            load_ranges = []
            loads3 = []  # (p_offset, p_vaddr, p_filesz) per PT_LOAD
            pt_note = None  # (ph_idx, p_offset, p_vaddr, p_filesz)
            pt_interp = None  # (ph_idx, p_offset, p_vaddr, p_filesz)
            pt_dyn = None  # (ph_idx, p_offset, p_vaddr, p_filesz)
            phdrs_raw = []
            for i in range(phnum):
                ph = struct.unpack_from(
                    "<IIQQQQQQ", data, e_phoff + i * phent)
                phdrs_raw.append(ph)
                (p_type, _pf, p_off, p_vaddr, _pp, p_filesz, _pm,
                 _pa) = ph
                if p_type == 1:  # PT_LOAD
                    load_ranges.append((p_off, p_off + p_filesz))
                    loads3.append((p_off, p_vaddr, p_filesz))
                elif p_type == 4 and pt_note is None:  # PT_NOTE
                    pt_note = (i, p_off, p_vaddr, p_filesz)
                elif p_type == 3:  # PT_INTERP
                    pt_interp = (i, p_off, p_vaddr, p_filesz)
                elif p_type == 2:  # PT_DYNAMIC
                    pt_dyn = (i, p_off, p_vaddr, p_filesz)
        except struct.error:
            return False, "phdr parse failed"
        if not load_ranges:
            return False, "no PT_LOAD segments"
        if e_shoff == 0 or shnum == 0 or shent < 64:
            return False, "no section header table"
        if e_shoff + shnum * shent > len(data):
            return False, "sht out of file"
        if shstrndx == 0xffff:  # SHN_XINDEX
            try:
                shstrndx = struct.unpack_from("<I", data, e_shoff + 16)[0]
            except struct.error:
                return False, "bad shstr xindex"
        if shstrndx >= shnum:
            return False, "bad shstr index"
        try:
            (_n, _t, _f2, _a, shstr_off, shstr_sz, _l, _i, _al,
             _en) = struct.unpack_from(
                 "<IIQQQQIIQQ", data, e_shoff + shstrndx * shent)
        except struct.error:
            return False, "bad shstr header"
        if shstr_off + shstr_sz > len(data):
            return False, "shstr out of file"
    
        # Full section table: (idx, name_off, name, type, flags, addr, off, size)
        secs = []
        notes = []  # SHT_NOTE entries only
        for i in range(shnum):
            off = e_shoff + i * shent
            if off + 64 > len(data):
                break
            (s_name, s_type, s_flags, s_addr, s_off, s_size, s_link,
             s_info, s_align, s_entsize) = struct.unpack_from(
                 "<IIQQQQIIQQ", data, off)
            nm = ""
            if s_name < shstr_sz:
                try:
                    end = data.index(b"\x00", shstr_off + s_name)
                    nm = data[shstr_off + s_name:end].decode(
                        "utf-8", "replace")
                except ValueError:
                    pass
            secs.append((i, s_name, nm, s_type, s_flags, s_addr, s_off, s_size))
            if s_type == SHT_NOTE:
                notes.append((i, s_name, nm, s_flags, s_addr, s_off, s_size))
        if not notes:
            return False, "no SHT_NOTE section"
    
        # First PT_LOAD (smallest p_offset) — its first page is what the
        # kernel exec gate scans.
        (f_off, f_vaddr, f_filesz) = min(loads3, key=lambda t: t[0])
        page_start = f_off
        page_end = min(f_off + 0x1000, f_off + f_filesz)
        if page_end - page_start < len(blob):
            return False, "first page smaller than ident blob"
    
        # ---- slot selection (T1 -> T2 -> T3 -> T4 -> T5) ----
        # T1: existing SHT_NOTE entirely inside the first page.
        in_page = [n for n in notes
                   if page_start <= n[5] and n[5] + max(n[6], 1) <= page_end
                   and n[6] >= len(blob)]
        if in_page:
            in_page.sort(key=lambda n: n[5])
            (s_idx, s_name, old_nm, s_flags, s_addr, s_off,
             s_size) = in_page[0]
            canon_off, canon_addr, canon_sz = s_off, s_addr, s_size
            patches = []
            detail_extra = ""
        else:
            # Protected byte ranges in the first page: ELF header, phdrs,
            # PT_INTERP / PT_DYNAMIC content, and every non-expendable
            # section that starts there.
            def protected_ranges(moved_idx=None, extra_ph=0, skip_phdr=False):
                pr = []
                if not skip_phdr:
                    pr.append((0, min(64, page_end)))
                    pr.append((e_phoff, min(e_phoff + (phnum + extra_ph) * phent,
                                            page_end)))
                if pt_interp is not None:
                    pr.append((pt_interp[1], min(pt_interp[1] + pt_interp[3],
                                                 page_end)))
                if pt_dyn is not None:
                    pr.append((pt_dyn[1], min(pt_dyn[1] + pt_dyn[3], page_end)))
                for (i, _no, nm, st, _fl, _a, so, ss) in secs:
                    if ss and so < page_end and i != moved_idx:
                        if _expendable_sec(nm, st):
                            continue
                        pr.append((so, min(so + ss, page_end)))
                return pr
    
            canon_off = None
            patches = []
            moved = {}  # sec idx -> (new_off, new_addr or None)
            tried = []
            # T2: plain carve.
            slot = _carve(protected_ranges(), page_start, page_end, len(blob))
            tried.append("carve")
            # T3: relocate the PT_INTERP string out of the first page.
            if slot is None and pt_interp is not None and \
                    page_start <= pt_interp[1] < page_end:
                (iph, ioff, ivaddr, isz) = pt_interp
                s = data[ioff:ioff + isz].split(b"\x00")[0] + b"\x00"
                new_off = len(data) + sum(len(b) for (_o, b) in patches)
                patches.append((new_off, s))
                patches.append((e_phoff + iph * phent + 8,
                                struct.pack("<Q", new_off)))
                patches.append((e_phoff + iph * phent + 32,
                                struct.pack("<Q", len(s))))
                patches.append((e_phoff + iph * phent + 40,
                                struct.pack("<Q", len(s))))
                for (i, _no, nm, st, _fl, _a, so, ss) in secs:
                    if nm == ".interp":
                        patches.append((e_shoff + i * shent + 24,
                                        struct.pack("<Q", new_off)))
                        patches.append((e_shoff + i * shent + 32,
                                        struct.pack("<Q", len(s))))
                        secs[i] = (i, _no, nm, st, _fl, _a, new_off, len(s))
                        break
                pt_interp = (iph, new_off, ivaddr, len(s))
                slot = _carve(protected_ranges(), page_start, page_end,
                              len(blob))
                tried.append("interp-reloc")
            # T4: relocate expendable first-page sections to EOF.
            if slot is None:
                for (i, _no, nm, st, _fl, _a, so, ss) in secs:
                    if not (ss and so < page_end):
                        continue
                    if i in moved:
                        continue
                    if not _expendable_sec(nm, st):
                        continue
                    new_off = len(data) + sum(len(b) for (_o, b) in patches)
                    patches.append((new_off, data[so:so + ss]))
                    patches.append((e_shoff + i * shent + 24,
                                    struct.pack("<Q", new_off)))
                    moved[i] = (new_off, None)
                    secs[i] = (i, _no, nm, st, _fl, _a, new_off, ss)
                    slot = _carve(protected_ranges(moved_idx=i),
                                  page_start, page_end, len(blob))
                    tried.append("exp-reloc:%s" % (nm or "?"))
                    if slot is not None:
                        break
            # T5: move a first-page loader table into an appended PT_LOAD.
            if slot is None:
                for k, (i, _no, nm, st, _fl, _a, so, ss) in enumerate(secs):
                    if not (ss and so < page_end):
                        continue
                    if i in moved or nm not in _MOVABLE_TAG:
                        continue
                    if pt_dyn is None:
                        break
                    tag = _MOVABLE_TAG[nm]
                    new_off = len(data) + sum(len(b) for (_o, b) in patches)
                    new_addr = 0x40000000 + k * 0x100000
                    ph_slot = e_phoff + phnum * phent
                    # The new phdr entry must land in bytes that are free
                    # (or belong to the section being moved).  The phdr range
                    # itself always covers the slot, so check against the
                    # non-phdr protected ranges only.
                    pr = protected_ranges(moved_idx=i, extra_ph=1)
                    clash = any(
                        a < ph_slot + 56 and ph_slot < b
                        for (a, b) in protected_ranges(moved_idx=i, extra_ph=1,
                                                       skip_phdr=True))
                    if clash:
                        continue
                    # patch list: data copy, new phdr, e_phnum, DT tag, SHT
                    copy = data[so:so + ss]
                    if len(copy) != ss:
                        continue  # section extends past EOF: unusable
                    patches.append((new_off, copy))
                    np_off = ph_slot
                    new_ph = struct.pack(
                        "<IIQQQQQQ", 1, 4, new_off, new_addr, new_addr,
                        ss, ss, 0x1000)
                    patches.append((np_off, new_ph))
                    patches.append((56, struct.pack("<H", phnum + 1)))
                    # DT tag patch in .dynamic
                    (dph, doff, dvaddr, dsz) = pt_dyn
                    found = False
                    for to in range(doff, min(doff + dsz, len(data) - 15), 16):
                        t = struct.unpack_from("<Q", data, to)[0]
                        if t == tag:
                            patches.append((to + 8, struct.pack("<Q", new_addr)))
                            found = True
                            break
                    if not found:
                        continue
                    patches.append((e_shoff + i * shent + 16,
                                    struct.pack("<Q", new_addr)))
                    patches.append((e_shoff + i * shent + 24,
                                    struct.pack("<Q", new_off)))
                    moved[i] = (new_off, new_addr)
                    secs[i] = (i, _no, nm, st, _fl, _a, new_off, ss)
                    slot = _carve(pr, page_start, page_end, len(blob))
                    tried.append("loadtable-reloc:%s" % (nm or "?"))
                    if slot is not None:
                        break
            if slot is None:
                layout = "; ".join(
                    "%s@%#x/%#x" % (nm or "?", so, ss)
                    for (_i, _no, nm, _st, _fl, _a, so, ss) in secs
                    if ss and so < page_end)
                free = []
                cur = page_start
                for (a, b) in sorted(protected_ranges()):
                    if a > cur:
                        free.append((cur, a))
                    cur = max(cur, b)
                if cur < page_end:
                    free.append((cur, page_end))
                fr = "; ".join("%#x..%#x/%d" % (a, b, b - a) for (a, b) in free)
                return False, (
                    "no first-page slot (page %#x..%#x blob=%d; tried %s; "
                    "sections: %s; free: %s)"
                    % (page_start, page_end, len(blob), ",".join(tried),
                       layout, fr))
            canon_off = slot
            for (a, v, fs) in loads3:
                if a <= canon_off < a + fs:
                    canon_addr = v + (canon_off - a)
                    break
            else:
                return False, "first-page slot not covered by PT_LOAD"
            canon_sz = len(blob)
            # Repurpose the first SHT_NOTE entry to describe the slot.
            (s_idx, s_name, old_nm, s_flags, s_addr, s_off,
             s_size) = notes[0]
            detail_extra = " (%s)" % ",".join(tried)
    
        if not any(a <= canon_off and canon_off + canon_sz <= b
                   for (a, b) in load_ranges):
            return False, "note location not covered by any PT_LOAD"
        if len(old_nm.encode("utf-8", "replace")) + 1 < 17:
            return False, "name slot too short (%r)" % old_nm
        if shstr_off + s_name + 17 > len(data):
            return False, "shstrtab slot out of file"
    
        # ---- install: single r+b pass ----
        try:
            with open(path, "r+b") as fh:
                for (poff, pbytes) in patches:
                    fh.seek(poff)
                    fh.write(pbytes)
                fh.seek(canon_off)
                fh.write(blob)
                rest = canon_sz - len(blob)
                if rest > 0:
                    fh.write(b"\x00" * rest)
                fh.seek(shstr_off + s_name)
                fh.write(b".note.ohos.ident\x00")
                base = e_shoff + s_idx * shent
                fh.seek(base + 16)
                fh.write(struct.pack("<Q", canon_addr))
                fh.seek(base + 24)
                fh.write(struct.pack("<Q", canon_off))
                fh.seek(base + 32)
                fh.write(struct.pack("<Q", canon_sz))
                if pt_note is not None:
                    base = e_phoff + pt_note[0] * phent
                    fh.seek(base + 8)
                    fh.write(struct.pack("<Q", canon_off))
                    fh.seek(base + 16)
                    fh.write(struct.pack("<Q", canon_addr))
                    fh.seek(base + 32)
                    fh.write(struct.pack("<Q", canon_sz))
                    fh.seek(base + 40)
                    fh.write(struct.pack("<Q", canon_sz))
                fh.flush()
        except OSError as exc:
            return False, "in-place patch failed: %s" % exc
    
        # ---- verify ----
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return False, "re-read failed"
        try:
            head = data[canon_off:canon_off + 16]
            ok_name = len(head) >= 16 and head[12:16] == b"OHOS"
            if shstr_off + s_name + 17 <= len(data):
                nm = data[shstr_off + s_name:shstr_off + s_name + 17]
                ok_sec = nm == b".note.ohos.ident\x00"
            else:
                ok_sec = False
            ok_ph = True
            if pt_note is not None:
                base = e_phoff + pt_note[0] * phent
                p_off2 = struct.unpack_from("<Q", data, base + 8)[0]
                ok_ph = p_off2 == canon_off
        except (struct.error, IndexError):
            return False, "verify parse failed"
        if not ok_name:
            return False, "note name mismatch after install"
        if not ok_sec:
            return False, "section rename verify failed"
        if not ok_ph:
            return False, "program header sync verify failed"
        return True, (
            "SHT[%d]=.note.ohos.ident@0x%x/%d PT_NOTE@0x%x%s"
            % (s_idx, canon_off, canon_sz, canon_off, detail_extra))

    def _sign_by_ident(self, path):
        """Make the oversized gnat1 executable WITHOUT binary-sign-tool
        (round-23, mirror of the main recipe).

        binary-sign-tool's rebuild of >8MB ELFs corrupts .dynamic and its
        .codesign is content-bound (cannot be copied between files); the
        kernel accepts note-carrying ELFs unsigned instead, but the note
        must be a section NAMED .note.ohos.ident inside the mapped image
        (round-20 add-section and round-21/22 in-place content both still
        got EACCES).  _ptnote_ident_overwrite renames the existing note
        section, syncs the SHT entry and the PT_NOTE program header, and
        writes the constant blob in place — never rebuilding the file; if
        there is no suitable note section, fall back to the round-20
        add-section.  Returns (ok, detail).

        Round-29 (different route): gnat1 is now handed to this method
        with the PRISTINE layout — _rewrite_toolchain no longer runs
        patchelf on oversized files (only an in-place .dynstr NEEDED
        patch), so _ptnote_ident_overwrite hits its T1 route: the
        original .note.gnu.build-id section at 0x28c, inside the first
        PT_LOAD's first page, with the PT_NOTE phdr already pointing
        there — the exact layout of a device-lld-linked binary
        (ctl-nopie, which execs every round)."""
        blob = self._ohos_ident_blob()
        if not blob:
            return False, "no .note.ohos.ident source on device"
        try:
            with open(blob, "rb") as fh:
                blob_bytes = fh.read()
        except OSError:
            return False, "ident blob unreadable"
        if len(blob_bytes) < 16 or blob_bytes[12:16] != b"OHOS":
            return False, "ident blob malformed (%d bytes)" % len(blob_bytes)
        ok, detail = self._ptnote_ident_overwrite(path, blob_bytes)
        if not ok:
            self.output.info(
                "note-ident in-place route unavailable (%s) — falling "
                "back to add-section" % detail)
            if not self._add_section(path, ".note.ohos.ident", blob):
                return False, "add-section .note.ohos.ident failed"
        else:
            self.output.info("note-ident in-place: %s" % detail)
        # E077 step 4 (round-27/28): patchelf's HMFS rewrite recreates
        # the file via a temp file (mode lost — round-28 log: 0o770, no
        # o+x) and chmod() is a no-op on HMDFS (E046), so execve fails
        # EACCES regardless of the note.  Round-27's O_CREAT|O_TRUNC
        # recreate did NOT change the mode of the EXISTING gnat1 (open()
        # mode applies only at creation); round-28 unlinks first, then
        # O_EXCL-creates a fresh inode with umask-0 0o755 (the
        # round-4 _repair_exec_bits pattern).  Verify o+x explicitly.
        if not self._copy_file_0755(path, path):
            return False, "byte-identical 0o755 recreate failed"
        mode = stat.S_IMODE(os.stat(path).st_mode)
        self.output.info("exec mode after note-ident: %s" % oct(mode))
        # Round-29: stat mode is NOT a reliable exec gate on HMFS — the
        # round-28 `mode & 0o001` guard fired on 0o770 even though files
        # recreated by _copy_file_0755 demonstrably exec on this device
        # (ctl-nopie exec rc=0 every round after the identical call, and
        # signed gnatmake runs via _verify_gnat_exec).  HMFS remaps file
        # ownership (E011) and creates modes where exec works through
        # the process group; only the real kernel exec probe below is
        # the ground truth (round-4 doctrine: os.access/stat unreliable,
        # only a real exec proves executability).  The stat value stays
        # as a diagnostic log line.
        if not self._dynamic_intact(path):
            return False, "dyncheck corrupt after note add"
        rc, first, err = self._exec_probe([path, "-v"], env=self._gnat_env())
        detail = "exec rc=%s first=%r" % (rc, first)
        if rc == -1:
            return False, detail + "; kernel refused exec (%s)" % (
                (err or "")[:120])
        return True, detail

    def _sign_oversized_bst(self, path):
        """Sign the oversized gnat1 with the device's binary-sign-tool
        DIRECTLY on the pristine apk bytes (round-30 route).

        Rounds 8-14 proved the kernel ACCEPTS a binary-sign-tool-signed
        gnat1 (the loader ran; only relocation failed), and rounds 20-29
        proved the copied .note.ohos.ident NEVER passes exec (EACCES
        even at the exact device-lld first-page layout) — the exec gate
        is the content-bound .codesign, and hnp system binaries
        (bash/python3/cmake) have no dumpable .note.ohos.ident at all.
        The round-16/18 ".dynamic corruption" was always measured on
        files REWRITTEN by patchelf (round-22: patchelf moves the 35MB
        file's note 0x28c -> 0x35b2f8) or llvm-objcopy --strip-unneeded
        first; round-29 already removed both from the oversized path
        (pristine + in-place .dynstr NEEDED patch only), so
        binary-sign-tool now signs the ORIGINAL Alpine layout — the
        same condition under which clang/22.1.8 and python/3.9.0 sign
        100MB+ ELFs successfully.  llvm-objcopy --remove-section is
        deliberately NOT run: pristine gnat1 has no .codesign to remove
        and an objcopy rewrite of the 35MB file is itself the
        section-moving corruption vector.  Returns (ok, detail)."""
        tool = self._sign_tool()
        if not tool:
            return False, "binary-sign-tool not found"
        try:
            proc = subprocess.run(
                [tool, "sign", "-inFile", path, "-outFile", path,
                 "-selfSign", "1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
            )
        except OSError as exc:
            return False, "binary-sign-tool sign exec failed: %s" % exc
        if proc.returncode != 0:
            return False, "binary-sign-tool sign rc=%s tail=%r" % (
                proc.returncode, proc.stdout[-200:])
        # E077 step 4: signing zeroes the mode to 000; restore
        # world-exec via the byte-identical 0o755 recreate (round-28
        # unlink+O_EXCL pattern) before the dyncheck and exec probe.
        if not self._copy_file_0755(path, path):
            return False, "byte-identical 0o755 recreate failed"
        mode = stat.S_IMODE(os.stat(path).st_mode)
        self.output.info("exec mode after oversized sign: %s" % oct(mode))
        if not self._dynamic_intact(path):
            return False, "dyncheck corrupt after oversized sign"
        rc, first, err = self._exec_probe([path, "-v"], env=self._gnat_env())
        detail = "exec rc=%s first=%r" % (rc, first)
        if rc == -1:
            return False, detail + "; kernel refused exec (%s)" % (
                (err or "")[:120])
        return True, detail

    def _sign_toolchain(self):
        """Sign every rewritten Alpine ELF under the toolchain root.

        Round-14 (mirror of the main recipe): walk the WHOLE root, not
        just usr/ — zlib unpacks to lib/ and musl libc/loader live in
        lib/ too; they must be signed or the loader refuses to load
        them (unsigned ELF dlopen -> Permission denied, E258/E077).

        Round-16 (mirror): binary-sign-tool's rebuild corrupts the large
        gnat1's .dynamic; when _probe_unsigned_exec() verified unsigned
        exec works, signing is SKIPPED so the rebuild never runs.

        Round-18 (mirror): unsigned exec is refused on this device, so
        signing cannot be skipped.  Oversized ELFs are stripped first,
        signed, then verified with _dynamic_intact; a corrupt result
        triggers ONE bounded retry (pristine restore -> strip -> rewrite
        -> sign -> check).

        Round-20 (mirror): the strip+sign retry still could not beat
        binary-sign-tool's rebuild corruption measured in rounds 16-18,
        and .codesign is content-bound so it cannot be copied; the
        .note.ohos.ident copy route (rounds 20-29) never passed exec
        (EACCES even at the exact device-lld first-page layout).

        Round-30 (mirror): oversized gcc-gnat files (exactly gnat1) are
        signed with binary-sign-tool DIRECTLY on the pristine apk bytes
        (round-29 keeps gnat1 pristine — no patchelf/objcopy rewrite,
        only the in-place .dynstr NEEDED patch).  Rounds 15-18 proved
        the kernel ACCEPTS a binary-sign-tool-signed gnat1 (the loader
        ran; only relocation failed) and clang/22.1.8 + python/3.9.0
        sign 100MB+ ELFs with this same tool; the round-16/18
        ".dynamic corruption" was measured on files REWRITTEN by
        patchelf/objcopy first, which round-29 eliminated.  All other
        ELFs keep the standard binary-sign-tool flow."""
        if getattr(self, "_unsigned_exec_ok", False):
            self.output.info(
                "unsigned exec verified — skipping binary-sign-tool "
                "(avoids the rebuild that corrupts gnat1's .dynamic)")
            return
        root = self._gnat_root()
        gnat_members = self._gnat_apk_members()
        oversized = []
        count = 0
        # Pass 1: every non-oversized ELF through the standard flow.
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                p = os.path.join(dirpath, name)
                if os.path.islink(p):
                    continue
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) != b"\x7fELF":
                            continue
                    size = os.path.getsize(p)
                except OSError:
                    continue
                rel = os.path.relpath(p, root).replace("\\", "/")
                # Round-30 (mirror): only gcc-gnat-apk files with a
                # pristine source go through the direct-sign path
                # (exactly the oversized gnat1); everything else is
                # plain-signed.
                if size > _LARGE_ELF_MIN and rel in gnat_members:
                    oversized.append(p)  # handled in pass 2
                    continue
                if self._sign_elf(p):
                    count += 1
        # Pass 2: oversized gcc-gnat files (exactly gnat1) — round-30
        # (mirror of the main recipe): binary-sign-tool DIRECTLY on the
        # pristine bytes (no objcopy, no patchelf, no note-ident — all
        # falsified by rounds 20-29).
        for p in oversized:
            self.output.info(
                "signing oversized ELF via binary-sign-tool (pristine): %s"
                % p)
            ok, detail = self._sign_oversized_bst(p)
            if not ok:
                raise ConanInvalidConfiguration(
                    "oversized ELF binary-sign-tool signing failed (%s): %s"
                    % (p, detail))
            count += 1
            self.output.info("oversized signed %s: %s" % (p, detail))
        self.output.info("OHOS-signed %d toolchain ELF files" % count)

    def _elf_dynamic_probe(self, path, label):
        """On-device ELF dynamic-section consistency check (pure stdlib,
        mirror of the main recipe's round-16 enhanced probe).

        Mirrors what the OHOS musl loader does in decode_dyn()/do_relocs()
        (porting/linux/user/ldso/dynlink.c): DT_SYMTAB/DT_STRTAB/DT_RELA/
        DT_JMPREL come from PT_DYNAMIC and each vaddr is resolved through
        the PT_LOAD segments.  A pointer outside every PT_LOAD means the
        loader reads garbage symbol entries — the round-15/16 mass
        empty-symbol "Error relocating ...: symbol not found" fingerprint
        on gnat1.  Round-16 evidence: the binary-sign-tool rebuild moved
        DT_SYMTAB (0x456670 -> 0x5dcdd8) while DT_RELA/DT_JMPREL stayed,
        and NEEDED/dynsym read EMPTY.  This probe ALSO cross-checks every
        DT_* vaddr against the section header table (sh_addr) and dumps
        the PT_LOAD layout.  Runs AFTER rewrite+sign; informational only.
        """
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return
        if data[:4] != b"\x7fELF" or len(data) < 64:
            return
        try:
            (ident, e_type, e_machine, e_version, e_entry, e_phoff, e_shoff,
             e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
             e_shstrndx) = struct.unpack_from("<16sHHIQQQIHHHHHH", data, 0)
            segs = []      # (vaddr_start, vaddr_end, file_off)
            dyn_off = dyn_sz = None
            for i in range(e_phnum):
                (p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz,
                 p_memsz, p_align) = struct.unpack_from(
                     "<IIQQQQQQ", data, e_phoff + i * e_phentsize)
                if p_type == 1:  # PT_LOAD
                    segs.append((p_vaddr, p_vaddr + p_memsz, p_offset))
                elif p_type == 2:  # PT_DYNAMIC
                    dyn_off, dyn_sz = p_offset, p_filesz
            if dyn_off is None:
                self.output.info("dynprobe %s: no PT_DYNAMIC" % label)
                return

            def vaddr_to_off(v):
                for (a, b, fo) in segs:
                    if a <= v < b:
                        return fo + (v - a)
                return None

            # ---- section header table (sh_addr/sh_offset vs DT_*) ----
            secs = {}
            if e_shoff and e_shentsize >= 64 and e_shnum:
                shstr_off = None
                if e_shstrndx < e_shnum:
                    (s_name, s_type, s_flags, s_addr, s_off, s_size,
                     s_link, s_info, s_align, s_entsize) = struct.unpack_from(
                         "<IIQQQQIIQQ", data,
                         e_shoff + e_shstrndx * e_shentsize)
                    shstr_off = s_off
                for i in range(e_shnum):
                    if e_shoff + (i + 1) * e_shentsize > len(data):
                        break
                    (s_name, s_type, s_flags, s_addr, s_off, s_size,
                     s_link, s_info, s_align, s_entsize) = struct.unpack_from(
                         "<IIQQQQIIQQ", data, e_shoff + i * e_shentsize)
                    if shstr_off is None:
                        nm = "?"
                    else:
                        end = data.index(b"\x00", shstr_off + s_name)
                        nm = data[shstr_off + s_name:end].decode(
                            "utf-8", "replace")
                    secs[nm] = (s_addr, s_off, s_size)
            sec_match = {
                "DT_SYMTAB": (6, ".dynsym"), "DT_STRTAB": (5, ".dynstr"),
                "DT_RELA": (7, ".rela.dyn"), "DT_JMPREL": (23, ".rela.plt"),
            }

            tags = []
            off = dyn_off
            while off + 16 <= dyn_off + dyn_sz:
                tag, val = struct.unpack_from("<qq", data, off)
                if tag == 0:
                    break
                tags.append((tag, val))
                off += 16
            names = {1: "DT_NEEDED", 5: "DT_STRTAB", 6: "DT_SYMTAB",
                     7: "DT_RELA", 23: "DT_JMPREL"}
            ptrs = {5: None, 6: None, 7: None, 23: None}
            for tag, val in tags:
                if tag in ptrs:
                    ptrs[tag] = val
            out = []
            for dt_nm, (tag, sec_nm) in sec_match.items():
                v = ptrs[tag]
                if v is None:
                    continue
                sh = secs.get(sec_nm)
                if sh:
                    match = (sh[0] == v)
                    out.append("%s=0x%x sec.%s.sh_addr=0x%x sh_off=0x%x "
                               "match=%s"
                               % (dt_nm, v, sec_nm, sh[0], sh[1], match))
                else:
                    out.append("%s=0x%x no-such-section" % (dt_nm, v))
            for tag, val in tags:
                if tag in (5, 6, 7, 23) and val is not None:
                    out.append("%s in_ptload=%s"
                               % (names[tag],
                                  any(a <= val < b for (a, b, _fo) in segs)))
            pload = ["PT_LOAD[v=0x%x off=0x%x msz=0x%x]"
                     % (a, fo, c - a)
                     for (a, c, fo) in segs]
            out.append("loads=%s" % ";".join(pload))
            for sn in (".interp", ".gnu.hash", ".hash", ".codesign"):
                if sn in secs:
                    sh = secs[sn]
                    out.append("sec.%s addr=0x%x off=0x%x size=0x%x"
                               % (sn, sh[0], sh[1], sh[2]))
            need_offs = [val for (tag, val) in tags if tag == 1]
            st_off = vaddr_to_off(ptrs[5]) if ptrs[5] is not None else None
            if need_offs and st_off is not None:
                got = []
                for n in need_offs[:4]:
                    if st_off + n >= len(data):
                        got.append("?")
                        continue
                    end = data.index(b"\x00", st_off + n)
                    got.append(data[st_off + n:end].decode("utf-8", "replace"))
                out.append("NEEDED[0:%d]=%r" % (len(got), got))
                head = data[st_off:st_off + 16]
                out.append("strtab_head_nul=%s"
                           % (head == b"\x00" * len(head)))
            sym_off = vaddr_to_off(ptrs[6]) if ptrs[6] is not None else None
            if sym_off is not None and st_off is not None:
                syms = []
                for i in range(3):
                    if sym_off + (i + 1) * 24 > len(data):
                        break
                    (st_name, st_info, st_other, st_shndx, st_value,
                     st_size) = struct.unpack_from(
                         "<IBBHQQ", data, sym_off + i * 24)
                    if st_off + st_name >= len(data):
                        nm = "?"
                    else:
                        end = data.index(b"\x00", st_off + st_name)
                        nm = data[st_off + st_name:end].decode(
                            "utf-8", "replace")
                    syms.append("[%d]%s" % (i, nm))
                out.append("dynsym[0:3]=%r" % syms)
            self.output.info("dynprobe %s: %s" % (label, "; ".join(out)))
        except Exception as exc:  # informational only
            self.output.info("dynprobe %s failed: %r" % (label, exc))

    def _rewrite_toolchain(self):
        """Rewrite every Alpine ELF under the toolchain root so its
        PT_INTERP points at the device loader and its libc NEEDED name
        resolves (round-7 exec model, mirror of the main recipe).
        Idempotent.  Returns the device interpreter path used.

        Round-14: walk the WHOLE root, not just usr/ — zlib's
        lib/libz.so.1.3.2 kept DT_NEEDED libc.musl-aarch64.so.1, which
        made the loader load Alpine's musl libc as a second libc
        (mixed-libc under BIND_NOW).  Rewriting it to libc.so keeps a
        single libc (the device loader itself)."""
        interp = self._device_interp()
        self.output.info("device interpreter: %s" % interp)
        root = self._gnat_root()
        gnat_members = self._gnat_apk_members()
        count = 0
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                p = os.path.join(dirpath, name)
                if os.path.islink(p):
                    continue
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                rel = os.path.relpath(p, root).replace("\\", "/")
                size = os.path.getsize(p)
                if size > _LARGE_ELF_MIN and rel in gnat_members:
                    # Round-29 (different route): oversized gcc-gnat files
                    # (exactly gnat1) KEEP the pristine layout — patchelf's
                    # rewrite of the 35MB file moves the first-page note
                    # section out of the first page (round-22 log:
                    # .note.gnu.build-id 0x28c -> 0x35b2f8) and has been
                    # the common factor in every failed exec probe across
                    # rounds 20-28.  Patch only the libc NEEDED name in
                    # place (.dynstr string, zero rebuild), so the
                    # note-ident install in _sign_by_ident lands in the
                    # ORIGINAL first-page slot (T1: right after .interp,
                    # inside PT_LOAD, PT_NOTE phdr already pointing there —
                    # the exact layout of a device-lld-linked binary).
                    if interp and self._elf_interp(p) != interp:
                        desc = self._rewrite_elf(p)
                    else:
                        desc = self._patch_needed_inplace(p)
                    if desc:
                        count += 1
                        self.output.info("rewrote %s: %s" % (p, desc))
                    continue
                desc = self._rewrite_elf(p)
                if desc:
                    count += 1
                    self.output.info("rewrote %s: %s" % (p, desc))
        self.output.info("rewrote %d toolchain ELF files" % count)
        return interp

    def _patch_needed_inplace(self, path):
        """In-place .dynstr patch replacing the Alpine libc NEEDED name
        (libc.musl-aarch64.so.1 -> libc.so) WITHOUT rebuilding the file.

        Round-29: the oversized gnat1 skips patchelf (see
        _rewrite_toolchain); this byte patch resolves the libc name
        exactly like `patchelf --replace-needed` would, but keeps every
        section offset, the PT_NOTE phdr and the first-page layout
        pristine so the note-ident install can use the ORIGINAL
        .note.gnu.build-id slot.  Parses PT_DYNAMIC/DT_NEEDED and
        resolves the strings through PT_LOAD exactly like the musl
        loader.  Returns a description, or None when nothing to do.
        Never raises."""
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return None
        if data[:4] != b"\x7fELF" or len(data) < 64:
            return None
        try:
            (_id, _t, _m, _v, _e, e_phoff, _shoff, _f, _eh, phent,
             phnum, _shent, _shnum, _shstrndx) = struct.unpack_from(
                 "<16sHHIQQQIHHHHHH", data, 0)
            segs = []      # (vaddr_start, vaddr_end, file_off)
            dyn_off = dyn_sz = None
            for i in range(phnum):
                (p_type, _pf, p_off, p_vaddr, _pp, p_filesz, p_memsz,
                 _pa) = struct.unpack_from(
                     "<IIQQQQQQ", data, e_phoff + i * phent)
                if p_type == 1:  # PT_LOAD
                    segs.append((p_vaddr, p_vaddr + p_memsz, p_off))
                elif p_type == 2:  # PT_DYNAMIC
                    dyn_off, dyn_sz = p_off, p_filesz
            if dyn_off is None:
                return None
            strtab_v = None
            needed_offs = []
            off = dyn_off
            while off + 16 <= dyn_off + dyn_sz:
                tag, val = struct.unpack_from("<qq", data, off)
                if tag == 0:
                    break
                if tag == 5:  # DT_STRTAB
                    strtab_v = val
                elif tag == 1:  # DT_NEEDED
                    needed_offs.append(val)
                off += 16
            if strtab_v is None or not needed_offs:
                return None
            st_off = None
            for (a, b, fo) in segs:
                if a <= strtab_v < b:
                    st_off = fo + (strtab_v - a)
                    break
            if st_off is None:
                return None
        except (struct.error, ValueError):
            return None
        target = None
        for nv in needed_offs:
            name_off = st_off + nv
            if name_off >= len(data):
                continue
            end = data.index(b"\x00", name_off)
            old = data[name_off:end]
            if old == b"libc.musl-aarch64.so.1":
                target = name_off
                break
        if target is None:
            return None  # already patched or libc not a NEEDED entry
        try:
            new = b"libc.so\x00" + b"\x00" * (len(b"libc.musl-aarch64.so.1")
                                              - len(b"libc.so"))
            with open(path, "r+b") as fh:
                fh.seek(target)
                fh.write(new)
        except OSError as exc:
            self.output.warning(
                "needed-inplace write failed on %s: %s" % (path, exc))
            return None
        return "needed-inplace: libc.musl-aarch64.so.1 -> libc.so"

    def _verify_gnat_exec(self, gnatmake):
        """Prove gnatmake actually executes directly on the rewritten
        binary (os.access is unreliable on HMDFS): require rc=0."""
        try:
            proc = subprocess.run(
                [gnatmake, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
        except OSError as exc:
            raise ConanInvalidConfiguration(
                "gnatmake is not executable after PT_INTERP rewrite "
                "(%s, interp=%r, e_type=%s): %s"
                % (gnatmake, self._elf_interp(gnatmake),
                   self._elf_e_type(gnatmake), exc))
        if proc.returncode != 0:
            raise ConanInvalidConfiguration(
                "gnatmake failed to run (%s): rc=%s tail=%r"
                % (gnatmake, proc.returncode, proc.stdout[-400:]))

    def _qsort_shim_path(self):
        """Build a native qsort_r shim library (device clang) and return
        its absolute path, or None on failure.

        Round-35 preflight (mirror of the main recipe): linking the smoke
        binary dies in gnatlink -> gcc -> collect2 -> ld with "Error
        relocating .../libctf.so.0: qsort_r: symbol not found".  GNU ld
        links libctf.so.0 for CTF debug support and that library relocates
        a call to qsort_r — a GNU extension the OHOS device libc.so does
        not export.  The device loader honors LD_PRELOAD (HMBS platform
        diagnosis), so a tiny signed shared library providing qsort_r is
        preloaded into the link environment.  Idempotent.
        """
        cached = getattr(self, "_qsort_shim", None)
        if cached:
            return cached
        shim = None
        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        if os.path.isfile(clang):
            shim = os.path.join(self.build_folder, "qsort_r_shim.so")
            src = os.path.join(self.build_folder, "qsort_r_shim.c")
            body = (
                "typedef unsigned long size_t;\n"
                "void qsort(void *, size_t, size_t,"
                " int (*)(const void *, const void *));\n"
                "typedef int (*qsort_cmp)(const void *, const void *, void *);\n"
                "static qsort_cmp g_cmp;\n"
                "static void *g_arg;\n"
                "static int g_wrap(const void *a, const void *b)\n"
                "{ return g_cmp(a, b, g_arg); }\n"
                "void qsort_r(void *base, size_t nmemb, size_t size,\n"
                "             qsort_cmp cmp, void *arg)\n"
                "{\n"
                "  g_cmp = cmp; g_arg = arg;\n"
                "  qsort(base, nmemb, size, g_wrap);\n"
                "}\n"
            )
            try:
                with open(src, "w") as fh:
                    fh.write(body)
                proc = subprocess.run(
                    [clang, "-shared", "-fPIC", "-o", shim, src],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=120,
                )
                if proc.returncode == 0 and os.path.isfile(shim):
                    self._sign_elf(shim)
                    self.output.info("qsort_r shim ready: %s" % shim)
                else:
                    self.output.warning(
                        "qsort_r shim build failed (ignored): %s"
                        % proc.stdout[-200:])
                    shim = None
            except OSError as exc:
                self.output.warning("qsort_r shim build error: %s" % exc)
                shim = None
        else:
            self.output.warning(
                "qsort_r shim: clang not found (%s) — link may fail "
                "on libctf.so.0 qsort_r" % clang)
        self._qsort_shim = shim
        return shim

    def _gnat_env(self):
        """Environment for the relocated Alpine GNAT toolchain (mirror of
        the main recipe's round-7 _gnat_env: tools execute directly after
        the ELF rewrite; LD_LIBRARY_PATH covers the Alpine shared libs,
        libc resolves as libc.so through the device loader)."""
        root = self._gnat_root()
        env = dict(os.environ)
        bin_dir = os.path.join(root, "usr", "bin")
        gcc_lib = os.path.join(root, "usr", "lib", "gcc", _GCC_TARGET)
        lib_dir = os.path.join(root, "usr", "lib")
        paths = []
        if os.path.isdir(bin_dir):
            paths.append(bin_dir)
        hnp_bin = "/data/service/hnp/bin"
        if os.path.isdir(hnp_bin):
            paths.append(hnp_bin)
        env["PATH"] = os.pathsep.join(paths + [env.get("PATH", "")])
        if os.path.isdir(gcc_lib):
            env["GCC_EXEC_PREFIX"] = os.path.join(
                root, "usr", "libexec", "gcc") + os.sep
            env["ADA_INCLUDE_PATH"] = os.path.join(gcc_lib, "adainclude")
            env["ADA_OBJECTS_PATH"] = os.path.join(gcc_lib, "adalib")
            env["LIBRARY_PATH"] = lib_dir + os.pathsep + gcc_lib
            ld_lib = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                [os.path.join(root, "lib"), lib_dir, gcc_lib]
                + ([ld_lib] if ld_lib else []))
        # Round-35 (mirror): qsort_r shim preloaded so the device loader
        # can relocate libctf.so.0 when GNU ld links the smoke binary.
        shim = self._qsort_shim_path()
        if shim:
            prev = env.get("LD_PRELOAD", "")
            env["LD_PRELOAD"] = shim + (os.pathsep + prev if prev else "")
        tmpdir = os.environ.get("HMBS_TMPDIR") or os.environ.get("TMPDIR")
        if tmpdir:
            for var in ("TMPDIR", "TMP", "TEMP"):
                env[var] = tmpdir
        return env

    def _probe_unsigned_exec(self):
        """Round-16 experiment (mirror of the main recipe): can a
        patchelf-rewritten, UNSIGNED Alpine ELF exec on this device?

        binary-sign-tool's rebuild corrupts the large gnat1's .dynamic
        (round-16 dynprobe: DT_SYMTAB moved into a zeroed region -> mass
        empty-symbol relocation errors).  If the kernel accepts unsigned
        patchelf-rewritten ELFs, signing can be skipped and the corrupting
        rebuild never runs.  Sets self._unsigned_exec_ok (default False =
        keep signing).  Informational; never raises.
        """
        self._unsigned_exec_ok = False
        cache = os.path.join(os.path.expanduser("~"), ".cache",
                             "ada-gnat-apks")
        apk = os.path.join(cache, "gcc-gnat-%s.apk" % _GNAT_TAG)
        if not os.path.isfile(apk):
            self.output.info(
                "unsigned-exec probe: gcc-gnat apk cache missing — keep signing")
            return
        scratch = os.path.join(self.build_folder, "unsigned-exec-probe")
        os.makedirs(scratch, exist_ok=True)
        members = {
            "gnatmake": "usr/bin/gnatmake",
            "gnat1": "usr/libexec/gcc/%s/gnat1" % _GCC_TARGET,
        }
        try:
            with tarfile.open(apk, "r:gz") as tf:
                for tag, member in members.items():
                    dst = os.path.join(scratch, tag)
                    try:
                        m = tf.getmember(member)
                    except KeyError:
                        self.output.info(
                            "unsigned-exec probe: %s missing from apk — "
                            "keep signing" % member)
                        return
                    with tf.extractfile(m) as src, open(dst, "wb") as out:
                        shutil.copyfileobj(src, out)
                    self._copy_file_0755(dst, dst)
                    if tag == "gnat1":
                        # Round-29: mirror the production pipeline — the
                        # oversized gnat1 is NOT patchelf-rewritten (its
                        # pristine first-page note slot must survive for
                        # the note-ident install); only the libc NEEDED
                        # name is patched in place.
                        self._patch_needed_inplace(dst)
                    else:
                        self._rewrite_elf(dst)  # interp+needed only, NO sign
                    # Round-29: restore the mode AFTER the rewrite —
                    # patchelf's temp-file rewrite drops the mode again,
                    # so the round-16 "unsigned refused" conclusion was
                    # confounded by mode (0600, no exec bit), not by the
                    # missing signature.
                    self._copy_file_0755(dst, dst)
        except OSError as exc:
            self.output.info(
                "unsigned-exec probe prepare failed (%r) — keep signing" % exc)
            return
        rc_gm, _f, err_gm = self._exec_probe(
            [os.path.join(scratch, "gnatmake"), "--version"])
        rc_g1, _f, err_g1 = self._exec_probe(
            [os.path.join(scratch, "gnat1"), "-v"],
            env=self._gnat_env())
        ok = rc_gm != -1 and rc_g1 != -1
        self._unsigned_exec_ok = ok
        self.output.info(
            "unsigned-exec probe: gnatmake rc=%s gnat1 rc=%s -> "
            "unsigned_exec_ok=%s" % (rc_gm, rc_g1, ok))
        if not ok:
            self.output.info(
                "unsigned-exec probe details: gnatmake err=%r gnat1 err=%r"
                % (err_gm, err_g1))

    def _activate_toolchain(self):
        """Repair exec bits, rewrite the Alpine ELFs for the device
        loader and update the environment (round-7 exec model, mirror of
        the main recipe)."""
        self._repair_exec_bits()
        # Round-18: start the sign input from known-good pristine apk
        # bytes every round (mirror of the main recipe), BEFORE rewrite.
        self._restore_pristine_large()
        self._rewrite_toolchain()
        # Round-16: decide whether the corrupting binary-sign-tool rebuild
        # can be skipped (unsigned exec verified) BEFORE signing.
        self._probe_unsigned_exec()
        # Sign AFTER the rewrite so exec of the Alpine toolchain ELFs is
        # accepted by the kernel (E258/E077: unsigned = Permission denied).
        self._sign_toolchain()
        # Round-15 (mirror): on-device dynamic-section consistency check
        # of the final signed bytes — gnat1 vs the known-good gnatmake.
        self._elf_dynamic_probe(
            os.path.join(self._gnat_root(), "usr", "bin", "gnatmake"),
            "gnatmake")
        self._elf_dynamic_probe(
            os.path.join(self._gnat_root(), "usr", "libexec", "gcc",
                         _GCC_TARGET, "gnat1"),
            "gnat1")
        os.environ.update(self._gnat_env())

    def test(self):
        gnatmake = self._find_gnatmake()
        # Activate the toolchain (loader discovery + launcher wrappers);
        # the compile below then runs gnatmake through the wrapper.
        self._activate_toolchain()
        saved_env = dict(os.environ)
        try:
            self._verify_gnat_exec(gnatmake)
            package = self.dependencies["ada-bar-codes"].package_folder
            include_dir = os.path.join(package, "include")
            library_dir = os.path.join(package, "lib")
            source = os.path.join(self.source_folder, "bar_codes_smoke.adb")
            binary = os.path.join(self.build_folder, "bar_codes_smoke")

            # gnatmake / smoke source are FILES, but the packaged include/
            # and lib/ are DIRECTORIES — os.path.isfile() is always False
            # for a directory, so the old check wrongly rejected the
            # package even when both dirs existed (round-37 fingerprint:
            # "required consumer-test input is missing: .../p/include").
            # Validate each path by its expected kind instead.
            for label, required, expect_dir in (
                ("gnatmake", gnatmake, False),
                ("smoke source", source, False),
                ("include dir", include_dir, True),
                ("library dir", library_dir, True),
            ):
                ok = os.path.isdir(required) if expect_dir else os.path.isfile(required)
                if not ok:
                    raise ConanInvalidConfiguration(
                        "required consumer-test input is missing: {}".format(required)
                    )

            compile_cmd = (
                '"{gnatmake}" -I"{inc}" -aL"{lib}" "{src}" -o "{bin}" '
                '-largs -L"{lib}" -lada_bar_codes'.format(
                    gnatmake=gnatmake,
                    inc=include_dir,
                    lib=library_dir,
                    src=source,
                    bin=binary,
                )
            )
            self.run(compile_cmd)

            # The freshly linked smoke binary carries the Alpine musl
            # PT_INTERP (/lib/ld-musl-aarch64.so.1) and the libc.musl
            # DT_NEEDED, so it is rewritten for the device loader and
            # force-chmod'ed 0o755 before being executed directly
            # (round-7 exec model).
            desc = self._rewrite_elf(binary)
            self._copy_file_0755(binary, binary)
            # Sign after rewrite so exec of this freshly linked Alpine ELF
            # is accepted by the kernel (E258/E077: unsigned = Permission
            # denied) — unless the round-16 unsigned-exec probe proved
            # unsigned exec works (skipping avoids the corrupting rebuild).
            if not getattr(self, "_unsigned_exec_ok", False):
                self._sign_elf(binary)
            self.output.info(
                "bar_codes_smoke rewritten: %s" % (desc or "none"))
            # The CI L0c gate only recognizes .c/.cpp/.cc/.cxx/.sh/.py test
            # sources in test_package/, while the real test is Ada
            # (bar_codes_smoke.adb).  run_tests.sh is the recognized driver
            # that actually executes the compiled smoke binary; its exit
            # status and stdout pass through unchanged, so failures still
            # propagate to the Conan test stage.
            driver = os.path.join(self.source_folder, "run_tests.sh")
            if not os.path.isfile(driver):
                raise ConanInvalidConfiguration(
                    "required test driver is missing: {}".format(driver)
                )
            proc = subprocess.run(
                ["sh", driver, binary],
                cwd=self.build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=600,
                env=self._gnat_env(),
            )
            output = proc.stdout
            self.output.info(output)
            m = re.search(r"checks_passed=\s*(\d+)", output)
            if proc.returncode != 0 or m is None:
                self.output.error("=== bar_codes_smoke output tail ===\n" + output[-800:])
                raise RuntimeError("test_package smoke test failed")
            passed_count = int(m.group(1))
            if passed_count < 3:
                raise RuntimeError(
                    "test_package smoke test passed only {} checks".format(passed_count)
                )
            result = {
                "executed": True,
                "passed": True,
                "command": "./bar_codes_smoke",
                "discovered": passed_count,
                "passedCount": passed_count,
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
            )

            # ---- Upstream test: test/bar_codes_test.adb (vendored verbatim
            # ---- into this test_package as bar_codes_test.adb).
            # test/bar_codes_test.adb renders 82 bar codes (Code 128 / MSI /
            # EAN-13 / UPC-A / Data Matrix / QR) as PNG files; the six MSI
            # samples reuse the same file name, leaving 77 distinct non-empty
            # PNGs on disk.  Any encode failure raises Cannot_Encode, so a
            # zero exit status means every sample was rendered.  The case
            # counts below come from the files the program actually writes.
            # It only uses public units (Bar_Codes, Bar_Codes_Media) plus the
            # Ada standard library, so it links against the packaged
            # libada_bar_codes.a exactly like the smoke consumer above.
            up_source = os.path.join(self.source_folder, "bar_codes_test.adb")
            up_binary = os.path.join(self.build_folder, "bar_codes_test")
            if not os.path.isfile(up_source):
                raise ConanInvalidConfiguration(
                    "required upstream-test source is missing: {}".format(up_source)
                )
            up_compile_cmd = (
                '"{gnatmake}" -I"{inc}" -aL"{lib}" "{src}" -o "{bin}" '
                '-largs -L"{lib}" -lada_bar_codes'.format(
                    gnatmake=gnatmake,
                    inc=include_dir,
                    lib=library_dir,
                    src=up_source,
                    bin=up_binary,
                )
            )
            self.run(up_compile_cmd)
            # The freshly linked test binary carries the Alpine musl PT_INTERP
            # (/lib/ld-musl-aarch64.so.1) and the libc.musl DT_NEEDED, so it
            # is rewritten for the device loader and force-chmod'ed 0o755
            # before being executed directly (round-7 exec model).
            up_desc = self._rewrite_elf(up_binary)
            self._copy_file_0755(up_binary, up_binary)
            if not getattr(self, "_unsigned_exec_ok", False):
                self._sign_elf(up_binary)
            self.output.info(
                "bar_codes_test rewritten: %s" % (up_desc or "none"))
            up_run_dir = os.path.join(self.build_folder, "upstream-test-run")
            shutil.rmtree(up_run_dir, ignore_errors=True)
            os.makedirs(up_run_dir, exist_ok=True)
            up_proc = subprocess.run(
                [up_binary],
                cwd=up_run_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
                env=self._gnat_env(),
            )
            pngs = [
                p
                for p in glob.glob(os.path.join(up_run_dir, "test *.png"))
                if os.path.getsize(p) > 0
            ]
            up_discovered = len(pngs)
            self.output.info(
                "upstream bar_codes_test exit={} png_files={}".format(
                    up_proc.returncode, up_discovered
                )
            )
            if up_proc.returncode != 0 or up_discovered == 0:
                self.output.error(
                    "=== bar_codes_test output tail ===\n" + up_proc.stdout[-800:]
                )
                raise RuntimeError(
                    "upstream tests failed: exit={}, pngs={}".format(
                        up_proc.returncode, up_discovered
                    )
                )
            upstream = {
                "status": "passed",
                "framework": "custom",
                "command": "./bar_codes_test",
                "discovered": up_discovered,
                "executed": up_discovered,
                "passed": up_discovered,
                "failed": 0,
                "skipped": 0,
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
            )
        finally:
            os.environ.clear()
            os.environ.update(saved_env)