#!/usr/bin/env python3
"""Conan recipe — codex-probe 1.0.3 (pure-Go CLI, JamesChan21/codex-probe).

codex-probe is a single-binary Go CLI for Codex credential workflows
(OAuth PKCE login / in-place renew / quota status / API smoke test /
Supabase AES-256-GCM sync / CSV export / proxy detection). It is pure Go:
the module has no ``import "C"`` and no cgo directives, so it is built with
``CGO_ENABLED=0`` and links to a fully static aarch64 executable.

Upstream build entry (README "Build from source"):

    go build -o codex-probe ./cmd/codex-probe/

Recipe form:

    CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local \
    go build -trimpath -ldflags "-s -w" -o <out> ./cmd/codex-probe

HarmonyOS platform facts verified on device (2026-09-18):

* E051/E166 (Go linker mmap on HMDFS): the linker mmaps its output file, which
  fails on HMDFS/tmpfs with "mapping output file failed: permission denied".
  The whole Go workspace (build cache, module cache, TMPDIR and link output)
  therefore lives on the ext2-like tmpfs under /data/storage/el2.
* E128/E077 (OHOS execve needs a code signature): an UNSIGNED ELF is refused
  with "Permission denied" (rc 126) on this platform, while the same file after
  ``binary-sign-tool sign -selfSign 1`` executes. Every Go SDK tool ELF and the
  produced binary are signed. Measured on device: unsigned -> rc 126,
  signed -> rc 0.
* Signature detection must be done on the real ELF section name. A raw byte
  search for b".codesign" FALSE-POSITIVES on Go binaries (the Go runtime embeds
  the literal "codesign" for macOS tooling), which silently skipped signing and
  produced the rc 126 failure above. This recipe queries `llvm-readelf -S` and
  matches the `.codesign` section header instead.
* Upstream 1.0.3 ships no test suite: `find . -name '*_test.go'` returns 0 files
  and .github/workflows/release.yml is a GoReleaser build-only job with no test
  step. `go build ./...` is used as machine evidence in build() and the
  ``no_tests`` HMBS marker is emitted from test_package (MANIFEST.yml
  upstream_test_in_build: false), aligned with the merged aiac/5.3.0 recipe.
"""
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class CodexProbeConan(ConanFile):
    name = "codex-probe"
    version = "1.0.3"

    package_type = "application"

    description = ("Codex credential & diagnostics CLI — token login, renew, "
                   "quota status, API smoke test, encrypted Supabase sync, CSV export")
    # Upstream README declares "## License / MIT" but the repository ships no
    # LICENSE file at tag v1.0.3, so no license file is packaged (recorded in
    # manifest.yaml/notes.md).
    license = "MIT"
    homepage = "https://github.com/JamesChan21/codex-probe"
    url = "https://github.com/JamesChan21/codex-probe"
    topics = ("codex", "credential", "cli", "oauth", "quota", "go", "harmonyos")

    # 顺序与 .gitcode/code-style.md §2 的规范示例及 archives/a/aiac/5.3.0 一致。
    settings = "os", "compiler", "build_type", "arch"

    # Go SDK used to build. 1.26.5 satisfies the module's `go 1.22` directive and
    # matches the worker/merged-recipe toolchain (archives/a/aiac/5.3.0).
    _go_version = "1.26.5"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.26.5.linux-arm64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.26.5.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.26.5.linux-arm64.tar.gz",
            ],
            "fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49",
        ),
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.26.5.linux-amd64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.26.5.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.26.5.linux-amd64.tar.gz",
            ],
            "5c2c3b16caefa1d968a94c1daca04a7ca301a496d9b086e17ad77bb81393f053",
        ),
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "codex-probe is prepared for Linux/OHOS targets only")

    # ── environment ────────────────────────────────────────────────────
    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOPROXY", os.environ.get(
            "GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"))
        env.define("GOSUMDB", os.environ.get("GOSUMDB", "sum.golang.google.cn"))
        env.define("GOTOOLCHAIN", "local")

        ws = self._go_workspace()
        for sub in ("tmp", "go-build-cache", "go-mod-cache", "link-out", "sign-tmp"):
            os.makedirs(os.path.join(ws, sub), exist_ok=True)
        env.define("TMPDIR", os.path.join(ws, "tmp"))
        env.define("GOTMPDIR", os.path.join(ws, "tmp"))
        env.define("GOCACHE", os.path.join(ws, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(ws, "go-mod-cache"))

        go = self._go_executable()
        goroot = self._goroot_for_go(go)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(go))
        env.vars(self).save_script("codex_probe_go_env")

    # ── build ──────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)   # no patches for 1.0.3 (conandata: patches: {})
        go = self._go_executable()
        ws = self._go_workspace()
        for sub in ("tmp", "go-build-cache", "go-mod-cache", "link-out"):
            os.makedirs(os.path.join(ws, sub), exist_ok=True)

        self.run(f'"{go}" mod download', cwd=self.source_folder,
                 env=["codex_probe_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Link on the ext2-like tmpfs on OHOS (E051/E166: Go linker mmap on HMDFS).
        if str(self.settings.os) == "OHOS":
            link_dir = os.path.join(ws, "link-out")
        else:
            link_dir = out_dir
        os.makedirs(link_dir, exist_ok=True)
        linked = os.path.join(link_dir, "codex-probe")
        final = os.path.join(out_dir, "codex-probe")

        self.run(
            f'"{go}" build -trimpath -ldflags "-s -w" -o "{linked}" ./cmd/codex-probe',
            cwd=self.source_folder, env=["codex_probe_go_env"],
        )
        if not os.path.isfile(linked):
            raise ConanInvalidConfiguration(
                "go build produced no binary at %s" % linked)

        if os.path.abspath(linked) != os.path.abspath(final):
            shutil.copy2(linked, final)
        # E128/E077: the packaged binary (and, on the same device, the ext2
        # copy the test_package executes) must be self-signed before execve.
        if not self._sign_elf_if_ohos(final):
            raise ConanInvalidConfiguration(
                "ELF signing of %s failed (binary-sign-tool unavailable?)" % final)
        if os.path.abspath(linked) != os.path.abspath(final):
            self._sign_elf_if_ohos(linked)

        self._run_upstream_tests(go)

    def package(self):
        copy(self, "codex-probe", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── upstream test evidence (audit trail; marker emitted by test_package) ──
    def _run_upstream_tests(self, go):
        """Record the upstream test inventory as machine evidence.

        codex-probe 1.0.3 has no *_test.go files, so `go test` reports
        "[no test files]" for every package. This run is kept **only as an
        audit trail** in the conan create log — it is deliberately NOT a build
        gate, because there is nothing to gate on: the module ships 0 tests and
        MANIFEST.yml declares upstream_test_in_build: false (the authoritative
        HMBS_UPSTREAM_TEST_RESULT marker with status "no_tests" is printed from
        test_package/conanfile.py, which is where the HMBS evidence gate reads
        it). A FAIL is surfaced loudly through output.warning() so it can never
        be silent; should upstream ever add a test suite, this method must be
        revisited and promoted to a hard failure before relying on it.
        """
        env = dict(os.environ)
        ws = self._go_workspace()
        env.update({
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(ws, "tmp"),
            "GOTMPDIR": os.path.join(ws, "tmp"),
            "GOCACHE": os.path.join(ws, "go-build-cache"),
            "GOMODCACHE": os.path.join(ws, "go-mod-cache"),
        })
        goroot = self._goroot_for_go(go)
        if goroot:
            env["GOROOT"] = goroot
        env["PATH"] = os.path.dirname(go) + os.pathsep + env.get("PATH", "")

        cmd = [go, "test", "-v", "-count=1", "./..."]
        try:
            proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=1800)
            out = proc.stdout.decode(errors="replace")
        except (OSError, subprocess.TimeoutExpired) as exc:
            out = "go test failed to run: %s" % exc

        passed = len(re.findall(r"^\s*--- PASS:", out, re.MULTILINE))
        failed = len(re.findall(r"^\s*--- FAIL:", out, re.MULTILINE))
        notests = len(re.findall(r"\[no test files\]", out))
        self.output.info("codex-probe upstream `go test -v -count=1 ./...`: "
                         "PASS=%d FAIL=%d no_test_files=%d" % (passed, failed, notests))
        self.output.info("codex-probe go test output preview:\n  " +
                         out[:2048].replace("\n", "\n  codex-probe go test | "))
        if failed:
            self.output.warning("upstream go test reported %d failing test(s)" % failed)

    # ── Go toolchain resolution / bootstrap ────────────────────────────
    def _go_workspace(self):
        """Writable ext2-like workspace (never the HMDFS archive tree)."""
        if str(self.settings.os) == "OHOS":
            for base in ("/data/storage/el2/base/haps/entry/files",
                         "/data/storage/el2/base/cache"):
                candidate = os.path.join(base, "codex-probe-1.0.3-go")
                try:
                    os.makedirs(candidate, exist_ok=True)
                    probe = os.path.join(candidate, ".probe")
                    Path(probe).write_text("ok\n", encoding="utf-8")
                    os.remove(probe)
                    return candidate
                except OSError:
                    continue
        root = os.path.join(self.build_folder, ".go-work")
        os.makedirs(root, exist_ok=True)
        return root

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser("~/sdk/go1.26.5/bin/go"),
            os.path.expanduser("~/.goenv/versions/1.26.5/bin/go"),
        ])
        found = shutil.which("go")
        if found:
            candidates.append(found)
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) \
                    and self._go_version_is_supported(candidate):
                self.output.info("using Go from %s" % candidate)
                return candidate
        return self._ensure_go_toolchain()

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(
                "Go SDK bootstrap is not prepared for host arch: %s" % host_arch)
        sdk_parent = os.path.join(self._go_workspace(), "go-sdk",
                                  "go%s-%s" % (self._go_version, host_arch))
        goroot = os.path.join(sdk_parent, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info("Go %s not found; downloading %s"
                             % (self._go_version, urls[0]))
            get(self, url=urls, sha256=sha256, destination=sdk_parent,
                strip_root=False)
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _go_version_is_supported(self, go):
        try:
            out = subprocess.run([go, "version"], capture_output=True,
                                 timeout=10).stdout.decode(errors="replace")
        except OSError:
            return False
        m = re.search(r"go version go(\d+\.\d+(?:\.\d+)?)", out)
        if not m:
            return False
        try:
            return ([int(x) for x in m.group(1).split(".")] >=
                    [int(x) for x in self._go_version.split(".")])
        except ValueError:
            return False

    def _go_host_arch(self):
        machine = platform.machine().lower()
        return {
            "x86_64": "amd64", "amd64": "amd64",
            "aarch64": "arm64", "arm64": "arm64", "armv8l": "arm64",
        }.get(machine, machine)

    def _goroot_for_go(self, gobin):
        gobin = os.path.realpath(gobin)
        for candidate in (os.path.dirname(os.path.dirname(gobin)),
                          os.environ.get("GOROOT", "")):
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "go")):
                return candidate
        return ""

    def _goos(self):
        return "linux" if str(self.settings.os) == "OHOS" else str(self.settings.os).lower()

    def _goarch(self):
        return {
            "x86_64": "amd64", "x86": "386",
            "armv8": "arm64", "armv8_32": "arm", "armv7": "arm",
            "armv7hf": "arm", "armv6": "arm",
        }.get(str(self.settings.arch), str(self.settings.arch))

    # ── ELF signing (E128/E077) ────────────────────────────────────────
    _OBJCOPY_CANDIDATES = ("/data/service/hnp/bin/llvm-objcopy",
                           "/storage/Users/currentUser/usr/local/bin/llvm-objcopy")
    _READELF_CANDIDATES = ("/data/service/hnp/bin/llvm-readelf",
                           "/storage/Users/currentUser/usr/local/bin/llvm-readelf")
    _SIGN_CANDIDATES = ("/data/service/hnp/bin/binary-sign-tool",
                        "/storage/Users/currentUser/usr/local/bin/binary-sign-tool")

    @staticmethod
    def _first_existing(candidates):
        """First existing path from an explicit candidate list, else PATH lookup."""
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        for cand in candidates:
            found = shutil.which(os.path.basename(cand))
            if found:
                return found
        return None

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _has_codesign_section(self, path):
        """True only if the ELF really carries a .codesign section.

        A raw b".codesign" byte search is NOT usable here: Go binaries embed
        the literal "codesign" string for macOS tooling, so the byte search
        false-positives and silently skips the signing step (observed on
        device as an unsigned Go SDK ELF failing with "Permission denied").
        """
        readelf = self._first_existing(self._READELF_CANDIDATES)
        if not readelf:
            return False
        try:
            out = subprocess.run([readelf, "-S", path], capture_output=True,
                                 text=True, timeout=30).stdout or ""
        except (OSError, subprocess.SubprocessError):
            return False
        return ".codesign" in out

    @staticmethod
    def _chmod_755(path):
        """Best-effort chmod of an ELF to 0755.

        chmod is NOT reliable on this platform: on /data/storage/el2 the call
        fails with PermissionError even for the file's own uid (the worker uid
        is not in the passwd db), and HMDFS ignores chmod for owner bits.
        Failure is therefore non-fatal — the file already carries its exec
        bits from tar extraction / from a previous signing pass, which is what
        actually matters for execve.
        """
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def _sign_elf_if_ohos(self, path):
        """Self-sign one ELF so OHOS will execve it. Returns True on success."""
        if str(self.settings.os) != "OHOS":
            return True
        if not self._is_elf(path):
            return True
        if self._has_codesign_section(path):
            self._chmod_755(path)
            return True

        objcopy = self._first_existing(self._OBJCOPY_CANDIDATES)
        signer = self._first_existing(self._SIGN_CANDIDATES)
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may refuse to exec %s" % path)
            return False
        if objcopy:
            subprocess.run([objcopy, "--remove-section", ".codesign", path],
                           capture_output=True, timeout=30)
        tmp_out = path + ".signed"
        try:
            subprocess.run([signer, "sign", "-inFile", path, "-outFile", tmp_out,
                            "-selfSign", "1"],
                           capture_output=True, timeout=120, check=True)
        except (OSError, subprocess.SubprocessError) as exc:
            self.output.warning("signing %s failed: %s" % (path, exc))
            try:
                os.remove(tmp_out)
            except OSError:
                pass
            return False
        if not os.path.getsize(tmp_out):
            os.remove(tmp_out)
            return False
        shutil.move(tmp_out, path)
        self._chmod_755(path)
        return True

    def _sign_go_sdk_if_ohos(self, goroot):
        """Sign every ELF of a freshly extracted Go SDK (idempotent)."""
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed-ok")
        if os.path.isfile(marker):
            return
        targets = []
        for sub in ("bin", os.path.join("pkg", "tool", "linux_%s"
                                        % self._go_host_arch())):
            d = os.path.join(goroot, sub)
            if os.path.isdir(d):
                targets.extend(os.path.join(d, n) for n in sorted(os.listdir(d)))
        signed = failed = 0
        for t in targets:
            if not os.path.isfile(t) or not self._is_elf(t):
                continue
            if self._sign_elf_if_ohos(t):
                signed += 1
            else:
                failed += 1
        self.output.info("Go SDK ELF signing: %d signed, %d failed" % (signed, failed))
        if failed:
            raise ConanInvalidConfiguration(
                "Go SDK ELF signing failed for %d file(s)" % failed)
        Path(marker).write_text("signed\n", encoding="utf-8")
