#!/usr/bin/env python3
"""Conan recipe — flow-cli homebrew (v2.17.4, pre-built binary).

Flow CLI is a Go-based command-line tool for building Flow blockchain applications.
Uses pre-built linux/arm64 binary from GitHub releases since the OHOS CI worker
lacks a Go toolchain (known platform limitation, see E128 use-prebuilt-package).

R32: OHOS is treated as Linux variant; no special OS detection needed for Go.
R28: test_package/ exists.
R34: test_package verifies the binary runs and produces correct output.

Permission strategy:
- Use system tar for extraction (preserves execute bit from tarball metadata).
- In package(), extract directly into package_folder/bin/ via system tar -C,
  avoiding conan.tools.files.copy() (drops execute bit) and os.rename()
  (may lose permissions on OHOS HMDFS).
- No chmod needed: system 'chmod' command is not available on OHOS CI worker PATH
  and os.chmod() is ineffective on OHOS HMDFS (E046) anyway.
"""
import os

from conan import ConanFile
from conan.tools.files import download
from conan.tools.layout import basic_layout


class FlowCliConan(ConanFile):
    name = "flow-cli"
    version = "homebrew"
    description = "Command-line interface for building Flow applications"
    license = "Apache-2.0"
    homepage = "https://onflow.org"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        # Use system tar for extraction instead of Conan's get().
        # Conan's get() uses Python tarfile.extractall() which on Python 3.12+
        # applies the "data" filter that strips the execute permission bit.
        # The system tar command preserves original permissions from the tarball.
        sources = self.conan_data["sources"]
        url = sources["url"]
        sha256 = sources["sha256"]
        filename = "flow-cli-v2.17.4-linux-arm64.tar.gz"
        download(self, url, filename, sha256=sha256)
        self.run(f"tar xzf {filename}")

    def build(self):
        # Pre-built binary — no Go toolchain needed
        # Binary is extracted to source_folder by source() with system tar
        # which preserves the execute permission bit from tarball metadata.
        # package() extracts directly into package_folder/bin/ via system tar -C,
        # so the execute permission from the tarball is preserved end-to-end
        # without any os.chmod() or os.rename().
        self.output.info("Using pre-built flow-cli linux/arm64 binary from GitHub releases")

    def package(self):
        # Extract the pre-built binary directly into the package folder
        # using system tar (same mechanism as source()).
        #
        # This avoids os.rename() which may lose the execute permission
        # on OHOS HMDFS (cross-device rename or HMDFS default-permission
        # assignment), and avoids conan.tools.files.copy() which drops
        # the execute bit.  System tar writes the file via the kernel
        # write() syscall with the exact permission bits from the tarball
        # metadata — the filesystem driver honours these at creation time,
        # so no separate chmod is needed (and chmod is ineffective on
        # OHOS anyway — see E046).
        tarball = os.path.join(self.source_folder, "flow-cli-v2.17.4-linux-arm64.tar.gz")
        if os.path.exists(tarball):
            bin_dir = os.path.join(self.package_folder, "bin")
            os.makedirs(bin_dir, exist_ok=True)
            self.run(f"tar xzf {tarball} -C {bin_dir}")
        else:
            # Fallback: binary already extracted by source() but
            # tarball was cleaned up — use os.rename() as best effort.
            binary_name = "flow-cli"
            src = os.path.join(self.source_folder, binary_name)
            dst_dir = os.path.join(self.package_folder, "bin")
            dst = os.path.join(dst_dir, binary_name)
            if os.path.exists(src):
                os.makedirs(dst_dir, exist_ok=True)
                os.rename(src, dst)
            else:
                self.output.warning("Binary not found at expected path, searching...")
                for root, _dirs, files in os.walk(self.source_folder):
                    if binary_name in files:
                        src_file = os.path.join(root, binary_name)
                        os.makedirs(dst_dir, exist_ok=True)
                        os.rename(src_file, dst)
                        break

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []