#!/usr/bin/env python3
"""Conan recipe for Crypt-OpenSSL-RSA 0.33 — Perl XS module for OpenSSL RSA.

Crypt::OpenSSL::RSA is a Perl XS module providing RSA encryption, decryption,
signing, and verification using OpenSSL's libcrypto. The build system is Perl's
ExtUtils::MakeMaker (perl Makefile.PL → make → make install).

Source: Downloaded from CPAN or GitHub mirror (CI worker network restrictions
may block cpan.metacpan.org; GitHub proxy mirrors are used as fallback).

Platform adaptations for HarmonyOS:
1. CRT files missing: LDDLFLAGS patched with -nostartfiles -nodefaultlibs -lc
2. OpenSSL path: detected via pkg-config or fallback to $HOME/usr/local
3. Crypt::OpenSSL::Guess: Makefile.PL patched to not require it (uses explicit paths)

R32: settings.os must check in ("Linux", "OHOS").
R33: No hardcoded absolute paths — all paths detected at build time.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches,
    copy, save, load,
)
from conan.tools.layout import basic_layout


class CryptOpenSSLRSAConan(ConanFile):
    name = "crypt-openssl-rsa"
    version = "0.33"
    description = "Perl XS module for OpenSSL RSA encryption and signing"
    license = "perl_artistic"
    homepage = "https://metacpan.org/pod/Crypt::OpenSSL::RSA"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        # Export base64-encoded source tarball (avoids binary diff issues)
        copy(self, "Crypt-OpenSSL-RSA-0.33.tar.gz.b64",
             src=os.path.join(self.recipe_folder, "sources"),
             dst=self.export_sources_folder)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Decode base64-encoded source tarball and extract
        # (avoids CI worker network restrictions and binary diff issues)
        self.run("base64 -d Crypt-OpenSSL-RSA-0.33.tar.gz.b64 > Crypt-OpenSSL-RSA-0.33.tar.gz")
        self.run("tar xzf Crypt-OpenSSL-RSA-0.33.tar.gz --strip-components=1")

    def _detect_perl_info(self):
        try:
            perl_ver = subprocess.check_output(
                ["perl", "-e", 'print sprintf("%vd", $^V)'],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
        except Exception:
            perl_ver = "5.42.0"
        try:
            perl_arch = subprocess.check_output(
                ["perl", "-MConfig", "-e", "print $Config{archname}"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
        except Exception:
            perl_arch = "aarch64-linux"
        return perl_ver, perl_arch

    def _detect_openssl_paths(self):
        """Detect OpenSSL library and include paths, install if missing."""
        home = os.path.expanduser("~")
        openssl_lib = f"{home}/usr/local/lib"
        openssl_inc = f"{home}/usr/local/include"

        # Check if OpenSSL is already installed
        if not os.path.exists(f"{openssl_lib}/libssl.so") and not os.path.exists(f"{openssl_lib}/libssl.a"):
            # Install OpenSSL via cmd-pkgs
            self.run(
                'curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- openssl 1.1.1w'
            )

        # Try pkg-config first
        try:
            lib_dir = subprocess.check_output(
                ["pkg-config", "--libs-only-L", "openssl"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            inc_dir = subprocess.check_output(
                ["pkg-config", "--cflags-only-I", "openssl"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            if lib_dir and inc_dir:
                return lib_dir.replace("-L", "").strip(), inc_dir.replace("-I", "").strip()
        except Exception:
            pass

        return openssl_lib, openssl_inc

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        openssl_lib, openssl_inc = self._detect_openssl_paths()
        perl_ver, perl_arch = self._detect_perl_info()
        home = os.path.expanduser("~")

        # Patch Makefile.PL to remove Crypt::OpenSSL::Guess dependency
        # The CI worker doesn't have this module installed.
        # We replace the use statement and the openssl_lib_paths/openssl_inc_paths calls
        # with explicit paths passed via LIBS and INC.
        makefile_pl = os.path.join(src, "Makefile.PL")
        content = load(self, makefile_pl)
        content = content.replace(
            "use Crypt::OpenSSL::Guess qw(openssl_inc_paths openssl_lib_paths);",
            "# Crypt::OpenSSL::Guess removed - using explicit OpenSSL paths",
        )
        content = content.replace(
            "openssl_lib_paths() . ' -lssl -lcrypto'",
            f"'-L{openssl_lib} -lssl -lcrypto'",
        )
        content = content.replace(
            "openssl_inc_paths()",
            f"'-I{openssl_inc}'",
        )
        save(self, makefile_pl, content)

        env_prefix = f'LD_LIBRARY_PATH="{openssl_lib}" '

        self.run(
            f'{env_prefix}perl Makefile.PL '
            f'LIBS="-L{openssl_lib} -lssl -lcrypto" '
            f'INC="-I{openssl_inc}"',
            cwd=src,
        )

        # Fix LDDLFLAGS — HarmonyOS musl lacks standard CRT startup files
        makefile_path = os.path.join(src, "Makefile")
        content = load(self, makefile_path)
        content = content.replace(
            "LDDLFLAGS = -shared",
            "LDDLFLAGS = -shared -nostartfiles -nodefaultlibs -lc",
        )
        save(self, makefile_path, content)

        self.run(f'{env_prefix}make', cwd=src)

    def package(self):
        src = self.source_folder
        perl_ver, perl_arch = self._detect_perl_info()

        so_src = os.path.join(src, "blib", "arch", "auto", "Crypt", "OpenSSL", "RSA")
        so_dst = os.path.join(self.package_folder, "lib", "site_perl", perl_ver, perl_arch, "auto", "Crypt", "OpenSSL", "RSA")
        copy(self, "*.so", so_src, so_dst)
        copy(self, "*.bs", so_src, so_dst)
        copy(self, "*.al", so_src, so_dst)
        copy(self, "autosplit.ix", so_src, so_dst)

        pm_src = os.path.join(src, "blib", "lib", "Crypt", "OpenSSL")
        pm_dst = os.path.join(self.package_folder, "lib", "site_perl", perl_ver, "Crypt", "OpenSSL")
        copy(self, "RSA.pm", pm_src, pm_dst)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
