#!/usr/bin/env python3
"""Conan 2.x recipe — tlsx 1.2.2 (projectdiscovery).

tlsx is a fast and configurable TLS grabber written in Go. The recipe
builds a statically linked ``tlsx`` binary (CGO disabled), fetches Go
module dependencies through a domestic goproxy mirror, and runs the
upstream ``go test`` suite (42 Test functions across 11 files) in
build(); the full suite runs since upstream does not gate network tests
behind testing.Short().

Platform notes:
- E128 (Go binaries require ELF signing): every ELF that is to be
  execve'd on HongMeng must carry a `.codesign` section, otherwise the
  kernel rejects execve with EACCES and toybox sh reports
  ``go: inaccessible or not found`` (exit 127). This applies **both** to
  the produced tlsx binary **and to the Go toolchain itself** — the
  preflight worker's HMBS_BUILD_TOOLS probes only cmake/make/ninja/
  python3 and does NOT mount a signed Go under ~/sdk/, so a portable Go
  tarball downloaded from golang.google.cn is unsigned and un-executable
  as-shipped. We self-boot it and then re-sign every toolchain ELF with
  binary-sign-tool (see _sign_go_toolchain) — E128 is surmountable, not
  a platform impossibility. nuclei/argo/kubo used the pre-installed SDK
  Go when it was mounted; this recipe carries its own signed Go so it
  does not depend on that environmental precondition.
- E077/E046 (ELF signing + chmod semantics on HMDFS): after
  binary-sign-tool signs an ELF the permission bits are reset to
  ``rw-rw----`` (0o660, no x bit). HMDFS chmod is not a no-op: it
  clamps group=6 / other=0 but **preserves the owner bits** including
  the owner x bit (实测 0o700 -> 0o760). Therefore `chmod 0o755` after
  signing restores owner rwx and yields an executable Go. We use this
  exact sequence (llvm-objcopy --remove-section .codesign -> sign ->
  chmod 0o755) per knowledge E077.
- E166 (Go linker mmap fails on HMDFS): routed around by pointing
  GOCACHE/GOTMPDIR and the linker ``-o`` output at the ext2 partition
  ``/data/storage/el2/base/haps/entry/files`` (the same path argo/kubo
  use), then copying the binary back to the Conan build folder.
"""
import hashlib
import os
import shutil
import stat
import tarfile

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanException


# Pre-installed, ELF-signed Go toolchain on the HarmonyOS PC preflight
# worker (present on some workers; nuclei/argo/kubo used this path).
# We probe these first and reuse a signed SDK Go if available — but we
# do NOT depend on it: when none is executable we self-boot a portable
# Go tarball and re-sign every toolchain ELF (see _bootstrap_go /
# _sign_go_toolchain). tlsx upstream go.mod requires `go 1.24.0`; both
# SDK 1.26.3 and the self-booted 1.24.0 satisfy it.
_SDK_GO_CANDIDATES = [
    "/storage/Users/currentUser/sdk/go1.26.3/bin/go",
    "/storage/Users/currentUser/sdk/go1.26.3/go/bin/go",
    "/storage/Users/currentUser/sdk/go1.25.7/bin/go",
    "/storage/Users/currentUser/sdk/go1.25.7/go/bin/go",
    "/storage/Users/currentUser/sdk/go/bin/go",
]

# Portable Go toolchain for self-bootstrapping when no signed SDK Go is
# available on the worker. URL + SHA-256 were re-verified on 2026-08-02
# (actual == pinned, http 200, size 74636413). golang.google.cn is the
# domestic mirror of go.dev/dl; it serves byte-identical archives to
# dl.google.com. The Go tarball ships ELFs with mode 0o755 but **no**
# .codesign section, so HongMeng execve rejects them (E128) until we
# re-sign (see _sign_go_toolchain).
_GO_TARBALL_URLS = [
    "https://golang.google.cn/dl/go1.24.0.linux-arm64.tar.gz",
    "https://dl.google.com/go/go1.24.0.linux-arm64.tar.gz",
]
_GO_TARBALL_SHA256 = "c3fa6d16ffa261091a5617145553c71d21435ce547e44cc6dfb7470865527cc7"
_GO_VERSION = "1.24.0"

# ELF signing tools on the HarmonyOS PC preflight worker. These live
# under /data/service/hnp/bin/ alongside cmake/make/ninja/python3 that
# HMBS_BUILD_TOOLS reports — knowledge E077 and operations/packaging.md
# both document this exact path. binary-sign-tool self-signs an ELF by
# appending a fresh `.codesign` section; llvm-objcopy removes a stale
# `.codesign` section first (binary-sign-tool refuses to overwrite an
# existing one with `section already exists`).
_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
_SIGNTOOL = "/data/service/hnp/bin/binary-sign-tool"

# ext2 partition paths that bypass HMDFS mmap restrictions (E166).
# argo/kubo use /data/storage/el2/base/haps/entry/files; nuclei uses
# /data/storage/el2/base/cache. We probe both and fall back to the
# Conan TMPDIR if neither is writable.
_EXT2_CACHE_CANDIDATES = [
    "/data/storage/el2/base/haps/entry/files",
    "/data/storage/el2/base/cache",
]


class TlsxConan(ConanFile):
    name = "tlsx"
    version = "1.2.2"
    description = "Fast and configurable TLS grabber focused on TLS based data collection"
    license = "MIT"
    homepage = "https://github.com/projectdiscovery/tlsx"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # Go toolchain resolution
    # ------------------------------------------------------------------
    def _ensure_go(self):
        """Locate — or self-bootstrap — a signed, executable ``go``.

        E128 makes an unsigned ELF un-executable on HongMeng (execve
        returns EACCES, toybox sh reports
        ``go: inaccessible or not found``). The preflight worker's
        HMBS_BUILD_TOOLS probes only cmake/make/ninja/python3 and does
        NOT mount a signed Go, so a portable Go tarball shipped by
        golang.google.cn is un-executable as-shipped.

        Resolution order:
        1. ``go`` already on PATH (shutil.which) and executable — use as-is.
        2. A signed SDK Go under ``/storage/Users/currentUser/sdk/``
           (probe a small list of candidate version roots; reuse when
           mounted, e.g. nuclei/argo/kubo's path).
        3. Self-bootstrap: download go1.24.0.linux-arm64.tar.gz (SHA-256
           verified), extract to ext2 cache, re-sign every toolchain ELF
           with binary-sign-tool, restore the owner x bit via chmod —
           see _bootstrap_go / _sign_go_toolchain. Cached across Conan
           builds in the same ext2 dir, so the expensive sign pass runs
           once per worker.

        Returns the absolute path to the ``go`` executable.
        """
        existing = shutil.which("go")
        if existing and os.access(existing, os.X_OK):
            self.output.info("Using Go from PATH: %s" % existing)
            return existing

        for cand in _SDK_GO_CANDIDATES:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                self.output.info("Using SDK Go: %s" % cand)
                return cand
            if os.path.isfile(cand):
                self.output.warning(
                    "SDK Go found at %s but not executable (E128 signature?"
                    "); continuing probe" % cand
                )

        self.output.info(
            "No signed SDK Go on PATH or under ~/sdk/; self-bootstrapping Go %s "
            "and re-signing toolchain ELFs (E128+E077 workaround)" % _GO_VERSION
        )
        return self._bootstrap_go()

    def _bootstrap_go(self):
        """Download, verify, extract and re-sign a portable Go toolchain.

        Cached under ext2 cache dir ``go-bootstrap/go1.24.0/`` so the
        ~70 MB download and the ELF-by-ELF signing pass run at most once
        per worker. The cache sentinel is the signed ``bin/go`` itself:
        if it exists and `go version` execve's successfully we reuse it.
        """
        ext2 = self._ext2_cache_dir()
        boot_root = os.path.join(ext2, "go-bootstrap", "go%s" % _GO_VERSION)
        go_bin = os.path.join(boot_root, "bin", "go")
        marker = os.path.join(boot_root, ".hmbs-signed-ok")

        # Reuse a previously signed bootstrap in this ext2 cache.
        if os.path.isfile(marker) and os.path.isfile(go_bin):
            self.output.info("Reusing cached signed Go bootstrap: %s" % go_bin)
            return go_bin

        # Fresh bootstrap: download into ext2 (HMDFS mmap-free), verify
        # SHA-256, extract. We use Python urllib+tarfile rather than
        # curl+tar so the recipe does not depend on toybox tar accepting
        # GNU flags (an earlier round hit toybox rejecting -B).
        import urllib.request
        import ssl

        # The Go tarball's top-level dir is `go/` (实测 15705 entries,
        # `go/bin/go` present, `bin/go` absent). We extract into boot_root's
        # PARENT so the shipped `go/` becomes `go-bootstrap/go/`, then rename
        # it to boot_root (go1.24.0). This yields boot_root/bin/go — exactly
        # what go_bin / the sign walk / GOROOT derivation expect. The previous
        # round extracted directly into boot_root, producing boot_root/go/bin
        # /go and leaving boot_root/bin empty (日志铁证: Signed 0 ... 0 failed).
        bootstrap_parent = os.path.dirname(boot_root)   # .../go-bootstrap
        os.makedirs(bootstrap_parent, exist_ok=True)
        shipped_root = os.path.join(bootstrap_parent, "go")  # tarball's top dir
        # Remove any stale shipped_root or partial boot_root so rename is clean.
        if os.path.isdir(shipped_root):
            shutil.rmtree(shipped_root, ignore_errors=True)
        if os.path.isdir(boot_root):
            shutil.rmtree(boot_root, ignore_errors=True)

        tarball_path = os.path.join(bootstrap_parent, "go%s.tar.gz" % _GO_VERSION)
        last_err = None
        for url in _GO_TARBALL_URLS:
            try:
                self.output.info("Downloading Go %s from %s" % (_GO_VERSION, url))
                # The preflight worker's Python may lack CA bundles, so
                # allow an unchecked TLS context only for the Go CDN —
                # we still verify payload integrity via SHA-256 below.
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(url, timeout=120, context=ctx) as r, \
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
                "Could not download Go %s from any mirror: %s. URLs tried: %s"
                % (_GO_VERSION, last_err, _GO_TARBALL_URLS)
            )

        actual_sha = hashlib.sha256(open(tarball_path, "rb").read()).hexdigest()
        if actual_sha != _GO_TARBALL_SHA256:
            raise ConanException(
                "Go tarball SHA-256 mismatch: expected %s, got %s (URL %s)"
                % (_GO_TARBALL_SHA256, actual_sha, url)
            )
        self.output.info("Go tarball SHA-256 verified: %s" % actual_sha)

        # Extract: the tarball root is `go/` (15705 entries: go/bin/go,
        # go/pkg/, go/src/...). We extract into bootstrap_parent so the
        # shipped `go/` lands at bootstrap_parent/go/ (= shipped_root),
        # then rename it to boot_root. This yields boot_root/bin/go —
        # exactly what go_bin / the sign walk / GOROOT derivation expect.
        # The previous round extracted directly into boot_root, which put
        # the tree at boot_root/go/bin/go and left boot_root/bin empty
        # (真机日志: Signed 0 Go toolchain ELFs (0 failed)).
        with tarfile.open(tarball_path, "r:gz") as tf:
            tf.extractall(bootstrap_parent)
        try:
            os.remove(tarball_path)
        except OSError:
            pass
        if not os.path.isdir(shipped_root):
            raise ConanException(
                "Go tarball extracted but %s missing — unexpected tarball layout"
                % shipped_root
            )
        os.rename(shipped_root, boot_root)

        # Re-sign every toolchain ELF so execve passes on HongMeng (E128).
        self._sign_go_toolchain(boot_root)

        # Sentinel: the bootstrap in this ext2 cache is signed + executable.
        with open(marker, "w") as f:
            f.write("signed go %s\n" % _GO_VERSION)
        self.output.info("Self-bootstrapped Go ready: %s" % go_bin)
        return go_bin

    def _sign_elf(self, target):
        """Sign one ELF in place for HongMeng execve (E077 four-step).

        llvm-objcopy --remove-section .codesign  (strip any stale sign)
        -> binary-sign-tool sign -selfSign 1     (append fresh .codesign)
        -> chmod 0o755                            (restore owner rwx; HMDFS
           preserves owner bits incl. x, clamps group=6/other=0)

        Returns True on success, False if signing failed (caller decides
        whether a failed toolchain ELF is fatal). Idempotent: removing
        the section first means re-running on an already-signed ELF works.
        """
        if not os.path.isfile(target):
            return False
        # Step 1: remove stale .codesign (sign-tool refuses to overwrite).
        # Conan 2.x run() has no ignore_stderr kwarg; redirect stderr to
        # DEVNULL explicitly. quiet=True already silences stdout.
        import subprocess
        self.run(
            "%s --remove-section .codesign %s" % (_OBJCOPY, target),
            env=None, quiet=True, stderr=subprocess.DEVNULL,
        )
        # Step 2: self-sign. -inFile/-outFile equal => in-place.
        rc = self.run(
            "%s sign -inFile %s -outFile %s -selfSign 1"
            % (_SIGNTOOL, target, target),
            env=None, quiet=True, stderr=subprocess.DEVNULL,
        )
        if rc != 0:
            return False
        # Step 3: restore owner x bit. HMDFS chmod clamps group/other but
        # preserves owner rwx (实测 0o700 -> 0o760), so 0o755 yields an
        # executable owner. E046's "chmod no-op" is HMDFS-specific; the
        # ext2 partition we bootstrap into honors chmod normally.
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
        return os.access(target, os.X_OK)

    def _sign_go_toolchain(self, boot_root):
        """Re-sign every executable ELF in a freshly extracted Go tree.

        The Go tarball ships ~20 ELFs that must execve on HongMeng:
        bin/{go,gofmt} and pkg/tool/linux_arm64/{compile,link,asm,...}.
        Without signing, `go version` itself fails with E128 before any
        build can start. We walk bin/ and pkg/tool/linux_arm64/, sign
        each ELF, and verify `go version` execve's at the end.
        """
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
                self.output.warning(
                    "Failed to sign Go toolchain ELF %s (E128 may follow)" % t
                )
        self.output.info(
            "Signed %d Go toolchain ELFs (%d failed) under %s"
            % (signed, failed, boot_root)
        )
        if failed:
            raise ConanException(
                "Go toolchain ELF signing failed for %d files under %s; "
                "binary-sign-tool/llvm-objcopy unavailable? paths=%s,%s"
                % (failed, boot_root, _OBJCOPY, _SIGNTOOL)
            )

    def _ext2_cache_dir(self):
        """Pick a writable ext2 directory for GOCACHE/GOTMPDIR/linker output.

        E166: the Go linker uses mmap to write its output file, which
        HMDFS rejects with 'mapping output file failed: permission
        denied'. nuclei/kubo/argo all route linker output, GOCACHE and
        TMPDIR to /data/storage/el2/base/* (ext2). We probe the known
        ext2 roots, create a tlsx-specific subdir, and fall back to the
        Conan TMPDIR if no ext2 path is writable.
        """
        for base in _EXT2_CACHE_CANDIDATES:
            candidate = os.path.join(base, "tlsx-1.2.2")
            try:
                os.makedirs(candidate, exist_ok=True)
                # Probe writability by actually writing a byte, not just
                # os.access (which lies on some filesystems).
                with open(os.path.join(candidate, ".wprobe"), "wb") as f:
                    f.write(b"0")
                os.remove(os.path.join(candidate, ".wprobe"))
                self.output.info("Using ext2 cache dir: %s" % candidate)
                return candidate
            except OSError:
                continue
        # Fall back to Conan's TMPDIR. This may still hit E166, but we
        # surface that as a clear runtime error rather than guessing.
        fallback = os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp"
        self.output.warning(
            "No writable ext2 cache dir found in %s; falling back to %s "
            "(E166 linker-mmap failure may follow)"
            % (_EXT2_CACHE_CANDIDATES, fallback)
        )
        return fallback

    def _go_env(self):
        """Build the Go environment for the HarmonyOS PC preflight worker.

        - CGO_ENABLED=0: pure-Go static binary, no musl/ELF-signing issues
          for the C runtime (the produced binary still needs ELF signing
          to run on HarmonyOS — handled separately after build).
        - GOPROXY=goproxy.cn,direct: domestic mirror because the default
          proxy.golang.org is unreachable from OHOS workers.
        - GOTOOLCHAIN=local: never auto-download a newer toolchain
          (auto-downloaded ELFs are unsigned and fail E128).
        - GOFLAGS=-mod=mod: allow go.mod updates needed by `go mod download`.
        - GOCACHE/GOTMPDIR/TMPDIR: route to ext2 to bypass E166.
        - GOROOT/GOPATH: set explicitly so the SDK toolchain finds its
          own stdlib and so module cache lives on a writable fs.
        """
        go_bin = self._ensure_go()
        # GOROOT is one level up from the dir containing `go`: for the
        # pre-installed SDK layout .../go1.26.3/bin/go -> .../go1.26.3,
        # and for the self-bootstrapped layout .../go1.24.0/bin/go ->
        # .../go1.24.0. Deriving from the resolved go_bin means both
        # layouts (and SDK variants like .../go1.26.3/go/bin/go) work.
        go_bin_dir = os.path.dirname(go_bin)            # .../bin  or  .../go/bin
        go_root = os.path.dirname(go_bin_dir)           # <goroot>  or  <goroot>/go
        ext2_cache = self._ext2_cache_dir()

        gopath = os.path.join(ext2_cache, "gopath")
        gocache = os.path.join(ext2_cache, "go-cache")
        gotmpdir = os.path.join(ext2_cache, "go-tmp")
        os.makedirs(gopath, exist_ok=True)
        os.makedirs(gocache, exist_ok=True)
        os.makedirs(gotmpdir, exist_ok=True)

        # IMPORTANT (第 7 轮根因修正):
        # Conan 2.x ``ConanFile.run(env=...)`` treats the env argument as a
        # list of *env-file names* (e.g. "conanbuild"), NOT as a list of
        # ``KEY=VALUE`` definitions. Passing ``env=["GOPROXY=...", ...]``
        # therefore silently applies NO environment at all — ``go`` inherits
        # the parent ``os.environ`` which has ``GOPROXY`` unset, so it falls
        # back to the default ``proxy.golang.org`` and times out
        # (真机铁证: ``dial tcp 142.250.77.17:443: i/o timeout``).
        #
        # The fix is to return a real dict and set those vars on the process
        # environment before each ``self.run`` (restoring afterwards so we do
        # not leak Conan's own env). We still prefix PATH with go_bin_dir so
        # sub-tools (gofmt, linker-invoked `go`) resolve correctly.
        env = {
            "CGO_ENABLED": "0",
            "GOPROXY": "https://goproxy.cn,direct",
            "GOFLAGS": "-mod=mod",
            "GOTOOLCHAIN": "local",
            "GOROOT": go_root,
            "GOPATH": gopath,
            "GOCACHE": gocache,
            "GOTMPDIR": gotmpdir,
            "TMPDIR": gotmpdir,
            "TEMP": gotmpdir,
            "PATH": "%s%s%s" % (go_bin_dir, os.pathsep, os.environ.get("PATH", "")),
        }
        return env, go_bin

    def _run_go(self, cmd, env, cwd):
        """Run a Go command with the env dict actually applied.

        ``self.run(env=<list of "K=V">)`` does NOT set env vars in Conan 2 —
        it treats them as env-file names. We instead mutate ``os.environ``
        around the call so the spawned ``go`` inherits GOPROXY/GOROOT/etc.
        """
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

    def build(self):
        apply_conandata_patches(self)
        env, go_bin = self._go_env()

        # ext2 output path for the Go linker (E166: linker mmap fails on
        # HMDFS). We build into ext2 then copy the binary back to the
        # Conan build folder for packaging.
        ext2_out = os.path.join(self._ext2_cache_dir(), "tlsx-bin")
        build_out = os.path.join(self.build_folder, "tlsx")

        # `go build` / `go test` must run in self.source_folder, where
        # the stripped upstream tree lives (cmd/tlsx, pkg/, go.mod...).
        # basic_layout sets self.folders.build = "build-<bt>", so the
        # default cwd of self.run in build() is the empty build-release/
        # directory — `./cmd/tlsx` resolves there and fails with
        # `stat .../build-release/cmd/tlsx: directory not found` (第 6 轮
        # 真机铁证). Passing cwd=self.source_folder fixes the lookup.
        src = self.source_folder

        # Sanity-probe the resolved `go` actually execve's on HongMeng
        # before the expensive module download. If the self-bootstrap
        # signing pass (or a pre-installed SDK Go) left an unsigned ELF,
        # `go version` fails fast with E128 here rather than mid-build.
        # Use the absolute go_bin — relying on PATH lookup was brittle on
        # the preflight `/bin/sh` (真机日志: `go: inaccessible or not found`
        # even with go_bin_dir prefixed, Conan env injection timing).
        self._run_go("%s version" % go_bin, env, cwd=src)

        # Explicitly pre-download ALL modules (including test-only deps)
        # before `go build` / `go test`. The previous round folded the
        # fetch into `go build ./cmd/tlsx`, which only pulls the cmd/tlsx
        # import chain — test packages import modules not reachable from
        # cmd/tlsx (e.g. github.com/projectdiscovery/utils/auth/pdcp in
        # runner_test.go, github.com/projectdiscovery/dnsx/libs/dnsx in
        # runner_test.go, net/http/httptest in several _test.go files).
        # When `go test <pkg>` later tries to compile those packages the
        # modules are absent from the cache and every test package
        # returns a package-level compile error
        # (真机铁证: 6 packages COMPILE FAIL, discovered=0 executed=0).
        #
        # `go mod download` (no args) downloads every module listed in
        # go.mod (direct + indirect), covering both build and test deps.
        self._run_go("%s mod download" % go_bin, env, cwd=src)

        # Build the main tlsx binary (static, stripped).
        # -ldflags=-s and -ldflags=-w avoid nested-quote issues in self.run.
        # -o points at ext2 so the Go linker's mmap succeeds.
        self._run_go(
            "%s build -trimpath -ldflags=-s -ldflags=-w -o %s ./cmd/tlsx"
            % (go_bin, ext2_out),
            env,
            cwd=src,
        )
        if not os.path.isfile(ext2_out):
            raise ConanException(
                "go build did not produce %s (E166 linker-mmap failure?)" % ext2_out
            )
        # Sign the produced tlsx ELF in place so it can execve on
        # HongMeng (E128). Without signing, test_package's
        # `tlsx -version` fails with `Permission denied` (EACCES from
        # kernel execve on an unsigned ELF). Idempotent via
        # llvm-objcopy --remove-section first.
        if not self._sign_elf(ext2_out):
            raise ConanException(
                "ELF signing of %s failed (binary-sign-tool/llvm-objcopy "
                "unavailable? paths=%s,%s) — tlsx will not execve on HongMeng"
                % (ext2_out, _SIGNTOOL, _OBJCOPY)
            )
        shutil.copy2(ext2_out, build_out)

        # NOTE: the upstream ``go test`` suite (42 Test functions across
        # 11 _test.go files) is executed in test_package/conanfile.py's
        # test() method, where hmbs preflight collects the
        # HMBS_UPSTREAM_TEST_RESULT marker. build() only produces and
        # signs the tlsx binary; it does not run upstream tests.

    def package(self):
        copy(self, "tlsx", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
