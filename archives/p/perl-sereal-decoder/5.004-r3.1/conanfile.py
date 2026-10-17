#!/usr/bin/env python3
"""Conan recipe for perl-sereal-decoder 5.004-r3.1 (Sereal::Decoder).

XS module — Sereal binary deserialization format decoder.
Build system: ExtUtils::MakeMaker (Makefile.PL) + xsubpp + clang.
Bundled libraries: miniz, csnappy, zstd (compiled statically into .so).

OHOS adaptations:
- ELF signing: llvm-objcopy + binary-sign-tool (required for .so dlopen)
- .so runtime loading in conan cache blocked by file permission model (E046)
- test_package uses file verification + perl -c syntax check
"""
import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlSerealDecoderConan(ConanFile):
    name = "perl-sereal-decoder"
    version = "5.004-r3.1"
    description = "Sereal::Decoder - Sereal binary deserialization format decoder (XS module)"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Sereal-Decoder"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: settings.os judgment must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. Only Linux and OHOS are supported."
            )

    def source(self):
        src = self.conan_data["sources"]
        try:
            get(self, **src, strip_root=True)
        except Exception as e:
            # Fallback: git clone (bypasses Python SSL module requirement)
            # CI workers with broken Python _ssl can still use git (which has its own SSL)
            self.output.warning(f"Conan get() failed: {e}")
            self.output.info("Trying git clone fallback...")
            urls = src.get("url", [])
            if isinstance(urls, str):
                urls = [urls]
            for url in urls:
                # Strip mirror proxy prefix to get original GitHub URL
                clean_url = url
                for prefix in ("https://gh-proxy.com/", "https://ghfast.com/"):
                    if clean_url.startswith(prefix):
                        clean_url = clean_url[len(prefix):]
                        break
                match = re.match(
                    r'https://github\.com/([^/]+/[^/]+)/archive/refs/tags/(.+)\.tar\.gz',
                    clean_url
                )
                if match:
                    repo, tag = match.groups()
                    git_url = f"https://github.com/{repo}.git"
                    self.run(f'git clone --depth 1 --branch "{tag}" "{git_url}" .')
                    shutil.rmtree(os.path.join(self.source_folder, ".git"),
                                  ignore_errors=True)
                    self.output.info(f"Source downloaded via git clone (tag: {tag})")
                    return
            raise

    def generate(self):
        # XS module: no autotools configure, just perl Makefile.PL
        pass

    def build(self):
        apply_conandata_patches(self)

        # GitHub archive structure: Perl/Decoder/ (build) + Perl/shared/ (headers/tools)
        # Makefile.PL requires inc/Sereal/BuildTools.pm which lives in Perl/shared/inc/
        # Copy shared files into Decoder dir (simulates link_files() for in-repo builds,
        # but uses copy instead of symlink for OHOS HMDFS compatibility)
        decoder_dir = os.path.join(self.source_folder, "Perl", "Decoder")
        shared_dir = os.path.join(self.source_folder, "Perl", "shared")
        for item in os.listdir(shared_dir):
            src = os.path.join(shared_dir, item)
            dst = os.path.join(decoder_dir, item)
            if not os.path.exists(dst):
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

        # XS module build: perl Makefile.PL → xsubpp → clang → .so
        # Env vars to skip interactive prompts and use bundled libs:
        #   USE_UNALIGNED=1 - enable unaligned loads for performance
        #   NO_ASM=1 - disable assembly in bundled zstd (cross-compile safe)
        #   CPAN_COMPAT=1 - skip prompts in CPAN mode
        #   SEREAL_USE_BUNDLED_LIBS=1 - skip Devel::CheckLib probes (avoids hang on OHOS)
        os.environ["USE_UNALIGNED"] = "1"
        os.environ["NO_ASM"] = "1"
        os.environ["CPAN_COMPAT"] = "1"
        os.environ["SEREAL_USE_BUNDLED_LIBS"] = "1"

        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=decoder_dir)
        # E074: HarmonyOS SELinux forbids FIFO, use -j1
        self.run("make -j1", cwd=decoder_dir)

    def package(self):
        decoder_dir = os.path.join(self.source_folder, "Perl", "Decoder")

        # Install to package folder directly via DESTDIR
        self.run(f'make install DESTDIR="{self.package_folder}"',
                 cwd=decoder_dir)

        # Create lib/ with signed .so copy for G4 artifact check + consumers
        lib_out = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_out, exist_ok=True)

        so_files = glob.glob(
            os.path.join(self.package_folder, "**", "*.so"), recursive=True
        )

        # Sign ELF .so files for HarmonyOS (P-SIGN-001)
        # musl dynamic linker checks .codesign section; unsigned .so = Permission denied
        for so_file in so_files:
            self.output.info(f"Processing ELF signing for {os.path.basename(so_file)}")
            # Remove old .codesign section if present (non-fatal if section doesn't exist)
            has_codesign = False
            try:
                result = subprocess.run(
                    ["llvm-readelf", "-S", so_file],
                    capture_output=True, text=True, check=True
                )
                has_codesign = ".codesign" in result.stdout
            except (FileNotFoundError, subprocess.CalledProcessError):
                self.output.warning(f"llvm-readelf failed for {so_file}, skipping codesign check")
            if has_codesign:
                self.run(f'llvm-objcopy --remove-section .codesign "{so_file}"',
                         cwd=decoder_dir)
            # Self-sign the .so for HarmonyOS
            self.run(f'binary-sign-tool sign -inFile "{so_file}" '
                     f'-outFile "{so_file}" -selfSign 1',
                     cwd=decoder_dir)
            # Copy signed .so to lib/ for standard artifact discovery
            shutil.copy2(so_file, os.path.join(lib_out, os.path.basename(so_file)))

    def package_info(self):
        # XS module: .so is loaded by Perl's XSLoader/DynaLoader
        self.cpp_info.libs = []
        perl_arch = "aarch64-linux" if str(self.settings.arch) in ("armv8", "aarch64") else "x86_64-linux"
        perl_ver = "5.42.2"
        lib_base = os.path.join(
            "data", "service", "hnp", "perl.org", f"perl_{perl_ver}",
            "lib", "site_perl", perl_ver, perl_arch
        )
        # Set libdirs to the .so directory for G4 artifact check
        self.cpp_info.libdirs = [os.path.join(lib_base, "auto", "Sereal", "Decoder")]
        # Set PERL5LIB for runtime usage — must use absolute path via package_folder
        perllib = os.path.join(self.package_folder, lib_base)
        self.runenv_info.define("PERL5LIB", perllib)
