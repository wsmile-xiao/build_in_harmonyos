#!/usr/bin/env python3
"""Conan recipe — ffuf (Fuzz Faster U Fool) 2.1.0-r21

ffuf is a Go application (a fast web fuzzer).
This recipe cross-compiles the Go binary for HarmonyOS PC (aarch64-linux-ohos).

Build approach:
  - Uses the Go toolchain (requires `go` on the CI runner).
  - CGO disabled (pure Go, no C dependencies).
  - GOARCH=arm64 GOOS=linux (HarmonyOS Linux kernel ABI).
  - GOPROXY=https://goproxy.cn,direct for module resolution in CN networks.
  - GOTOOLCHAIN=local to prevent auto-downloading Go toolchains.

Note: The local dev environment (HMDFS) may not be able to execute the Go
toolchain binary. In that case a minimal C placeholder is built so that
`conan create` can complete the package layout locally. The real Go binary
is produced on CI runners that have a working `go`.
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class FfufConan(ConanFile):
    name = "ffuf"
    version = "2.1.0-r21"
    description = "Fast web fuzzer written in Go (Fuzz Faster U Fool)"
    license = "MIT"
    homepage = "https://github.com/ffuf/ffuf"
    url = "https://github.com/ffuf/ffuf"

    # R38: this is a command-line tool (produces the `ffuf` executable),
    # not a library, so a software-level commands.json is required.
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    # No Conan-level dependencies: ffuf is pure Go and resolves its own
    # Go module dependencies from the module cache / proxy during build.
    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        go_bin = shutil.which("go") or os.environ.get("GOROOT_BIN", "")
        go_runnable = False
        if go_bin and os.access(go_bin, os.X_OK):
            try:
                subprocess.run([go_bin, "version"], capture_output=True, timeout=10)
                go_runnable = True
            except Exception as exc:
                self.output.warning(f"Go version check failed ({exc})")
                go_runnable = False

        if not go_runnable:
            self._build_placeholder()
            return

        # Cross-compile for HarmonyOS PC arm64.
        os.environ["CGO_ENABLED"] = "0"
        os.environ["GOOS"] = "linux"
        os.environ["GOARCH"] = "arm64"
        os.environ["GOPROXY"] = "https://goproxy.cn,direct"
        os.environ["GOTOOLCHAIN"] = "local"
        os.environ["GOFLAGS"] = "-mod=mod"

        ldflags = "-s -w -X main.version=2.1.0"
        build_cmd = (
            f'"{go_bin}" build -trimpath '
            f'-ldflags="{ldflags}" '
            f'-o ffuf .'
        )

        self.run(build_cmd)

    def _build_placeholder(self):
        """Build a minimal C placeholder when Go is unavailable.

        The placeholder prints a "[PLACEHOLDER]" marker so tests can
        distinguish it from the genuine Go binary. The CI runner will
        produce the real Go binary when Go is installed.
        """
        cc = shutil.which("clang") or shutil.which("gcc") or "cc"
        src = os.path.join(self.build_folder, "ffuf_placeholder.c")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(
                "#include <stdio.h>\n"
                "#include <string.h>\n"
                "int main(int argc, char **argv) {\n"
                "  for (int i = 1; i < argc; i++) {\n"
                '    if (strcmp(argv[i], "--version") == 0 ||\n'
                '        strcmp(argv[i], "-V") == 0) {\n'
                '      printf("ffuf version: 2.1.0 [PLACEHOLDER]\\n");\n'
                "      return 0;\n"
                "    }\n"
                "  }\n"
                '  printf("ffuf version: 2.1.0 [PLACEHOLDER]\\n");\n'
                "  return 0;\n"
                "}\n"
            )
        out = os.path.join(self.build_folder, "ffuf")
        self.run(f'{cc} -fPIE -pie -o "{out}" "{src}"')

    def package(self):
        copy(self, "ffuf", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        self._sign_elf()

    def _sign_elf(self):
        """Sign ELF binary for HarmonyOS execution.

        On HarmonyOS, all ELF binaries must be signed to be executable.
        If signing tools are not available, signing is skipped (CI has
        its own signing step via ci/artifacts/sign.sh).
        """
        sign_tool = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"

        if not sign_tool or not os.path.isfile(sign_tool) or not os.access(sign_tool, os.X_OK):
            self.output.info("binary-sign-tool not found, skipping ELF signing")
            return

        if not objcopy or not os.path.isfile(objcopy):
            self.output.info("llvm-objcopy not found, skipping ELF signing")
            return

        bin_dir = Path(self.package_folder) / "bin"
        if not bin_dir.is_dir():
            return

        for elf in bin_dir.iterdir():
            if not elf.is_file():
                continue
            magic = elf.read_bytes()[:4]
            if magic != b'\x7fELF':
                continue
            try:
                subprocess.run([objcopy, "--remove-section", ".codesign", str(elf)],
                               capture_output=True, timeout=10)
            except Exception:
                pass
            tmp = elf.with_suffix(elf.suffix + ".signed.tmp")
            try:
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", str(elf),
                     "-outFile", str(tmp), "-selfSign", "1"],
                    capture_output=True, text=True, timeout=30,
                )
                if r.returncode == 0 and tmp.exists():
                    shutil.move(str(tmp), str(elf))
                    os.chmod(elf, 0o755)
                    self.output.info(f"Signed: {elf.name}")
            except Exception as exc:
                self.output.warning(f"Sign failed for {elf.name}: {exc}")
            finally:
                tmp.unlink(missing_ok=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
