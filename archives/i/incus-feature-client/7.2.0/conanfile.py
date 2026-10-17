#!/usr/bin/env python3
"""Conan recipe for incus-feature-client 7.2.0 — the Incus CLI client (`/usr/bin/incus`).

`incus-feature-client` is the Alpine binary sub-package of the upstream ``incus-feature``
source package (``community/incus-feature/APKBUILD``): its ``client()`` function splits out
a single binary, ``/usr/bin/incus`` — the Incus command-line client.  Upstream is
https://github.com/lxc/incus tag ``v7.2.0`` (Go module ``github.com/lxc/incus/v7``).

The client is 100% pure Go: ``cmd/incus``'s import closure contains no ``import "C"`` and
no third-party native library; ``internal/i18n`` ships a ``!cgo`` fallback and the cgo-only
files (``shared/idmap``, ``internal/netutils``) are not imported by the client.  It is
therefore cross-compiled with ``CGO_ENABLED=0`` — exactly like the existing ``archives/i/incus``
7.1.0 precedent ("incus client, 4 client tools built successfully with CGO_ENABLED=0").

Upstream build entry (``Makefile`` ``client:`` target): ``go install ./cmd/incus``.  This
recipe builds ``./cmd/incus`` directly with ``go build``.

HarmonyOS (OHOS) adaptation — all at the recipe level, no upstream source patch:
  1. ``CGO_ENABLED=0 GOOS=linux GOARCH=arm64`` — a static aarch64 ELF the OHOS kernel runs.
  2. The Go toolchain is self-bootstrapped (pinned version + official sha256); no host Go.
  3. The Go **linker** mmaps its output file; HMDFS rejects that
     (``link: mapping output file failed: permission denied``), so the link output and
     the GOTMPDIR/GOCACHE/GOMODCACHE live on the ext2-style app data partition
     (``/data/storage/el2/base/haps/entry/files``).
  4. Every ELF that OHOS fork/execs must carry a ``.codesign`` section; the built binary
     (and the ``go test`` binaries) are self-signed with ``binary-sign-tool``.

Upstream tests: the client package ``./cmd/incus`` plus every package in its import closure
that ships ``*_test.go`` are executed with ``go test -v`` (signed via a ``-exec`` wrapper).
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

# Go module path prefix of the main module (used to restrict the closure to incus packages).
_MODULE_PREFIX = "github.com/lxc/incus/v7"


class IncusFeatureClientConan(ConanFile):
    name = "incus-feature-client"
    version = "7.2.0"

    # Go toolchain bootstrapped into the (writable) workspace; no host dependency on a
    # system Go install.  Pinned to the exact linux-<hostarch> SDK plus official sha256.
    # incus go.mod declares `go 1.25.10`, so the local toolchain must be >= 1.25.10.
    _go_version = "1.25.10"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.25.10.linux-arm64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.25.10.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.25.10.linux-arm64.tar.gz",
            ],
            "654da1f9b50a5d1c2a85ccf8ed405aa89c06e94d18384628bf186f7712677b08",
        ),
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.25.10.linux-amd64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.25.10.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.25.10.linux-amd64.tar.gz",
            ],
            "42d4f7a32316aa66591eca7e89867256057a4264451aca10570a715b3637ba70",
        ),
    }

    package_type = "application"

    description = "Incus CLI client — command-line client for the Incus system container and VM manager (pure Go)"
    license = "Apache-2.0"
    homepage = "https://github.com/lxc/incus"
    url = "https://github.com/lxc/incus"
    topics = ("incus", "lxc", "container", "virtual-machine", "cli", "go")

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # No patches for incus-feature-client 7.2.0 (patches: []); kept for conandata
        # patch-export parity so the pipeline is uniform across recipes.
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("incus-feature-client supports Linux and OHOS targets only")

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOTOOLCHAIN", "local")
        env.define("GOPROXY", os.environ.get("GOPROXY", "https://goproxy.cn,direct"))
        env.define("GOSUMDB", os.environ.get("GOSUMDB", "sum.golang.google.cn"))

        go_workspace = self._go_workspace()
        env.define("TMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOCACHE", os.path.join(go_workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(go_workspace, "go-mod-cache"))
        # Pre-create subdirs: Go refuses to bootstrap without every path component.
        for d in ("tmp", "go-build-cache", "go-mod-cache", "bin"):
            os.makedirs(os.path.join(go_workspace, d), exist_ok=True)

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("incus_feature_client_go_env")

    def build(self):
        go = self._go_executable()
        # Build-time safety net in case generate() was skipped.
        for subdir in ("tmp", "go-build-cache", "go-mod-cache", "bin"):
            os.makedirs(os.path.join(self._go_workspace(), subdir), exist_ok=True)

        apply_conandata_patches(self)

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker mmap fails on HMDFS: link on an ext2-like workspace on OHOS.
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "incus")
        final_exe = os.path.join(out_dir, "incus")

        # Upstream `make client` = `go install ./cmd/incus` (no ldflags; Version comes from
        # internal/version/flex.go, i.e. "7.2" for this feature-branch tag).
        self.run(
            f'"{go}" build -trimpath -o "{linked_exe}" ./cmd/incus',
            cwd=self.source_folder,
            env=["incus_feature_client_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # Run the upstream Go test suite (client closure) and emit machine evidence
        # (HMBS_UPSTREAM_TEST_RESULT) for the HMBS evidence gate.
        self._run_upstream_tests(go)

    def package(self):
        copy(self, "incus", os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── upstream tests ────────────────────────────────────────────────

    def _client_test_packages(self, go, test_env):
        """Return the incus packages in the ``./cmd/incus`` import closure that ship tests.

        Upstream ships 122 ``*_test.go`` across the whole (server + client) tree, but only
        the client's own import closure can be built with CGO_ENABLED=0 — the server
        packages (``cmd/incusd``, ``internal/server/*``) require liblxc/cowsql/go-sqlite3.
        This mirrors the APKBUILD ``check()`` intent, restricted to the client sub-package.
        """
        proc = subprocess.run(
            [go, "list", "-deps", "-f", "{{.ImportPath}} {{.Dir}}", "./cmd/incus"],
            cwd=self.source_folder,
            env=test_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        pkgs = []
        for line in proc.stdout.decode(errors="replace").splitlines():
            parts = line.split()
            if len(parts) != 2:
                continue
            imp, directory = parts
            if not imp.startswith(_MODULE_PREFIX):
                continue
            if os.path.isdir(directory) and any(f.endswith("_test.go") for f in os.listdir(directory)):
                pkgs.append(imp)
        return pkgs

    def _run_upstream_tests(self, go):
        """Run ``go test -v -count=1`` for the client closure and emit HMBS markers.

        Each package is run in its own ``go test`` process: the shared
        ``shared/subprocess`` signal test installs a SIGHUP trap in a child ``sh`` and is
        timing-sensitive when many test binaries are driven by one invocation.
        """
        base_env = dict(os.environ)
        go_workspace = self._go_workspace()
        base_env.update({
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(go_workspace, "tmp"),
            "GOTMPDIR": os.path.join(go_workspace, "tmp"),
            "GOCACHE": os.path.join(go_workspace, "go-build-cache"),
            "GOMODCACHE": os.path.join(go_workspace, "go-mod-cache"),
        })
        goroot = self._goroot_for_go(go)
        if goroot:
            base_env["GOROOT"] = goroot
        base_env["PATH"] = os.path.dirname(go) + os.pathsep + base_env.get("PATH", "")

        packages = self._client_test_packages(go, base_env)
        self.output.info(f"incus-feature-client upstream test packages ({len(packages)}): " + ", ".join(packages))

        exec_cmd = ""
        if str(self.settings.os) == "OHOS":
            exec_cmd = self._write_test_exec_wrapper()

        agg = {"discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0}
        cases = []
        for pkg in packages:
            argv = [go, "test", "-v", "-count=1"]
            if exec_cmd:
                argv.append(f"-exec={exec_cmd}")
            argv.append(pkg)
            cmd = " ".join(argv)
            try:
                proc = subprocess.run(
                    argv,
                    cwd=self.source_folder,
                    env=base_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=3600,
                )
                out = proc.stdout.decode(errors="replace")
                rc = proc.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                out = f"go test failed to run: {exc}"
                rc = 1

            top = re.findall(r"^--- (PASS|FAIL|SKIP):\s+(\S+)", out, re.MULTILINE)
            sub = re.findall(r"^\s+--- (PASS|FAIL|SKIP):\s+(\S+)", out, re.MULTILINE)
            ran = re.findall(r"^=== RUN\s+(\S+)", out, re.MULTILINE)
            p = sum(1 for k, _ in top + sub if k == "PASS")
            f = sum(1 for k, _ in top + sub if k == "FAIL")
            s = sum(1 for k, _ in top + sub if k == "SKIP")
            agg["discovered"] += len(ran)
            agg["executed"] += p + f
            agg["passed"] += p
            agg["failed"] += f
            agg["skipped"] += s
            cases.extend(f"{pkg}: {name}" for name in ran)
            self.output.info(f"  {pkg}: RUN={len(ran)} PASS={p} FAIL={f} SKIP={s} rc={rc} cmd={cmd}")

        status = "failed" if agg["failed"] > 0 else ("passed" if agg["passed"] > 0 else "no_tests")
        upstream = dict(agg)
        upstream.update({"status": status, "framework": "go test", "packages": packages, "cases": cases})
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

        if agg["failed"] > 0:
            raise ConanInvalidConfiguration(f"incus-feature-client upstream tests failed: {agg['failed']} failing case(s)")

    def _write_test_exec_wrapper(self):
        """Return a ``<sh> <script>`` command for ``go test -exec`` that signs the
        compiled test binary before executing it (OHOS refuses to exec an unsigned ELF)."""
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
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        return f"{bash} {script}"

    # ── Go toolchain helpers (aligned with the qrcp / aiac / abbtr Go recipes) ──

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in (
                "/data/storage/el2/base/haps/entry/files",
                "/data/storage/el2/base/cache",
            ):
                candidate = os.path.join(base, "incus-feature-client-7.2.0-go")
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
            os.path.expanduser("~/usr/local/bin/binary-sign-tool"),
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
            os.path.expanduser("~/sdk/go1.25.10/bin/go"),
            os.path.expanduser("~/.goenv/versions/1.25.10/bin/go"),
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
        m = output.split("go version ")[-1].split(" ")[0]  # go1.25.10
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
