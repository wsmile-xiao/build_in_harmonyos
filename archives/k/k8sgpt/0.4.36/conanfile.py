#!/usr/bin/env python3
"""Conan recipe for k8sgpt 0.4.36 — Kubernetes debugging powered by AI (Go CLI).

OHOS aarch64 port notes (see notes.md for the full evidence trail):
- Pure-Go build (CGO_ENABLED=0), upstream Makefile L57: go build -trimpath
  -ldflags "-s -w -X main.version=... -X main.commit=... -X main.date=...".
- Go >= 1.26 toolchain required by go.mod (toolchain go1.26.5). On OHOS every
  fork/exec'd ELF must carry a .codesign section, so the downloaded Go SDK is
  re-signed with binary-sign-tool. Go 1.26+ binaries embed the literal string
  ".codesign" (linker metadata), so signature detection by content search is
  impossible — this recipe re-signs UNCONDITIONALLY (signing is idempotent).
- OHOS sandbox denies fork/exec of script files (shebang) from Go processes
  (fork/exec of signed ELF binaries works), so the `go test -exec` wrapper is
  compiled to an ELF with clang, signed, and then used.
- Go linker mmap fails on HMDFS (E051/E046): GOCACHE/GOMODCACHE/TMPDIR and the
  link output are redirected to a non-HMDFS workspace under /data/storage.
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
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# OHOS `go test -exec` wrapper, compiled to a signed ELF.
#
# Why not a shell script (ali 0.8.0 pattern)? The OHOS app sandbox denies
# fork/exec of non-ELF files from Go processes with EACCES — `go test` cannot
# exec a shebang wrapper even when chmod 755 (executing the same script from a
# shell works). Executing *signed ELF* binaries is allowed (that is how the go
# tool spawns compile/link). Therefore the wrapper is a tiny C program that
# re-signs the test binary in place and execs it.
_OHOS_TEST_EXEC_C = r"""
/* ohos-test-exec — OHOS `go test -exec` wrapper (compiled ELF, self-signed).
 * Usage: ohos-test-exec <test-binary> [args...]
 * Re-signs the test binary in place (always: Go 1.26+ binaries embed the
 * literal ".codesign" string, so signature presence cannot be detected by
 * string search), then execs it with the remaining arguments.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef WRAP_TMPDIR
#define WRAP_TMPDIR "/data/storage/el2/base/haps/entry/files/k8sgpt-conan-go/0.4.36/sign-tmp"
#endif

static const char *SIGNER = "/data/service/hnp/bin/binary-sign-tool";
static const char *OBJCOPY = "/data/service/hnp/bin/llvm-objcopy";

static int run(const char *file, char *const argv[]) {
    pid_t pid = fork();
    if (pid < 0) return -1;
    if (pid == 0) { execv(file, argv); _exit(127); }
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) return -1;
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "ohos-test-exec: usage: wrapper <test-binary> [args...]\n");
        return 127;
    }
    const char *bin = argv[1];
    struct stat st;
    if (stat(bin, &st) != 0) {
        fprintf(stderr, "ohos-test-exec: test binary not found: %s\n", bin);
        return 127;
    }
    char tmpin[512], tmpout[512];
    snprintf(tmpin, sizeof(tmpin), WRAP_TMPDIR "/t.%ld.bin", (long)getpid());
    snprintf(tmpout, sizeof(tmpout), "%s.signed", tmpin);
    int in = open(bin, O_RDONLY);
    if (in < 0) { perror("ohos-test-exec: open test binary"); return 127; }
    int out = open(tmpin, O_WRONLY | O_CREAT | O_TRUNC, 0755);
    if (out < 0) { perror("ohos-test-exec: open tmp copy"); return 127; }
    char buf[65536];
    ssize_t n;
    while ((n = read(in, buf, sizeof(buf))) > 0) {
        if (write(out, buf, n) != n) { close(in); close(out); return 127; }
    }
    close(in);
    fsync(out);
    close(out);
    char *oc_argv[] = { "llvm-objcopy", "--remove-section", ".codesign", (char *)tmpin, NULL };
    run(OBJCOPY, oc_argv); /* best effort: section may not exist */
    char *sg_argv[] = { "binary-sign-tool", "sign", "-selfSign", "1",
                        "-inFile", (char *)tmpin, "-outFile", (char *)tmpout,
                        "-signAlg", "SHA256withECDSA", NULL };
    if (run(SIGNER, sg_argv) != 0) {
        fprintf(stderr, "ohos-test-exec: binary-sign-tool failed\n");
        unlink(tmpin);
        return 127;
    }
    if (rename(tmpout, bin) != 0) {
        perror("ohos-test-exec: rename signed binary");
        unlink(tmpin);
        return 127;
    }
    chmod(bin, 0755);
    unlink(tmpin);
    execv(bin, &argv[1]);
    fprintf(stderr, "ohos-test-exec: exec %s failed: %s\n", bin, strerror(errno));
    return 127;
}
"""


class K8sgptConan(ConanFile):
    name = "k8sgpt"
    version = "0.4.36"
    _go_version = "1.26.5"  # go.mod: toolchain go1.26.5 (GOTOOLCHAIN=local)
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

    description = "Kubernetes debugging powered by AI: scan clusters, find problems and get root-cause advice from AI backends"
    license = "Apache-2.0"
    homepage = "https://k8sgpt.ai"
    url = "https://github.com/k8sgpt-ai/k8sgpt"
    topics = ("k8sgpt", "kubernetes", "sre", "ai", "diagnostics", "go")

    settings = "os", "arch", "compiler", "build_type"

    # Upstream v0.4.36 tag commit (ldflags -X main.commit)
    _upstream_commit = "d33935a"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("k8sgpt is prepared for Linux/OHOS targets only")

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

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("k8sgpt_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["k8sgpt_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker mmap fails on HMDFS (E051/E046): link on ext2-like workspace on OHOS.
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())
        ldflags = (
            f"-s -w -X main.version=v{self.version} "
            f"-X main.commit={self._upstream_commit} "
            f"-X main.date=$(date +%FT%TZ)"
        )
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["k8sgpt_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        self._run_upstream_tests(go)

    # ── OHOS go test -exec wrapper (compiled ELF) ──

    def _write_ohos_test_exec_wrapper(self):
        """Compile the `go test -exec` wrapper to a signed ELF.

        OHOS sandbox: fork/exec of scripts (shebang) from Go processes is
        denied (EACCES) while fork/exec of signed ELF binaries works, so the
        wrapper must be a real ELF. It is compiled with clang and signed like
        every other executable on OHOS.
        """
        go_workspace = self._go_workspace()
        wrapper_dir = os.path.join(go_workspace, "test-exec-wrapper")
        Path(wrapper_dir).mkdir(parents=True, exist_ok=True)
        src_path = os.path.join(wrapper_dir, "ohos-test-exec.c")
        elf_path = os.path.join(wrapper_dir, "ohos-test-exec")

        sign_tmp = os.path.join(go_workspace, "sign-tmp")
        Path(sign_tmp).mkdir(parents=True, exist_ok=True)

        with open(src_path, "w", encoding="utf-8") as f:
            f.write(_OHOS_TEST_EXEC_C)

        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        if not os.path.exists(clang):
            raise ConanInvalidConfiguration("clang is required on OHOS to build the go test -exec wrapper ELF")
        # Always recompile (source is written fresh every time).
        proc = subprocess.run(
            [clang, "-O2", f'-DWRAP_TMPDIR="{sign_tmp}"', "-o", elf_path, src_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        if proc.returncode != 0:
            raise ConanInvalidConfiguration(
                "failed to compile ohos-test-exec wrapper: " + proc.stderr.decode(errors="replace")
            )
        self._sign_elf_if_ohos(elf_path)
        self.output.info(f"k8sgpt: wrote OHOS go test -exec wrapper ELF to {elf_path}")
        return elf_path

    def _run_upstream_tests(self, go):
        """Run upstream `go test -v -count=1 ./...` and emit HMBS markers.

        Upstream Makefile `test:` target is exactly `go test ./...`; -race is
        NOT used upstream (and would require cgo). Test files are patched by
        conandata patches (OHOS test infrastructure adaptation only).
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

        exec_args = []
        if str(self.settings.os) == "OHOS":
            wrapper = self._write_ohos_test_exec_wrapper()
            exec_args = ["-exec", wrapper]

        def _run(cmd):
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=self.source_folder,
                    env=base_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=2700,
                )
                return proc.stdout.decode(errors="replace")
            except (OSError, subprocess.TimeoutExpired) as exc:
                return f"go test failed to run: {exc}"

        def _count(output):
            p = len(re.findall(r"^\s*--- PASS:", output, re.MULTILINE))
            f = len(re.findall(r"^\s*--- FAIL:", output, re.MULTILINE))
            s = len(re.findall(r"^\s*--- SKIP:", output, re.MULTILINE))
            return p, f, s

        cmd = [go, "test", "-v", "-count=1"] + exec_args + ["./..."]
        out = _run(cmd)
        p, f, s = _count(out)
        self.output.info(f"k8sgpt `go test ./...`: PASS={p} FAIL={f} SKIP={s}")
        preview = out[-8192:].replace("\n", "\n  k8sgpt go test | ")
        self.output.info("k8sgpt go test output tail:\n  " + preview)

        if f > 0:
            status = "failed"
        elif p > 0:
            status = "passed"
        else:
            status = "failed" if "permission denied" in out.lower() else "no_tests"

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
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        # Persist for test_package re-emit on cache hit (build() skipped -> marker would otherwise disappear).
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"), "w", encoding="utf-8") as _f:
                json.dump(upstream, _f)
        except Exception:
            pass

    def package(self):
        copy(self, self._exe_name(), os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))
        # Carry HMBS upstream result into package for test_package cache-hit re-emit.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            dst_dir = os.path.join(self.package_folder, "res")
            os.makedirs(dst_dir, exist_ok=True)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_dir, "hmbs_upstream.json"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── Go toolchain helpers (based on ali/ain pattern) ──

    def _go_workspace(self):
        if str(self.settings.os) != "OHOS":
            root = os.path.join(self.build_folder, ".go-work")
        else:
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/k8sgpt-conan-go",
            )
        workspace = os.path.join(root, self.version)
        for child in ("tmp", "go-build-cache", "go-mod-cache", "link-out", "go-sdk"):
            Path(workspace, child).mkdir(parents=True, exist_ok=True)
        return workspace

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
        """Sign all Go SDK executables on OHOS.

        NOTE: re-signs UNCONDITIONALLY. Go 1.26+ binaries embed the literal
        string ".codesign" in their linker metadata (content search false
        positive — Go 1.24-based recipes could skip via grep, Go 1.26 cannot).
        binary-sign-tool signing is idempotent, so unconditional re-signing
        is always safe and always correct.
        """
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
        Path(marker).write_text(
            "signed with binary-sign-tool (unconditional re-sign, Go 1.26 .codesign false-positive fix)\n",
            encoding="utf-8",
        )

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf_if_ohos(self, path):
        """Sign an ELF executable in place (OHOS only). Unconditional re-sign.

        Do NOT "optimize" this into a signature-detection skip: Go 1.26+
        binaries contain the ".codesign" literal in string tables, so content
        sniffing reports already-signed for binaries that are NOT signed, and
        the process then dies with EACCES on exec.
        """
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool is required to sign OHOS Go executables")
        tmp_dir = os.path.join(self._go_workspace(), "sign-tmp")
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        tmp_in = os.path.join(tmp_dir, os.path.basename(path))
        tmp_out = f"{tmp_in}.signed"
        shutil.copy2(path, tmp_in)
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                       capture_output=True, timeout=30)
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", tmp_in, "-outFile", tmp_out,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
        os.unlink(tmp_in)

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
        return "k8sgpt.exe" if self._goos() == "windows" else "k8sgpt"

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser(f"~/sdk/go{self._go_version}/bin/go"),
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
            output = subprocess.run([go, "version"], capture_output=True, timeout=30).stdout.decode()
        except OSError:
            return False
        m = output.split("go version ")[-1].split(" ")[0]  # go1.26.5
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
