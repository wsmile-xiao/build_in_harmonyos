#!/usr/bin/env python3
"""Conan 2.x recipe — dbmate 2.33.0 (Go database migration tool).

dbmate is a lightweight, framework-agnostic database migration tool
written in Go. It supports PostgreSQL, MySQL, ClickHouse, BigQuery, and
SQLite (via CGO). This recipe builds a statically-linked binary with all
drivers including SQLite (CGO_ENABLED=1).

Platform notes (HarmonyOS):
- E166 (Go linker mmap fails on HMDFS): GOCACHE, GOTMPDIR, and the
  linker -o output are routed to an ext2 partition.
- E128 (ELF signing): every ELF that is execve'd on HongMeng must carry
  a .codesign section. The produced dbmate binary and the Go toolchain
  ELFs are signed with binary-sign-tool.
- E077 (chmod semantics on HMDFS): after signing, chmod 0o755 restores
  the owner x bit; HMDFS preserves owner bits.
"""
import hashlib
import os
import shutil
import subprocess
import re
import tarfile
import urllib.request
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# ext2 partition paths that bypass HMDFS mmap restrictions (E166).
_EXT2_CACHE_CANDIDATES = [
    "/data/storage/el2/base/haps/entry/files",
    "/data/storage/el2/base/cache",
]

# ELF signing tools on the HarmonyOS PC preflight worker.
_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
_SIGNTOOL = "/data/service/hnp/bin/binary-sign-tool"

# Pre-installed Go toolchain candidates (Harmonybrew, SDK, goenv).
_SDK_GO_CANDIDATES = [
    "/storage/Users/currentUser/.harmonybrew/bin/go",
    "/storage/Users/currentUser/.goenv/shims/go",
    "/storage/Users/currentUser/.goenv/versions/1.26.3/bin/go",
    "/storage/Users/currentUser/.goenv/versions/1.26.5/bin/go",
    "/storage/Users/currentUser/sdk/go1.26.3/bin/go",
    "/storage/Users/currentUser/sdk/go/bin/go",
]

# Portable Go toolchain for self-bootstrapping when no signed SDK Go is
# available on the worker (e.g. CI buildbot workers).
_GO_TARBALL_URLS = [
    "https://golang.google.cn/dl/go1.26.3.linux-arm64.tar.gz",
    "https://dl.google.com/go/go1.26.3.linux-arm64.tar.gz",
]
_GO_TARBALL_SHA256 = "9d89a3ea57d141c2b22d70083f2c8459ba3890f2d9e818e7e933b75614936565"
_GO_VERSION = "1.26.3"


class DbmateConan(ConanFile):
    name = "dbmate"
    version = "2.33.0"
    description = "A lightweight, framework-independent database migration tool"
    license = "MIT"
    homepage = "https://github.com/amacneil/dbmate"
    topics = ("database", "migration", "cli", "go")

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("dbmate is prepared for Linux/OHOS targets only")

    # ------------------------------------------------------------------
    # Go toolchain resolution
    # ------------------------------------------------------------------
    def _ensure_go(self):
        """Locate — or self-bootstrap — a signed, executable ``go``.

        Resolution order:
        1. ``go`` already on PATH (shutil.which) and executable.
        2. SDK Go candidates under known paths.
        3. Self-bootstrap: download go1.26.3 tarball, extract to ext2,
           re-sign every toolchain ELF, cache across builds.
        """
        existing = shutil.which("go")
        if existing and os.access(existing, os.X_OK):
            self.output.info("Using Go from PATH: %s" % existing)
            return existing

        for cand in _SDK_GO_CANDIDATES:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                self.output.info("Using Go: %s" % cand)
                return cand
            if os.path.isfile(cand):
                self.output.warning(
                    "Go found at %s but not executable (E128?), continuing probe" % cand
                )

        self.output.info(
            "No signed Go on PATH or SDK paths; self-bootstrapping Go %s "
            "and re-signing toolchain ELFs (E128+E077 workaround)" % _GO_VERSION
        )
        return self._bootstrap_go()

    def _bootstrap_go(self):
        """Download, verify, extract and re-sign a portable Go toolchain.

        Cached under ext2 cache dir so the download and signing pass run
        at most once per worker.
        """
        ext2 = self._ext2_cache_dir()
        boot_root = os.path.join(ext2, "go-bootstrap", "go%s" % _GO_VERSION)
        go_bin = os.path.join(boot_root, "bin", "go")
        marker = os.path.join(boot_root, ".hmbs-signed-ok")

        # Reuse a previously signed bootstrap
        if os.path.isfile(marker) and os.path.isfile(go_bin):
            self.output.info("Reusing cached signed Go bootstrap: %s" % go_bin)
            return go_bin

        # Fresh bootstrap: download into ext2
        bootstrap_parent = os.path.dirname(boot_root)
        os.makedirs(bootstrap_parent, exist_ok=True)
        shipped_root = os.path.join(bootstrap_parent, "go")
        if os.path.isdir(shipped_root):
            shutil.rmtree(shipped_root, ignore_errors=True)
        if os.path.isdir(boot_root):
            shutil.rmtree(boot_root, ignore_errors=True)

        tarball_path = os.path.join(bootstrap_parent, "go%s.tar.gz" % _GO_VERSION)
        last_err = None
        for url in _GO_TARBALL_URLS:
            try:
                self.output.info("Downloading Go %s from %s" % (_GO_VERSION, url))
                with urllib.request.urlopen(url, timeout=120) as r, \
                        open(tarball_path, "wb") as out:
                    shutil.copyfileobj(r, out)
                last_err = None
                break
            except Exception as e:
                last_err = e
                self.output.warning("Download from %s failed: %s" % (url, e))
                continue
        if last_err is not None:
            raise ConanException(
                "Could not download Go %s from any mirror: %s" % (_GO_VERSION, last_err)
            )

        actual_sha = hashlib.sha256(open(tarball_path, "rb").read()).hexdigest()
        if actual_sha != _GO_TARBALL_SHA256:
            raise ConanException(
                "Go tarball SHA-256 mismatch: expected %s, got %s" % (_GO_TARBALL_SHA256, actual_sha)
            )
        self.output.info("Go tarball SHA-256 verified: %s" % actual_sha)

        # Extract: tarball root is `go/`, extract into parent then rename
        with tarfile.open(tarball_path, "r:gz") as tf:
            tf.extractall(bootstrap_parent)
        try:
            os.remove(tarball_path)
        except OSError:
            pass
        if not os.path.isdir(shipped_root):
            raise ConanException(
                "Go tarball extracted but %s missing" % shipped_root
            )
        os.rename(shipped_root, boot_root)

        # Re-sign every toolchain ELF for HongMeng execve (E128)
        self._sign_go_toolchain(boot_root)

        with open(marker, "w") as f:
            f.write("signed go %s\n" % _GO_VERSION)
        self.output.info("Self-bootstrapped Go ready: %s" % go_bin)
        return go_bin

    def _sign_go_toolchain(self, boot_root):
        """Re-sign every executable ELF in a freshly extracted Go tree."""
        tool_subdir = os.path.join(boot_root, "pkg", "tool", "linux_arm64")
        targets = []
        for d in (os.path.join(boot_root, "bin"), tool_subdir):
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    targets.append(p)

        signed, failed = 0, 0
        for t in targets:
            ok = self._sign_elf(t)
            if ok:
                signed += 1
            else:
                failed += 1
                self.output.warning("Failed to sign Go toolchain ELF %s" % t)
        self.output.info(
            "Signed %d Go toolchain ELFs (%d failed)" % (signed, failed)
        )
        if failed:
            raise ConanException(
                "Go toolchain ELF signing failed for %d files" % failed
            )

    @staticmethod
    def _goroot_for_go(go_bin):
        """Derive GOROOT from the go binary path."""
        go_path = Path(go_bin).resolve()
        goroot = go_path.parent.parent
        if go_path.parent.name == "bin" and (goroot / "pkg").is_dir():
            return str(goroot)
        # Harmonybrew symlink layout: .../bin/go -> .../Cellar/go/1.26.5/libexec/bin/go
        if (goroot / "pkg").is_dir():
            return str(goroot)
        return None

    def _check_go_version(self, go_bin):
        """Verify Go version meets minimum requirement (1.25.0)."""
        try:
            output = subprocess.check_output(
                [go_bin, "version"], text=True, stderr=subprocess.STDOUT
            ).strip()
        except (subprocess.CalledProcessError, OSError) as e:
            raise ConanInvalidConfiguration(
                "Failed to execute '%s version': %s" % (go_bin, e)
            )
        self.output.info("Go version: %s" % output)
        match = re.search(r"go(\d+)\.(\d+)", output)
        if not match:
            raise ConanInvalidConfiguration("Unable to parse Go version from: %s" % output)
        major, minor = int(match.group(1)), int(match.group(2))
        if (major, minor) < (1, 25):
            raise ConanInvalidConfiguration(
                "dbmate 2.33.0 requires Go >= 1.25, got: %s" % output
            )

    # ------------------------------------------------------------------
    # ext2 cache (E166 workaround)
    # ------------------------------------------------------------------
    def _ext2_cache_dir(self):
        """Pick a writable ext2 directory for GOCACHE/GOTMPDIR/linker output."""
        for base in _EXT2_CACHE_CANDIDATES:
            candidate = os.path.join(base, "dbmate-2.33.0")
            try:
                os.makedirs(candidate, exist_ok=True)
                with open(os.path.join(candidate, ".wprobe"), "wb") as f:
                    f.write(b"0")
                os.remove(os.path.join(candidate, ".wprobe"))
                self.output.info("Using ext2 cache dir: %s" % candidate)
                return candidate
            except OSError:
                continue
        fallback = os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp"
        self.output.warning(
            "No writable ext2 cache dir found; falling back to %s (E166 may follow)" % fallback
        )
        return fallback

    # ------------------------------------------------------------------
    # ELF signing (E128/E077)
    # ------------------------------------------------------------------
    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf(self, path):
        """Sign one ELF in place for HongMeng execve (E077 four-step)."""
        if str(self.settings.os) != "OHOS":
            return True
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return True
        if not os.path.isfile(path):
            return False
        # Step 1: remove stale .codesign
        self.run(
            "%s --remove-section .codesign %s" % (_OBJCOPY, path),
            env=None, quiet=True, stderr=subprocess.DEVNULL,
        )
        # Step 2: self-sign
        rc = self.run(
            "%s sign -selfSign 1 -inFile %s -outFile %s" % (_SIGNTOOL, path, path),
            env=None, quiet=True, stderr=subprocess.DEVNULL,
        )
        if rc != 0:
            return False
        # Step 3: restore owner x bit
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass
        return os.access(path, os.X_OK)

    # ------------------------------------------------------------------
    # Go environment
    # ------------------------------------------------------------------
    def _go_env(self):
        """Build the Go environment for HarmonyOS."""
        go_bin = self._ensure_go()
        self._check_go_version(go_bin)

        go_bin_dir = os.path.dirname(go_bin)
        goroot = self._goroot_for_go(go_bin)
        ext2_cache = self._ext2_cache_dir()

        gopath = os.path.join(ext2_cache, "gopath")
        gocache = os.path.join(ext2_cache, "go-cache")
        gotmpdir = os.path.join(ext2_cache, "go-tmp")
        os.makedirs(gopath, exist_ok=True)
        os.makedirs(gocache, exist_ok=True)
        os.makedirs(gotmpdir, exist_ok=True)

        env = {
            "CGO_ENABLED": "1",
            "GOPROXY": "https://goproxy.cn,direct",
            "GOSUMDB": "sum.golang.google.cn",
            "GOFLAGS": "-mod=mod",
            "GOTOOLCHAIN": "local",
            "GOPATH": gopath,
            "GOCACHE": gocache,
            "GOTMPDIR": gotmpdir,
            "TMPDIR": gotmpdir,
            "TEMP": gotmpdir,
            "PATH": "%s%s%s" % (go_bin_dir, os.pathsep, os.environ.get("PATH", "")),
        }
        if goroot:
            env["GOROOT"] = goroot
        # CC/CXX for CGO (go-sqlite3 C compilation)
        if shutil.which("clang"):
            env["CC"] = shutil.which("clang")
        if shutil.which("clang++"):
            env["CXX"] = shutil.which("clang++")
        return env, go_bin

    def _run_go(self, cmd, env, cwd):
        """Run a Go command with the env dict actually applied."""
        saved = {}
        for k, v in env.items():
            saved[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            return self.run(cmd, env=None, cwd=cwd)
        finally:
            for k, old in saved.items():
                if old is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = old

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def generate(self):
        from conan.tools.env import Environment
        env = Environment()
        env.define("CGO_ENABLED", "1")
        env.define("GOPROXY", "https://goproxy.cn,direct")
        env.define("GOSUMDB", "sum.golang.google.cn")
        env.define("GOTOOLCHAIN", "local")
        env.vars(self).save_script("dbmate_go_env")

    def build(self):
        apply_conandata_patches(self)
        env, go_bin = self._go_env()
        ext2_cache = self._ext2_cache_dir()
        src = self.source_folder

        # Sanity-probe Go execve
        self._run_go("%s version" % go_bin, env, cwd=src)

        # Pre-download all modules
        self._run_go("%s mod download" % go_bin, env, cwd=src)

        # Build with CGO for SQLite support, matching upstream Makefile for Linux
        ext2_out = os.path.join(ext2_cache, "dbmate")
        build_out = os.path.join(self.build_folder, "dbmate")

        self._run_go(
            '%s build -tags netgo,osusergo,sqlite_omit_load_extension,sqlite_fts5,sqlite_json '
            '-ldflags "-s -extldflags -static" -o %s .' % (go_bin, ext2_out),
            env,
            cwd=src,
        )
        if not os.path.isfile(ext2_out):
            raise ConanException(
                "go build did not produce %s (E166 linker-mmap failure?)" % ext2_out
            )

        # Sign the produced ELF for HarmonyOS (E128)
        if not self._sign_elf(ext2_out):
            raise ConanException(
                "ELF signing of %s failed (binary-sign-tool/llvm-objcopy unavailable?)"
                % ext2_out
            )
        shutil.copy2(ext2_out, build_out)

    def package(self):
        copy(self, "dbmate", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
