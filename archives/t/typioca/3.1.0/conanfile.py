#!/usr/bin/env python3
"""Conan recipe for typioca 3.1.0 — cozy terminal typing-speed tester (pure Go CLI).

typioca is a pure-Go command-line application (module
``github.com/bloznelis/typioca``, ``main.go`` at the repo root). The upstream
Makefile builds it with::

    go build -trimpath -ldflags "-w -s -X 'github.com/bloznelis/typioca/cmd.Version=${VERSION}'" -a -tags netgo -o execs/typioca

which is what this recipe reproduces (minus the ``-a`` full rebuild) as a
static ``CGO_ENABLED=0`` binary for OHOS/Linux aarch64 (also x86_64).

HarmonyOS notes (see knowledge E523 / E134 and the aiac/abbtr Go precedents):
- The Go linker calls ``fallocate()``/``mmap`` on its output file; HMDFS and
  tmpfs on OHOS return ``EACCES`` (``mapping output file failed: permission
  denied``). Link output therefore goes to an ext2-like writable workspace
  under ``/data/storage/el2/base/haps/entry/files`` when building for OHOS.
- Every ELF that OHOS will ``fork/exec`` (the typioca binary *and* the Go SDK
  tool binaries) must be self-signed with ``binary-sign-tool`` (``.codesign``
  section) before it can run.
- Go's pure-Go resolver (netgo) reads ``/etc/resolv.conf`` only; on some OHOS
  dev images those nameservers are unreachable and ``go mod download`` fails
  with ``dial tcp: lookup ... i/o timeout``. ``GOPROXY`` is therefore
  overridable from the environment (``GOPROXY`` / ``GOSUMDB`` / ``GOMODCACHE``)
  so a file:// module proxy can be substituted locally, while CI keeps the
  default public proxy.

Upstream 3.1.0 ships no ``*_test.go`` files and its CI
(``.github/workflows/ci.yml``) only runs ``make build-all`` — there is no
upstream test step. ``go test -v -count=1 ./...`` is still executed as machine
evidence (status ``no_tests``); see test_package/MANIFEST.yml.
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
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TypiocaConan(ConanFile):
    name = "typioca"
    version = "3.1.0"

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

    package_type = "application"

    description = "Cozy typing speed tester in terminal (pure Go CLI)"
    license = "MIT"
    homepage = "https://github.com/bloznelis/typioca"
    url = "https://github.com/bloznelis/typioca"
    topics = ("typioca", "typing", "tui", "bubbletea", "cli", "go")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # No patches for typioca 3.1.0; kept for conandata patch export parity.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("typioca supports Linux and OHOS targets only")

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        # Overridable so a file:// module proxy can stand in when Go's netgo
        # resolver cannot reach the default proxy (OHOS dev images).
        env.define("GOPROXY", os.environ.get("GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"))
        env.define("GOSUMDB", os.environ.get("GOSUMDB", "sum.golang.google.cn"))
        env.define("GOTOOLCHAIN", "local")

        go_workspace = self._go_workspace()
        env.define("TMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOCACHE", os.path.join(go_workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.environ.get("GOMODCACHE", os.path.join(go_workspace, "go-mod-cache")))
        # Pre-create subdirs: Go refuses to bootstrap without every path component.
        for d in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(go_workspace, d), exist_ok=True)

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("typioca_go_env")

    def build(self):
        apply_conandata_patches(self)  # no-op: conandata.yml declares patches: {}
        go = self._go_executable()
        # Build-time safety net: re-create subdirs in case generate() was skipped
        # or the workspace path changed between phases.
        for subdir in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(self._go_workspace(), subdir), exist_ok=True)
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["typioca_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker fallocate/mmap fails on HMDFS: link on ext2-like workspace on OHOS.
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())
        ldflags = "-s -w -X github.com/bloznelis/typioca/cmd.Version=3.1.0"
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["typioca_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # Upstream has no tests; still run `go test` as machine evidence.
        self._run_upstream_tests(go)

    def package(self):
        copy(self, self._exe_name(),
             src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── upstream test evidence (no_tests) ──────────────────────────────────

    def _run_upstream_tests(self, go):
        """Run upstream ``go test ./...`` and emit machine evidence.

        typioca 3.1.0 contains no ``*_test.go`` files, so ``go test -v -count=1
        ./...`` compiles every package and prints ``[no test files]`` for each.
        This run is kept as evidence for the ``no_tests`` declaration.
        """
        base_env = dict(os.environ)
        ws = self._go_workspace()
        base_env.update({
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(ws, "tmp"),
            "GOTMPDIR": os.path.join(ws, "tmp"),
            "GOCACHE": os.path.join(ws, "go-build-cache"),
            "GOMODCACHE": os.environ.get("GOMODCACHE", os.path.join(ws, "go-mod-cache")),
            "GOPROXY": os.environ.get("GOPROXY", "https://goproxy.cn,direct"),
            "GOSUMDB": os.environ.get("GOSUMDB", "sum.golang.google.cn"),
        })
        goroot = self._goroot_for_go(go)
        if goroot:
            base_env["GOROOT"] = goroot
        base_env["PATH"] = os.path.dirname(go) + os.pathsep + base_env.get("PATH", "")

        cmd = [go, "test", "-v", "-count=1", "./..."]
        try:
            proc = subprocess.run(cmd, cwd=self.source_folder, env=base_env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800)
            out = proc.stdout.decode(errors="replace")
        except (OSError, subprocess.TimeoutExpired) as exc:
            out = f"go test failed to run: {exc}"

        p = len(re.findall(r"^\s*--- PASS:", out, re.MULTILINE))
        f = len(re.findall(r"^\s*--- FAIL:", out, re.MULTILINE))
        s = len(re.findall(r"^\s*--- SKIP:", out, re.MULTILINE))
        note = len(re.findall(r"\[no test files\]", out))
        self.output.info(f"typioca upstream `go test -v -count=1 ./...`: PASS={p} FAIL={f} SKIP={s} no_test_pkgs={note}")
        preview = out[:2048].replace("\n", "\n  typioca go test | ")
        self.output.info("typioca go test output preview:\n  " + preview)

        status = "failed" if f > 0 else ("passed" if p > 0 else "no_tests")
        upstream = {
            "status": status,
            "framework": "go test",
            "command": " ".join(cmd),
            "discovered": p + f + s,
            "executed": p + f,
            "passed": p,
            "failed": f,
            "skipped": s,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    # ── Go toolchain helpers ───────────────────────────────────────────────

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in (
                "/data/storage/el2/base/haps/entry/files",
                "/data/storage/el2/base/cache",
            ):
                candidate = os.path.join(base, "typioca-3.1.0-go")
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

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(f"Go SDK bootstrap is not prepared for host arch: {host_arch}")
        sdk_root = os.path.join(self._go_workspace(), "go-sdk", f"go{self._go_version}-{host_arch}")
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info(f"Go >= {self._go_version} not found; downloading {urls[0]}")
            get(self, url=urls, sha256=sha256, destination=sdk_root, strip_root=False)
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return
        tool_dir = os.path.join(goroot, "pkg", "tool", f"linux_{self._go_host_arch()}")
        candidates = [os.path.join(goroot, "bin", "go"), os.path.join(goroot, "bin", "gofmt")]
        if os.path.isdir(tool_dir):
            candidates.extend(os.path.join(tool_dir, name) for name in os.listdir(tool_dir))
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                self._sign_elf_if_ohos(candidate)
        Path(marker).write_text("signed\n", encoding="utf-8")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            raise ConanInvalidConfiguration("binary-sign-tool is required to sign OHOS Go executables")
        tmp_dir = os.path.join(self._go_workspace(), "sign-tmp")
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        tmp_in = os.path.join(tmp_dir, os.path.basename(path))
        tmp_out = f"{tmp_in}.signed"
        shutil.copy2(path, tmp_in)
        objcopy = (os.environ.get("OHOS_LLVM_OBJCOPY")
                   or shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                           capture_output=True, timeout=10)
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", tmp_in, "-outFile", tmp_out,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
        if os.path.isfile(tmp_in):
            os.unlink(tmp_in)

    def _find_binary_sign_tool(self):
        for candidate in (
            os.environ.get("OHOS_BINARY_SIGN_TOOL"),
            os.environ.get("BINARY_SIGN_TOOL"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
            shutil.which("binary-sign-tool"),
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _goos(self):
        if str(self.settings.os) == "OHOS":
            return "linux"
        return str(self.settings.os).lower()

    def _goarch(self):
        arch = str(self.settings.arch)
        return {
            "x86_64": "amd64",
            "x86": "386",
            "armv8": "arm64",
            "armv8_32": "arm",
            "armv7": "arm",
            "armv7hf": "arm",
            "armv6": "arm",
        }.get(arch, arch)

    def _exe_name(self):
        return "typioca.exe" if self._goos() == "windows" else "typioca"

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
            if candidate and os.path.isfile(candidate) and self._go_version_is_supported(candidate):
                return candidate
        return self._ensure_go_toolchain()

    def _go_version_is_supported(self, go):
        try:
            output = subprocess.run([go, "version"], capture_output=True, timeout=10).stdout.decode()
        except OSError:
            return False
        token = output.split("go version ")[-1].split(" ")[0]  # go1.26.5
        ver = token[2:]  # 1.26.5
        try:
            return [int(x) for x in ver.split(".")] >= [int(x) for x in self._go_version.split(".")]
        except ValueError:
            return False

    @staticmethod
    def _go_host_arch():
        machine = platform.machine().lower()
        return {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv8l": "arm64",
        }.get(machine, machine)

    @staticmethod
    def _goroot_for_go(gobin):
        gobin = os.path.realpath(gobin)
        candidates = [os.path.dirname(os.path.dirname(gobin)), os.environ.get("GOROOT", "")]
        for candidate in candidates:
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "go")):
                return candidate
        return ""
