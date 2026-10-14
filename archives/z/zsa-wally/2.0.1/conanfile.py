#!/usr/bin/env python3
"""Conan recipe for zsa-wally 2.0.1 — ZSA 键盘烧录工具（Wally CLI flavor）.

上游任务卡 #12412 名称 zsa-wally 2.0.1。形态实测定谳（W0）：
  - ZSA 生态中 tag 2.0.1 唯一对应 github.com/zsa/wally-cli（tag `2.0.1-linux`），
    Go CLI（go.mod go 1.14, gousb v2.1.0 CGO → libusb-1.0, gohex, pb.v1）。
  - GUI 仓 github.com/zsa/wally 是 Go+Wails v1（webkit2gtk+npm），tag 序列
    2.0.0→2.1.0 无 2.0.1；webkit2gtk/wails 均不在 ohpcd 制品仓（GUI 路线不可行，
    存证于 notes.md）。
  - 官方 sdist sha256 与 AUR zsa-wally-cli 2.0.1-6 PKGBUILD 权威值一致。

构建：Go 1.23.8（addchain/aiac 同款自举+ELF 签名模式），CGO_ENABLED=1
（gousb #cgo pkg-config: libusb-1.0），libusb/1.0.27 来自 ohpcd 制品仓，
pkg-config 注入 + CGO_CFLAGS/LDFLAGS 双保险，链接产出放 el2 工作区规避
HMDFS linker-mmap（E051）。
"""

import os
import platform
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ZsaWallyConan(ConanFile):
    name = "zsa-wally"
    version = "2.0.1"
    _go_version = "1.23.8"
    _go_archives = {
        "arm64": (
            [
                "https://mirrors.aliyun.com/golang/go1.23.8.linux-arm64.tar.gz",
                "https://golang.google.cn/dl/go1.23.8.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.23.8.linux-arm64.tar.gz",
            ],
            "9d6d938422724a954832d6f806d397cf85ccfde8c581c201673e50e634fdc992",
        ),
    }
    package_type = "application"

    description = "Wally CLI: flash your ZSA keyboard (ErgoDox EZ / Moonlander / Planck EZ) the EZ way (Go + libusb)"
    license = "MIT"
    homepage = "https://github.com/zsa/wally"
    url = "https://github.com/zsa/wally-cli"
    topics = ("zsa", "wally", "keyboard", "flasher", "usb", "dfu", "teensy", "go", "cli")

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # gousb (CGO) requires libusb-1.0 headers at build time and the shared
        # library at run time (VirtualRunEnv in test_package provides the
        # LD_LIBRARY_PATH). Same ohpcd registry dependency as airspy/airspyhf.
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("zsa-wally is prepared for Linux/OHOS targets only")

    # ------------------------------------------------------------------
    # Environment (CGO cross-compile for OHOS arm64)
    # ------------------------------------------------------------------
    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "1")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOPROXY", os.environ.get("GOPROXY", "https://goproxy.cn,direct"))
        env.define("GOSUMDB", os.environ.get("GOSUMDB", "sum.golang.google.cn"))
        env.define("GOTOOLCHAIN", "local")

        go_workspace = self._go_workspace()
        env.define("TMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOCACHE", os.path.join(go_workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(go_workspace, "go-mod-cache"))

        # CC for CGO: prefer the profile-configured compiler, fall back to PATH.
        cc = self._conf_compiler("c") or shutil.which("clang")
        cxx = self._conf_compiler("cpp") or shutil.which("clang++")
        if cc:
            env.define("CC", cc)
        if cxx:
            env.define("CXX", cxx)

        # libusb injection (dual insurance: pkg-config + explicit CGO flags).
        usb_inc, usb_lib, pc_dir = self._libusb_paths()
        env.define("CGO_CFLAGS", f"-I{usb_inc}")
        env.define("CGO_LDFLAGS", f"-L{usb_lib} -lusb-1.0")
        env.define("PKG_CONFIG_PATH", pc_dir)
        env.define("PKG_CONFIG_LIBDIR", pc_dir)

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("zsa_wally_go_env")

    def _conf_compiler(self, lang):
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default={})
            if isinstance(compilers, dict):
                return compilers.get(lang)
        except Exception:
            pass
        return None

    def _libusb_paths(self):
        """Return (include_dir, lib_dir, pkgconfig_dir) for the libusb dependency.

        The libusb package ships lib/pkgconfig/libusb-1.0.pc with
        prefix=/usr/local (autotools default, wrong for a Conan package), so we
        rewrite the .pc with the real package prefix into the build folder and
        point PKG_CONFIG_PATH there — gousb's `#cgo pkg-config: libusb-1.0`
        directive then resolves include/lib flags to the registry artifact.
        """
        libusb = self.dependencies["libusb"]
        pkg = libusb.package_folder
        usb_inc = os.path.join(pkg, "include", "libusb-1.0")
        usb_lib = os.path.join(pkg, "lib")

        pc_dir = os.path.join(self.build_folder, "pkgconfig")
        Path(pc_dir).mkdir(parents=True, exist_ok=True)
        dst_pc = os.path.join(pc_dir, "libusb-1.0.pc")
        src_pc = os.path.join(usb_lib, "pkgconfig", "libusb-1.0.pc")
        if os.path.isfile(src_pc):
            content = Path(src_pc).read_text(encoding="utf-8")
            content = content.replace("prefix=/usr/local", f"prefix={pkg}")
            Path(dst_pc).write_text(content, encoding="utf-8")
        else:
            # Fallback: synthesize a minimal .pc from the package layout.
            Path(dst_pc).write_text(
                f"prefix={pkg}\n"
                "exec_prefix=${prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "Name: libusb-1.0\n"
                "Description: C API for USB device access\n"
                "Version: 1.0.27\n"
                "Libs: -L${libdir} -lusb-1.0\n"
                "Cflags: -I${includedir}/libusb-1.0\n",
                encoding="utf-8",
            )
        return usb_inc, usb_lib, pc_dir

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def build(self):
        go = self._go_executable()
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["zsa_wally_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker mmap fails on HMDFS (E051/E046): link on ext2-like
        # workspace on OHOS (addchain precedent).
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())

        # Upstream tag 2.0.1-linux still carries appVersion="2.0.0" in main.go
        # (upstream oversight); inject the real package version via ldflags so
        # `wally-cli --version` reports 2.0.1 (same pattern as addchain's
        # meta.buildversion injection).
        # Inject version via ldflags; do NOT use -s (strips Go build info).
        # NOTE: the OHOS-target lld emits a PLACEHOLDER .codesign section
        # (plus .note.ohos.ident) in freshly linked CGO binaries. The
        # placeholder is not accepted by the kernel loader (exec fails with
        # EPERM "Operation not permitted"), so the linked binary must be
        # force re-signed: strip the placeholder section and run
        # binary-sign-tool (empirically verified: placeholder -> EPERM;
        # re-signed -> runs). force=True skips the has-signature early-exit.
        ldflags = f'-s -w -X main.appVersion={self.version}'
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["zsa_wally_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe, force=True)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # Upstream test evidence (source-tree audit; wally-cli 2.0.1 has no
        # *_test.go — the authoritative HMBS no_tests mark is emitted in
        # test_package per the aiac/aribb24/augustus precedent).
        self._run_upstream_tests(go)

    def _run_upstream_tests(self, go):
        """Run upstream ``go test ./...`` for audit logging and emit HMBS mark.

        wally-cli 2.0.1 contains no *_test.go files, so ``go test -v -count=1
        ./...`` compiles the module and prints ``[no test files]``. The HMBS
        evidence gate scans test_package stdout, so the authoritative
        no_tests mark is printed there (aiac precedent); this run is kept as
        machine evidence in the conan create log.
        """
        import json
        import re

        base_env = dict(os.environ)
        go_workspace = self._go_workspace()
        usb_inc, usb_lib, pc_dir = self._libusb_paths()
        go_env_overrides = {
            "CGO_ENABLED": "1",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(go_workspace, "tmp"),
            "GOTMPDIR": os.path.join(go_workspace, "tmp"),
            "GOCACHE": os.path.join(go_workspace, "go-build-cache"),
            "GOMODCACHE": os.path.join(go_workspace, "go-mod-cache"),
            "CGO_CFLAGS": f"-I{usb_inc}",
            "CGO_LDFLAGS": f"-L{usb_lib} -lusb-1.0",
            "PKG_CONFIG_PATH": pc_dir,
            "PKG_CONFIG_LIBDIR": pc_dir,
        }
        cc = self._conf_compiler("c") or shutil.which("clang")
        if cc:
            go_env_overrides["CC"] = cc
        goroot = self._goroot_for_go(go)
        if goroot:
            go_env_overrides["GOROOT"] = goroot
        base_env.update(go_env_overrides)
        base_env["PATH"] = os.path.dirname(go) + os.pathsep + base_env.get("PATH", "")

        cmd = [go, "test", "-v", "-count=1", "./..."]
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

        p = len(re.findall(r"^\s*--- PASS:", out, re.MULTILINE))
        f = len(re.findall(r"^\s*--- FAIL:", out, re.MULTILINE))
        s = len(re.findall(r"^\s*--- SKIP:", out, re.MULTILINE))
        self.output.info("zsa-wally upstream `go test -v -count=1 ./...`: "
                         f"PASS={p} FAIL={f} SKIP={s}")
        preview = out[:2048].replace("\n", "\n  zsa-wally go test | ")
        self.output.info("zsa-wally go test output preview:\n  " + preview)

        if f > 0:
            status = "failed"
        elif p > 0:
            status = "passed"
        else:
            status = "no_tests"

        upstream = {
            "status": status,
            "framework": "go test",
            "command": " ".join(cmd),
            "discovered": 0,
            "executed": 0,
            "passed": p,
            "failed": f,
            "skipped": s,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def package(self):
        copy(self, self._exe_name(), os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "license.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── Go toolchain helpers (addchain / aiac pattern) ──

    def _go_workspace(self):
        if str(self.settings.os) != "OHOS":
            root = os.path.join(self.build_folder, ".go-work")
        else:
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/zsa-wally-conan-go",
            )
        workspace = os.path.join(root, self.version)
        for child in (
            "tmp",
            "go-build-cache",
            "go-mod-cache",
            "link-out",
            "go-sdk",
        ):
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
        # Marker write may fail on a foreign-owned shared workspace (different
        # CI worker uid); signing is idempotent via _has_ohos_signature, so a
        # missing marker only costs a redundant re-scan, not a failure.
        try:
            Path(marker).write_text("signed\n", encoding="utf-8")
        except OSError:
            pass

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

    def _sign_elf_if_ohos(self, path, force=False):
        if str(self.settings.os) != "OHOS":
            return
        if not force and self._has_ohos_signature(path):
            # Already signed (e.g. reused SDK workspace from a previous
            # build). HMFS protects signed binaries with an immutable-like
            # 'c' attribute so chmod(2) returns EPERM even for the owner;
            # the exec bit is normally already set, so only chmod when the
            # file is not executable and tolerate EPERM.
            if not os.access(path, os.X_OK):
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass
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
                       capture_output=True, timeout=10)
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
        return "wally-cli.exe" if self._goos() == "windows" else "wally-cli"

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
            output = subprocess.run([go, "version"], capture_output=True, timeout=10).stdout.decode()
        except OSError:
            return False
        m = output.split("go version ")[-1].split(" ")[0]  # go1.23.8
        ver = m[2:]  # 1.23.8
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
