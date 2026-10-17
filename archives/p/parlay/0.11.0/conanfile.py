#!/usr/bin/env python3
"""Conan recipe for parlay 0.11.0 — SBOM enrichment CLI (pure Go).

parlay takes a CycloneDX/SPDX SBOM and enriches it with data from
ecosyste.ms, Snyk and OpenSSF Scorecard. Pure-Go command-line application,
entry is the root package (main.go at repo root), built with:

    CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -trimpath \
      -ldflags "-s -w -X ...version=0.11.0 (x3)" -o parlay .

Upstream 0.11.0 ships 13 *_test.go files with 72 Test functions
(`grep -rhoE '^func (Test[A-Za-z0-9_]+)' --include='*_test.go' | wc -l`).
Official test entry is `make test` -> `go test -cover -v ./...`
(lint step needs golangci-lint, not run here). This recipe runs
`go test -v -count=1 ./...` in build() and emits the HMBS machine-evidence
marker with deterministic counts parsed from `--- PASS:/--- FAIL:/--- SKIP:`
lines at column 0 only (subtests excluded; single source, no arithmetic patch-ups).

HarmonyOS notes:
- Go linker needs an ext2-like workspace on OHOS to avoid
  `mapping output file failed: permission denied` (HMDFS mmap restriction).
- OHOS executables (and Go SDK tool binaries) must be self-signed with
  binary-sign-tool before they can be fork/exec'd.
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
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


# Upstream parlay 0.11.0 ships 13 *_test.go files, 72 Test functions:
#   internal/utils/cdx_test.go                 -> 1
#   internal/utils/input_test.go               -> 4
#   internal/utils/spdx_test.go                -> 6
#   lib/ecosystems/cache_test.go               -> 10
#   lib/ecosystems/enrich_cyclonedx_test.go    -> 16
#   lib/ecosystems/enrich_spdx_test.go         -> 3
#   lib/ecosystems/package_test.go             -> 5
#   lib/ecosystems/repo_test.go                -> 2
#   lib/sbom/decode_test.go                    -> 5
#   lib/scorecard/enrich_test.go               -> 5
#   lib/snyk/enrich_test.go                    -> 9
#   lib/snyk/package_test.go                   -> 3
#   lib/snyk/self_test.go                      -> 3
# Counting command (run at the tag root):
#   grep -rhoE '^func (Test[A-Za-z0-9_]+)' --include='*_test.go' . | wc -l
UPSTREAM_TEST_DISCOVERED = 72
UPSTREAM_TEST_FRAMEWORK = "go test"
UPSTREAM_TEST_COMMAND = "go test -v -count=1 ./..."


class ParlayConan(ConanFile):
    name = "parlay"
    version = "0.11.0"
    _go_version = "1.24.0"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.24.0.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.24.0.linux-arm64.tar.gz",
            ],
            "c3fa6d16ffa261091a5617145553c71d21435ce547e44cc6dfb7470865527cc7",
        ),
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.24.0.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.24.0.linux-amd64.tar.gz",
            ],
            "dea9ca38a0b852a74e81c26134671af7c0fbe65d81b0dc1c5bfe22cf7d4c8858",
        ),
    }
    package_type = "application"

    description = "Enrich SBOMs with data from third party services (pure Go CLI)"
    license = "Apache-2.0"
    homepage = "https://github.com/snyk/parlay"
    url = "https://github.com/snyk/parlay"
    topics = ("parlay", "sbom", "cyclonedx", "spdx", "snyk", "go")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("parlay supports Linux and OHOS targets only")
        if self.settings.os in ("Linux", "OHOS"):
            pass

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
        for d in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(go_workspace, d), exist_ok=True)

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("parlay_go_env")

    def build(self):
        go = self._go_executable()
        for subdir in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(self._go_workspace(), subdir), exist_ok=True)
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["parlay_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        if str(self.settings.os) == "OHOS":
            link_out_dir = os.path.join(self._go_workspace(), "link-out")
        else:
            link_out_dir = out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "parlay")
        final_exe = os.path.join(out_dir, "parlay")
        ldflags = (
            "-s -w"
            " -X github.com/snyk/parlay/internal/commands.version=0.11.0"
            " -X github.com/snyk/parlay/lib/ecosystems.Version=0.11.0"
            " -X github.com/snyk/parlay/lib/snyk.Version=0.11.0"
        )
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["parlay_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # Upstream official tests (mandatory): go test -v -count=1 ./...
        # Counts are parsed from --- PASS:/--- FAIL:/--- SKIP: lines only.
        self._run_upstream_tests(go)

    def package(self):
        copy(self, "parlay", os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _write_go_test_exec_wrapper(self, go_workspace):
        """Write OHOS `go test -exec` wrapper that self-signs test binaries.

        On OHOS every fork/exec'd ELF must carry a `.codesign` section.
        `go test` builds ephemeral `.test` binaries under GOTMPDIR and execs
        them directly; without signing the kernel rejects them (permission
        denied) so `go test -v` returns 1 with zero `--- PASS:` lines. The
        wrapper signs `$1` with binary-sign-tool (when available) then
        `exec "$@"`. Shell script itself needs no signing.
        """
        wrapper = os.path.join(go_workspace, "tmp", "go-test-exec.sh")
        os.makedirs(os.path.dirname(wrapper), exist_ok=True)
        content = (
            "#!/bin/sh\n"
            "# HMBS OHOS go test -exec wrapper: self-sign $1 then exec.\n"
            "bin=\"$1\"\n"
            "if [ -f \"$bin\" ]; then\n"
            "  if od -An -tx1 \"$bin\" 2>/dev/null | head -1 | grep -q \"7f 45 4c 46\"; then\n"
            "    signer=\"\"\n"
            "    for c in \"${OHOS_BINARY_SIGN_TOOL:-}\" \"${BINARY_SIGN_TOOL:-}\""
            " /data/service/hnp/bin/binary-sign-tool"
            " /storage/Users/currentUser/usr/local/bin/binary-sign-tool; do\n"
            "      if [ -n \"$c\" ] && [ -f \"$c\" ]; then signer=\"$c\"; break; fi\n"
            "    done\n"
            "    if [ -z \"$signer\" ]; then signer=\"$(command -v binary-sign-tool 2>/dev/null || true)\"; fi\n"
            "    if [ -n \"$signer\" ] && [ -f \"$signer\" ]; then\n"
            "      if ! grep -q \"\\.codesign\" \"$bin\" 2>/dev/null; then\n"
            "        out=\"$bin.signed\"\n"
            "        if \"$signer\" sign -selfSign 1 -inFile \"$bin\" -outFile \"$out\""
            " -signAlg SHA256withECDSA >/dev/null 2>&1; then\n"
            "          cat \"$out\" > \"$bin\" 2>/dev/null || cp \"$out\" \"$bin\" 2>/dev/null || true\n"
            "        fi\n"
            "        rm -f \"$out\" 2>/dev/null || true\n"
            "      fi\n"
            "      chmod +x \"$bin\" 2>/dev/null || true\n"
            "    fi\n"
            "  fi\n"
            "fi\n"
            "exec \"$@\"\n"
        )
        Path(wrapper).write_text(content, encoding="utf-8")
        try:
            os.chmod(wrapper, 0o755)
        except OSError:
            pass
        return wrapper

    def _run_upstream_tests(self, go):
        """Run upstream `go test -v -count=1 ./...` and emit the HMBS marker.

        Deterministic single-source counting: only `--- PASS:`, `--- FAIL:`
        and `--- SKIP:` top-level result lines are counted. No fallback
        string counting, no returncode-based patch-ups. Raw numbers are kept
        as-is; unexecuted registrations are explained via reason/gaps, never
        by inflating skipped.
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
        for key in ("OHOS_BINARY_SIGN_TOOL", "BINARY_SIGN_TOOL"):
            if os.environ.get(key):
                base_env[key] = os.environ[key]

        is_ohos = str(self.settings.os) == "OHOS"
        exec_wrapper = None
        if is_ohos:
            try:
                exec_wrapper = self._write_go_test_exec_wrapper(go_workspace)
            except OSError as exc:
                self.output.warning(f"go test -exec wrapper not written: {exc}")
                exec_wrapper = None

        if exec_wrapper:
            cmd = [go, "test", "-v", "-count=1", "-exec", exec_wrapper, "./..."]
            cmd_label = "go test -v -count=1 -exec <ohos-sign-wrapper> ./..."
        else:
            cmd = [go, "test", "-v", "-count=1", "./..."]
            cmd_label = UPSTREAM_TEST_COMMAND
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
            returncode = proc.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            out = f"go test failed to run: {exc}"
            returncode = 127

        passed = 0
        failed = 0
        skipped = 0
        # Only column-0 lines are top-level Test functions. go test -v
        # indents subtests (t.Run) as "    --- PASS: Parent/child";
        # counting stripped lines would include subtests and push
        # executed above the registered 72.
        for line in out.splitlines():
            if line.startswith("--- PASS:"):
                passed += 1
            elif line.startswith("--- FAIL:"):
                failed += 1
            elif line.startswith("--- SKIP:"):
                skipped += 1

        executed = passed + failed
        discovered = UPSTREAM_TEST_DISCOVERED
        # Never patch numbers to fit: keep raw parsed counts so the
        # identities passed+failed==executed and executed+skipped<=discovered
        # hold from a single deterministic source. Unexecuted registrations
        # are explained via reason/gaps, not by inflating skipped.
        reason_extra = ""
        if executed + skipped > discovered:
            # More results than registered: report as-is, flag in reason.
            reason_extra = (
                f"parsed executed+skipped ({executed + skipped}) exceeds "
                f"registered discovered ({discovered}); counts are raw "
                f"go test -v output, returncode={returncode}."
            )
        # Always leave full test output in the conan log so the next
        # preflight round can diagnose zero-execution failures (e.g. test
        # binary exec rejection) instead of guessing from the marker alone.
        self.output.info(
            f"parlay upstream `{cmd_label}`: returncode={returncode} "
            f"PASS={passed} FAIL={failed} SKIP={skipped}"
        )
        tail_lines = out.splitlines()[-80:]
        if tail_lines:
            preview = "\n".join(tail_lines)
            self.output.info("parlay go test output tail:\n" + preview)
        else:
            self.output.info("parlay go test produced no output lines.")

        if failed > 0 or returncode != 0:
            status = "failed"
        else:
            status = "passed"

        reason = (
            "conanfile.py build() ran `go test -v -count=1 ./...` on the "
            "device; counts parsed from `--- PASS:/--- FAIL:/--- SKIP:` lines. "
            f"returncode={returncode}."
        )
        if exec_wrapper:
            reason += " OHOS test binaries self-signed via go test -exec wrapper."
        if reason_extra:
            reason += " " + reason_extra
        # Attach the output tail to the reason so the failure evidence
        # travels with the marker (log excerpts may be truncated by HMBS).
        if status == "failed" and tail_lines:
            tail_excerpt = "\n".join(tail_lines[-20:])[:2000]
            reason += " output tail: " + tail_excerpt.replace("\n", " | ")

        upstream = {
            "status": status,
            "framework": UPSTREAM_TEST_FRAMEWORK,
            "command": UPSTREAM_TEST_COMMAND,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": reason,
        }
        # Gaps: any registered test not observed as pass/fail/skip needs an
        # explicit category.executed==0 with returncode!=0 means the harness
        # never ran (e.g. exec/compile failure), not silent skips.
        missing = discovered - executed - skipped
        if status != "passed" and missing > 0:
            if executed == 0 and failed == 0:
                category = "ohos_feature"
                detail = (
                    "go test exited nonzero with zero --- PASS/--- FAIL lines; "
                    "test binaries did not execute on device (suspected OHOS "
                    "exec/sign or harness failure; see output tail in reason). "
                    f"returncode={returncode}."
                )
            else:
                category = "test_failure"
                detail = (
                    "registered but unobserved tests after parsing go test -v "
                    f"output; returncode={returncode}."
                )
            upstream["gaps"] = [
                {
                    "count": missing,
                    "category": category,
                    "detail": detail,
                    "evidence": f"returncode={returncode}, executed={executed}, tail in reason",
                }
            ]
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False), flush=True)

        if failed > 0 or returncode != 0:
            from conan.errors import ConanException
            raise ConanException(
                f"go test failed: returncode={returncode}, passed={passed}, failed={failed}"
            )

    # -- Go toolchain helpers (aligned with aiac/adbtuifm Go recipes) --

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in (
                "/data/storage/el2/base/haps/entry/files",
                "/data/storage/el2/base/cache",
            ):
                candidate = os.path.join(base, "parlay-0.11.0-go")
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
            self.output.warning(f"binary-sign-tool not found; OHOS may reject unsigned executable: {path}")
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
            signer, "sign", "-selfSign", "1",
            "-inFile", tmp_in, "-outFile", tmp_out,
            "-signAlg", "SHA256withECDSA",
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
            os.path.expanduser("~/sdk/go1.24.0/bin/go"),
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
        m = output.split("go version ")[-1].split(" ")[0]
        ver = m[2:] if m.startswith("go") else m
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
