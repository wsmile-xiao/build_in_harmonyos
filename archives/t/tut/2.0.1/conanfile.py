#!/usr/bin/env python3
"""Conan recipe — tut 2.0.1 (Go, Mastodon TUI).

Upstream https://github.com/RasmusLindroth/tut, tag 2.0.1 (go 1.18 module,
CGO-free TUI for Mastodon). Build system is Go modules; the product is a
single statically linked `tut` binary (`go build .` at the module root).

Platform notes (all build-environment work, zero upstream source changes):
- E128 (Go binaries require ELF signing): every ELF execve'd on HongMeng
  must carry a `.codesign` section. This applies both to the produced tut
  binary and to the Go toolchain itself. We probe a signed SDK Go first and
  otherwise self-bootstrap a portable Go tarball and re-sign every toolchain
  ELF with binary-sign-tool (tlsx/nuclei/argo/kubo precedent).
- E077 (sign resets x bit): after binary-sign-tool signs an ELF we run
  chmod 0o755 to restore owner rwx (HMDFS preserves owner bits).
- E166 (Go linker mmap fails on HMDFS): GOCACHE/GOTMPDIR and the linker -o
  output are routed to the ext2 partition /data/storage/el2/base/*, then the
  binary is copied back to the Conan build folder.
- Upstream has zero tests (96 files in the 2.0.1 tarball, no *_test.go, no
  Test funcs). build() only produces the binary; test_package runs the
  consumer smoke test and emits the no_tests upstream marker.
"""
import hashlib
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

_SDK_GO_CANDIDATES = [
    "/storage/Users/currentUser/sdk/go1.26.3/bin/go",
    "/storage/Users/currentUser/sdk/go1.26.3/go/bin/go",
    "/storage/Users/currentUser/sdk/go1.25.7/bin/go",
    "/storage/Users/currentUser/sdk/go1.25.7/go/bin/go",
    "/storage/Users/currentUser/sdk/go/bin/go",
]

_GO_TARBALL_URLS = [
    "https://golang.google.cn/dl/go1.24.0.linux-arm64.tar.gz",
    "https://dl.google.com/go/go1.24.0.linux-arm64.tar.gz",
]
_GO_TARBALL_SHA256 = "c3fa6d16ffa261091a5617145553c71d21435ce547e44cc6dfb7470865527cc7"
_GO_VERSION = "1.24.0"

_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
_SIGNTOOL = "/data/service/hnp/bin/binary-sign-tool"

_EXT2_CACHE_CANDIDATES = [
    "/data/storage/el2/base/haps/entry/files",
    "/data/storage/el2/base/cache",
]


class TutConan(ConanFile):
    name = "tut"
    version = "2.0.1"
    description = "TUI for Mastodon with vim inspired keys"
    license = "MIT"
    homepage = "https://github.com/RasmusLindroth/tut"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tut requires Linux or OHOS, got %s" % self.settings.os)
        if str(self.settings.arch) not in ("armv8", "arm64", "aarch64"):
            raise ConanInvalidConfiguration(
                "tut 2.0.1 recipe targets aarch64, got %s" % self.settings.arch)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ext2_cache_dir(self):
        for base in _EXT2_CACHE_CANDIDATES:
            candidate = os.path.join(base, "tut-2.0.1")
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
            "No writable ext2 cache dir found in %s; falling back to %s "
            "(E166 linker-mmap failure may follow)"
            % (_EXT2_CACHE_CANDIDATES, fallback))
        return fallback

    def _resolve_sign_tool(self, primary, prog):
        # Probe the absolute HNP path first, then PATH. Returning the
        # resolved path lets callers emit an actionable diagnostic instead
        # of a bare shell "Error 127" from self.run().
        if primary and os.path.isfile(primary) and os.access(primary, os.X_OK):
            return primary
        found = shutil.which(prog)
        if found and os.access(found, os.X_OK):
            self.output.info(
                "Sign tool %s not executable at %s; using PATH fallback %s"
                % (prog, primary, found))
            return found
        return primary

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf(self, target):
        if not os.path.isfile(target):
            return False
        # The Go tree may ship wrapper scripts alongside ELFs; only ELFs
        # need (and accept) objcopy/sign-tool. Skipping non-ELFs keeps one
        # stray script from failing the whole toolchain sign pass.
        if not self._is_elf(target):
            self.output.info("Skipping non-ELF %s (no signing needed)" % target)
            return True
        import subprocess
        objcopy = self._resolve_sign_tool(_OBJCOPY, "llvm-objcopy")
        signtool = self._resolve_sign_tool(_SIGNTOOL, "binary-sign-tool")
        if not (os.path.isfile(signtool) and os.access(signtool, os.X_OK)):
            self.output.warning(
                "binary-sign-tool not found/executable (tried %s and PATH); "
                "cannot sign %s (E128 will follow)" % (_SIGNTOOL, target))
            return False
        # Step 1: strip a stale .codesign section. binary-sign-tool refuses
        # to overwrite an existing section ("section already exists"), while
        # objcopy fails when there is nothing to strip (fresh tarball).
        # Either way this step must never abort the sign pass (old code used
        # self.run() which raises on non-zero exit, and a missing objcopy
        # surfaced only as opaque "Error 127").
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", target],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=30)
        except Exception as e:
            self.output.warning(
                "objcopy --remove-section on %s ignored: %s" % (target, e))
        # Step 2: self-sign to a temp file, then atomically move over the
        # original. In-place (-inFile X -outFile X) is unreliable per
        # knowledge/operations/packaging.md; tmp+move is the id3v2/sign_elf.py
        # precedent. Retry 3x (sign-tool flakiness documented in knowledge).
        tmp = target + ".signed.tmp"
        try:
            os.remove(tmp)
        except OSError:
            pass
        signed_ok = False
        last_err = ""
        for _ in range(3):
            try:
                r = subprocess.run(
                    [signtool, "sign", "-inFile", target,
                     "-outFile", tmp, "-selfSign", "1"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=60)
            except Exception as e:
                last_err = str(e)
                continue
            if r.returncode == 0 and os.path.isfile(tmp):
                try:
                    shutil.move(tmp, target)
                except OSError as e:
                    last_err = str(e)
                    continue
                signed_ok = True
                break
            err = ""
            try:
                err = (r.stderr or b"").decode("utf-8", "replace").strip()[-500:]
            except Exception:
                pass
            last_err = "rc=%s %s" % (r.returncode, err)
        if not signed_ok:
            try:
                os.remove(tmp)
            except OSError:
                pass
            self.output.warning(
                "ELF signing failed for %s: %s" % (target, last_err))
            return False
        # Step 3 (E077): signing resets mode bits; restore owner rwx.
        # HMDFS clamps group/other but preserves owner bits incl. x, and
        # ext2 honors chmod normally, so 0o755 always yields exec owner.
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
        return os.access(target, os.X_OK)

    def _sign_go_toolchain(self, boot_root):
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
            if self._sign_elf(t):
                signed += 1
            else:
                failed += 1
                self.output.warning(
                    "Failed to sign Go toolchain ELF %s (E128 may follow)" % t)
        self.output.info(
            "Signed %d Go toolchain ELFs (%d failed) under %s"
            % (signed, failed, boot_root))
        if failed:
            raise ConanException(
                "Go toolchain ELF signing failed for %d files under %s; "
                "binary-sign-tool/llvm-objcopy unavailable? paths=%s,%s"
                % (failed, boot_root, _OBJCOPY, _SIGNTOOL))

    def _bootstrap_go(self):
        ext2 = self._ext2_cache_dir()
        boot_root = os.path.join(ext2, "go-bootstrap", "go%s" % _GO_VERSION)
        go_bin = os.path.join(boot_root, "bin", "go")
        marker = os.path.join(boot_root, ".hmbs-signed-ok")
        if os.path.isfile(marker) and os.path.isfile(go_bin):
            self.output.info("Reusing cached signed Go bootstrap: %s" % go_bin)
            return go_bin
        import urllib.request
        import ssl
        bootstrap_parent = os.path.dirname(boot_root)
        os.makedirs(bootstrap_parent, exist_ok=True)
        shipped_root = os.path.join(bootstrap_parent, "go")
        if os.path.isdir(shipped_root):
            shutil.rmtree(shipped_root, ignore_errors=True)
        if os.path.isdir(boot_root):
            shutil.rmtree(boot_root, ignore_errors=True)
        tarball_path = os.path.join(bootstrap_parent, "go%s.tar.gz" % _GO_VERSION)
        last_err = None
        url = _GO_TARBALL_URLS[0]
        for url in _GO_TARBALL_URLS:
            try:
                self.output.info("Downloading Go %s from %s" % (_GO_VERSION, url))
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
                % (_GO_VERSION, last_err, _GO_TARBALL_URLS))
        actual_sha = hashlib.sha256(open(tarball_path, "rb").read()).hexdigest()
        if actual_sha != _GO_TARBALL_SHA256:
            raise ConanException(
                "Go tarball SHA-256 mismatch: expected %s, got %s (URL %s)"
                % (_GO_TARBALL_SHA256, actual_sha, url))
        self.output.info("Go tarball SHA-256 verified: %s" % actual_sha)
        with tarfile.open(tarball_path, "r:gz") as tf:
            tf.extractall(bootstrap_parent)
        try:
            os.remove(tarball_path)
        except OSError:
            pass
        if not os.path.isdir(shipped_root):
            raise ConanException(
                "Go tarball extracted but %s missing" % shipped_root)
        os.rename(shipped_root, boot_root)
        self._sign_go_toolchain(boot_root)
        with open(marker, "w") as f:
            f.write("signed go %s\n" % _GO_VERSION)
        self.output.info("Self-bootstrapped Go ready: %s" % go_bin)
        return go_bin

    def _ensure_go(self):
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
                    "SDK Go found at %s but not executable; continuing probe" % cand)
        self.output.info(
            "No signed SDK Go on PATH or under ~/sdk/; self-bootstrapping Go %s "
            "and re-signing toolchain ELFs (E128+E077 workaround)" % _GO_VERSION)
        return self._bootstrap_go()

    def _go_env(self):
        go_bin = self._ensure_go()
        go_bin_dir = os.path.dirname(go_bin)
        go_root = os.path.dirname(go_bin_dir)
        ext2_cache = self._ext2_cache_dir()
        gopath = os.path.join(ext2_cache, "gopath")
        gocache = os.path.join(ext2_cache, "go-cache")
        gotmpdir = os.path.join(ext2_cache, "go-tmp")
        os.makedirs(gopath, exist_ok=True)
        os.makedirs(gocache, exist_ok=True)
        os.makedirs(gotmpdir, exist_ok=True)
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
        env, go_bin = self._go_env()
        ext2_out = os.path.join(self._ext2_cache_dir(), "tut-bin")
        build_out = os.path.join(self.build_folder, "tut")
        src = self.source_folder
        self._run_go("%s version" % go_bin, env, cwd=src)
        self._run_go("%s mod download" % go_bin, env, cwd=src)
        self._run_go(
            "%s build -trimpath -ldflags=-s -ldflags=-w -o %s ."
            % (go_bin, ext2_out),
            env,
            cwd=src)
        if not os.path.isfile(ext2_out):
            raise ConanException(
                "go build did not produce %s (E166 linker-mmap failure?)" % ext2_out)
        if not self._sign_elf(ext2_out):
            raise ConanException(
                "ELF signing of %s failed (binary-sign-tool/llvm-objcopy "
                "unavailable? paths=%s,%s)"
                % (ext2_out, _SIGNTOOL, _OBJCOPY))
        shutil.copy2(ext2_out, build_out)

    def package(self):
        copy(self, "tut", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
