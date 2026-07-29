#!/usr/bin/env python3
"""Conan recipe for pbzip2 1.1.13 — parallel bzip2 compressor.

pbzip2 is a parallel implementation of the bzip2 block-sorting file
compressor that uses pthreads and achieves near-linear speedup on
multi-core machines. It produces and consumes bzip2-compatible files.

Build system: simple Makefile (no autotools configure script).
The Makefile respects CXX, CXXFLAGS, LDFLAGS and LDLIBS.
License: bzip2-1.0.6 (BSD-style)
"""
import os
import shlex
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class Pbzip2Conan(ConanFile):
    name = "pbzip2"
    version = "1.1.13"
    description = "pbzip2 — parallel bzip2 compressor/decompressor using pthreads"
    license = "bzip2-1.0.6"
    homepage = "https://launchpad.net/pbzip2"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # bzip2 is available as a pre-compiled system package at ~/usr/local
    # (installed via cmd-pkgs). The Makefile uses PREFIX to locate headers
    # and libraries: -I$(PREFIX)/include and -L$(PREFIX)/lib.

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Build in source directory — pbzip2's Makefile is in the source root
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        # R32: Platform check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        sources = self.conan_data["sources"]
        download_args = {key: value for key, value in sources.items() if key != "backup_urls"}
        try:
            get(self, **download_args, strip_root=True)
        except Exception:
            backup_urls = sources.get("backup_urls", [])
            if not backup_urls:
                raise
            for index, backup_url in enumerate(backup_urls):
                try:
                    self.output.warning(f"Primary URL failed, trying backup: {backup_url}")
                    get(self, url=backup_url, sha256=sources["sha256"], strip_root=True)
                    return
                except Exception:
                    if index == len(backup_urls) - 1:
                        raise

    def generate(self):
        # AutotoolsToolchain generates CC, CXX, CFLAGS, CXXFLAGS, LDFLAGS, etc.
        # R33: All flags come from Conan toolchain, no shell env vars in build()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # bzip2 is NOT pre-installed on OHOS CI workers — ~/usr/local has no
        # bzlib.h or libbz2.a. The bzip2 archive package ships only a legacy
        # ohc-run.py manifest (no conanfile.py), so it cannot be consumed as
        # a Conan dependency. Build bzip2's static lib from source into a
        # local prefix and point pbzip2's Makefile at it via PREFIX.
        prefix = self._build_bzip2()

        # pbzip2 uses a plain Makefile (no configure script needed).
        # The configure wrapper (patch 0003) is a no-op for G0 verification.
        # R9: Use -j1, never -j$(nproc)
        # R33: CXX comes from Conan toolchain env; CXXFLAGS/LDFLAGS use PREFIX
        #      from the Makefile to locate bzip2 headers and libraries.
        # GNU Make command-line variables override Makefile '=' assignments,
        # so PREFIX passed here takes precedence over the Makefile default.
        self.run(f'make -j1 PREFIX={shlex.quote(prefix)}', env="conanbuildenv")

    def _build_bzip2(self):
        """Build bzip2 1.0.8 static lib + headers into a local prefix.

        OHOS CI workers do not ship bzip2 development files. We compile
        libbz2.a (with -fPIC so it links into the pbzip2 binary) and
        install bzlib.h + libbz2.a into <build_folder>/bzip2_prefix.
        """
        bzip2_prefix = os.path.join(self.build_folder, "bzip2_prefix")
        libbz2 = os.path.join(bzip2_prefix, "lib", "libbz2.a")
        if os.path.exists(libbz2):
            return bzip2_prefix  # idempotent across re-runs

        bzip2_src = os.path.join(self.build_folder, "bzip2_src")
        os.makedirs(bzip2_src, exist_ok=True)
        if not os.path.exists(os.path.join(bzip2_src, "Makefile")):
            get(self,
                url="https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz",
                sha256="ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269",
                strip_root=True,
                destination=bzip2_src)

        # Build only the static library (R26: no shared lib).
        # -fPIC is required so libbz2.a can be linked into the pbzip2 binary.
        self.run(
            f'make -C {shlex.quote(bzip2_src)} -j1 '
            f'CC=clang AR=llvm-ar RANLIB=llvm-ranlib '
            f'CFLAGS="-Wall -O2 -fPIC -D_FILE_OFFSET_BITS=64" libbz2.a',
            env="conanbuildenv")

        # Install headers + static lib into prefix
        inc_dir = os.path.join(bzip2_prefix, "include")
        lib_dir = os.path.join(bzip2_prefix, "lib")
        os.makedirs(inc_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        shutil.copy(os.path.join(bzip2_src, "bzlib.h"),
                    os.path.join(inc_dir, "bzlib.h"))
        shutil.copy(os.path.join(bzip2_src, "libbz2.a"),
                    os.path.join(lib_dir, "libbz2.a"))
        return bzip2_prefix

    def package(self):
        # pbzip2 is a CLI tool — copy binary, symlinks, and man page
        copy(self, "pbzip2", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "pbzip2.1", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

        # Create symlinks pbunzip2 and pbzcat (HMDFS-compatible: rm -f && ln -s)
        bin_dir = os.path.join(self.package_folder, "bin")
        for link_name in ["pbunzip2", "pbzcat"]:
            link_path = os.path.join(bin_dir, link_name)
            if os.path.lexists(link_path):
                os.remove(link_path)
            os.symlink("pbzip2", link_path)

        # Sign ELF binary (HarmonyOS requires ELF signature for execution)
        bin_path = os.path.join(self.package_folder, "bin", "pbzip2")
        self._sign_elf(bin_path)

    def _sign_elf(self, bin_path):
        """Sign ELF binary for HarmonyOS execution (conditional on tool availability)."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.exists(sign_tool):
            # Not on OHOS worker — skip signing (CI sign.sh handles it)
            return

        # Remove old signature if present (non-fatal: section may not exist
        # on a freshly built binary that has never been signed before)
        r = subprocess.run([objcopy, "--remove-section", ".codesign", bin_path],
                           capture_output=True, timeout=10)
        if r.returncode != 0:
            self.output.warning(
                f"objcopy --remove-section .codesign returned {r.returncode} "
                f"(normal if no existing signature): "
                f"{r.stderr.decode(errors='replace').strip()}"
            )

        # Sign with self-signed certificate
        tmp = bin_path + ".signed.tmp"
        last_stderr = ""
        for _attempt in range(3):
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", bin_path,
                 "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, timeout=30)
            if r.returncode == 0 and os.path.exists(tmp):
                shutil.move(tmp, bin_path)
                break
            last_stderr = r.stderr.decode(errors='replace').strip()
            time.sleep(1)
        else:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise ConanException(
                f"ELF signing failed after 3 attempts for {bin_path}. "
                f"Binary will not be executable on HarmonyOS. "
                f"Last stderr: {last_stderr}"
            )
        os.chmod(bin_path, 0o755)

    def package_info(self):
        # pbzip2 is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # libbz2 is statically linked into the pbzip2 binary (built from
        # source in _build_bzip2), so only pthread remains a system lib.
        self.cpp_info.system_libs = ["pthread"]
