#!/usr/bin/env python3
"""Conan recipe for qrcp 0.11.6 — transfer files over Wi-Fi by scanning a QR code.

qrcp is a pure-Go command-line application (module ``github.com/claudiodangelis/qrcp``).
The command entry point is the repository root (``main.go`` -> ``cmd.Execute()``), so it
is built with a bare ``go build .`` (no ``./cmd`` target). Upstream (``.goreleaser.yml``)
builds with ``CGO_ENABLED=0`` and cross-compiles a static binary:

    CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
    go build -trimpath -ldflags "-s -w \
      -X github.com/claudiodangelis/qrcp/version.version=0.11.6 \
      -X github.com/claudiodangelis/qrcp/version.date=<date>" -o qrcp .

Upstream ships one test file, ``config/config_test.go`` (``TestNew``, a table-driven
test with 5 sub-cases), run by ``go test ./...`` in ``.github/workflows/main.yml``.

HarmonyOS notes:
- qrcp is cross-compiled with ``GOOS=linux``/``GOARCH=arm64``/``CGO_ENABLED=0`` into a
  static ELF, which the HarmonyOS (Linux-compatible) kernel can execute directly.
- The Go linker needs an ext2-like workspace on OHOS (HMDFS mmap restriction:
  ``mapping output file failed: permission denied``); the link output is written under
  ``/data/storage/el2/base/haps/entry/files`` when running on OHOS.
- Every executed ELF on OHOS (the qrcp binary and the Go SDK tool binaries themselves)
  must carry a ``.codesign`` section before it can be fork/exec'd, so both are
  self-signed with ``binary-sign-tool``.
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


class QrcpConan(ConanFile):
    name = "qrcp"
    version = "0.11.6"

    # Go toolchain bootstrapped into the (writable) workspace; no host dependency on a
    # system Go install. Pinned to the exact linux-<hostarch> SDK plus official sha256.
    _go_version = "1.23.8"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.23.8.linux-arm64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.23.8.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.23.8.linux-arm64.tar.gz",
            ],
            "9d6d938422724a954832d6f806d397cf85ccfde8c581c201673e50e634fdc992",
        ),
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.23.8.linux-amd64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.23.8.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.23.8.linux-amd64.tar.gz",
            ],
            "45b87381172a58d62c977f27c4683c8681ef36580abecd14fd124d24ca306d3f",
        ),
    }
    package_type = "application"

    description = "Transfer files over Wi-Fi from your computer to a mobile device by scanning a QR code (pure Go CLI)"
    license = "MIT"
    homepage = "https://github.com/claudiodangelis/qrcp"
    url = "https://github.com/claudiodangelis/qrcp"
    topics = ("qrcp", "qr-code", "file-transfer", "cli", "go")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # No patches for qrcp 0.11.6; kept for conandata patch export parity.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("qrcp supports Linux and OHOS targets only")

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOPROXY", os.environ.get("GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"))
        env.define("GOSUMDB", os.environ.get("GOSUMDB", "sum.golang.google.cn"))
        env.define("GOTOOLCHAIN", "local")

        go_workspace = self._go_workspace()
        env.define("TMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOCACHE", os.path.join(go_workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(go_workspace, "go-mod-cache"))
        # Pre-create subdirs: Go refuses to bootstrap without every path component.
        for d in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(go_workspace, d), exist_ok=True)

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("qrcp_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        # Build-time safety net in case generate() was skipped.
        for subdir in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(self._go_workspace(), subdir), exist_ok=True)
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["qrcp_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker mmap fails on HMDFS: link on an ext2-like workspace on OHOS.
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "qrcp")
        final_exe = os.path.join(out_dir, "qrcp")
        ldflags = (
            "-s -w "
            f"-X github.com/claudiodangelis/qrcp/version.version={self.version} "
            f"-X github.com/claudiodangelis/qrcp/version.date={self._build_date()}"
        )
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["qrcp_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # Run the upstream Go test suite (config/config_test.go) and emit machine
        # evidence (HMBS_UPSTREAM_TEST_RESULT) for the HMBS evidence gate.
        self._run_upstream_tests(go)

    def package(self):
        copy(self, "qrcp", os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── upstream tests ────────────────────────────────────────────────

    def _run_upstream_tests(self, go):
        """Run upstream ``go test -v -count=1 ./...`` and emit HMBS markers.

        qrcp 0.11.6 ships a single upstream test file ``config/config_test.go`` with
        ``TestNew`` (a table-driven test containing 5 sub-cases). ``go test -v`` reports
        one ``=== RUN   TestNew`` line plus one per sub-case; PASS/FAIL/SKIP are parsed
        from the ``--- PASS/FAIL/SKIP`` markers.
        """
        base_env = dict(os.environ)
        go_workspace = self._go_workspace()
        go_env_overrides = {
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(go_workspace, "tmp"),
            "GOTMPDIR": os.path.join(go_workspace, "tmp"),
            "GOCACHE": os.path.join(go_workspace, "go-build-cache"),
            "GOMODCACHE": os.path.join(go_workspace, "go-mod-cache"),
        }
        goroot = self._goroot_for_go(go)
        if goroot:
            go_env_overrides["GOROOT"] = goroot
        base_env.update(go_env_overrides)
        base_env["PATH"] = os.path.dirname(go) + os.pathsep + base_env.get("PATH", "")

        cmd = [go, "test", "-v", "-count=1"]
        if str(self.settings.os) == "OHOS":
            wrapper = self._write_test_exec_wrapper()
            if wrapper:
                # OHOS refuses to exec an unsigned ELF, so each compiled test
                # binary must be signed before Go forks it.
                cmd.append(f"-exec={wrapper}")
        cmd.append("./...")
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.source_folder,
                env=base_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=1800,
            )
            out = proc.stdout.decode(errors="replace")
        except (OSError, subprocess.TimeoutExpired) as exc:
            out = f"go test failed to run: {exc}"

        top_passed = re.findall(r"^--- PASS:\s+(\S+)", out, re.MULTILINE)
        top_failed = re.findall(r"^--- FAIL:\s+(\S+)", out, re.MULTILINE)
        top_skipped = re.findall(r"^--- SKIP:\s+(\S+)", out, re.MULTILINE)
        sub_passed = re.findall(r"^\s+--- PASS:\s+(\S+)", out, re.MULTILINE)
        sub_failed = re.findall(r"^\s+--- FAIL:\s+(\S+)", out, re.MULTILINE)
        sub_skipped = re.findall(r"^\s+--- SKIP:\s+(\S+)", out, re.MULTILINE)
        ran = re.findall(r"^=== RUN\s+(\S+)", out, re.MULTILINE)

        p = len(top_passed) + len(sub_passed)
        f = len(top_failed) + len(sub_failed)
        s = len(top_skipped) + len(sub_skipped)

        self.output.info(f"qrcp upstream `go test -v -count=1 ./...`: PASS={p} FAIL={f} SKIP={s}")
        self.output.info("qrcp upstream test cases: " + ", ".join(ran))
        preview = out[:4096].replace("\n", "\n  qrcp go test | ")
        self.output.info("qrcp go test output preview:\n  " + preview)

        status = "failed" if f > 0 else ("passed" if p > 0 else "no_tests")
        upstream = {
            "status": status,
            "framework": "go test",
            "command": " ".join(cmd),
            "discovered": len(ran),
            "executed": p + f,
            "passed": p,
            "failed": f,
            "skipped": s,
            "cases": ran,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def _write_test_exec_wrapper(self):
        """Return a ``<sh> <script>`` command for ``go test -exec`` that signs the
        compiled test binary before executing it.

        OHOS refuses to fork/exec an unsigned ELF ("permission denied"), so the
        test binary Go compiles into a temp dir is signed in place here.
        """
        signer = self._find_binary_sign_tool()
        if not signer:
            return ""
        objcopy = (
            os.environ.get("OHOS_LLVM_OBJCOPY")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        mv = shutil.which("mv") or "/bin/mv"
        chmod = shutil.which("chmod") or "/bin/chmod"
        sh = shutil.which("sh") or "/bin/sh"
        script = os.path.join(self._go_workspace(), "sign-test-exec.sh")
        Path(script).write_text(
            "#!/bin/sh\n"
            "bin=\"$1\"; shift\n"
            f"\"{objcopy}\" --remove-section .codesign \"$bin\" 2>/dev/null || true\n"
            f"\"{signer}\" sign -selfSign 1 -inFile \"$bin\" -outFile \"$bin.signed\" "
            "-signAlg SHA256withECDSA >/dev/null 2>&1 || true\n"
            "if [ -f \"$bin.signed\" ]; then\n"
            f"    \"{mv}\" -f \"$bin.signed\" \"$bin\"\n"
            "fi\n"
            f"\"{chmod}\" 755 \"$bin\" 2>/dev/null || true\n"
            "exec \"$bin\" \"$@\"\n",
            encoding="utf-8",
        )
        return f"{sh} {script}"

    # ── Go toolchain helpers (aligned with aiac / abbtr Go recipes) ────

    def _build_date(self):
        # Deterministic build stamp (keeps `conan create` reproducible for verification).
        return "2026-09-29"

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in (
                "/data/storage/el2/base/haps/entry/files",
                "/data/storage/el2/base/cache",
            ):
                candidate = os.path.join(base, "qrcp-0.11.6-go")
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
        candidates = [
            os.path.join(goroot, "bin", "go"),
            os.path.join(goroot, "bin", "gofmt"),
        ]
        if os.path.isdir(tool_dir):
            candidates.extend(os.path.join(tool_dir, filename) for filename in os.listdir(tool_dir))

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
            self.output.warning("binary-sign-tool not found; OHOS may reject unsigned executable: %s" % path)
            return
        tmp_dir = os.path.join(self._go_workspace(), "sign-tmp")
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        tmp_in = os.path.join(tmp_dir, os.path.basename(path))
        tmp_out = f"{tmp_in}.signed"
        shutil.copy2(path, tmp_in)
        objcopy = (
            os.environ.get("OHOS_LLVM_OBJCOPY")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in], capture_output=True, timeout=10)
        subprocess.check_call([
            signer,
            "sign",
            "-selfSign",
            "1",
            "-inFile",
            tmp_in,
            "-outFile",
            tmp_out,
            "-signAlg",
            "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
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

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser("~/sdk/go1.23.8/bin/go"),
            os.path.expanduser("~/.goenv/versions/1.23.8/bin/go"),
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
        m = output.split("go version ")[-1].split(" ")[0]  # go1.23.8
        ver = m[2:]
        try:
            return [int(x) for x in ver.split(".")] >= [int(x) for x in self._go_version.split(".")]
        except ValueError:
            return False

    def _go_host_arch(self):
        machine = platform.machine().lower()
        return {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv8l": "arm64",
        }.get(machine, machine)

    def _goroot_for_go(self, gobin):
        gobin = os.path.realpath(gobin)
        candidates = [
            os.path.dirname(os.path.dirname(gobin)),
            os.environ.get("GOROOT", ""),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "go")):
                return candidate
        return ""
