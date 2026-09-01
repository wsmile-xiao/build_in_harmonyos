#!/usr/bin/env python3
"""Conan recipe for Crypt::Eksblowfish (Perl XS module with ExtUtils::MakeMaker).

Crypt::Eksblowfish implements the Eksblowfish block cipher (used by bcrypt).
This is a Perl XS module built with ExtUtils::MakeMaker (Makefile.PL), containing
compiled C code (Eksblowfish.xs -> Eksblowfish.so).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
The .so is loaded by Perl XSLoader/DynaLoader at runtime.

Adaptations for OHOS:
- CPATH/LIBRARY_PATH set to OHOS SDK sysroot for musl headers
- PERL5LIB set to user-installed Perl module path
- Makefile.PL patched to replace Module::Build passthrough with standalone
  ExtUtils::MakeMaker version; cleans -fstack-protector-strong from ldflags (E137)
- Perl paths (sitelib, archname, sitearch) obtained dynamically via perl -V
  to avoid hardcoding version-specific paths (e.g. 5.42.2, aarch64-linux)
- R32: settings.os check uses in ("Linux", "OHOS")
- R33: build environment via Conan buildenv_info, not raw os.environ
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlCryptEksblowfishConan(ConanFile):
    name = "perl-crypt-eksblowfish"
    version = "0.009-r16"
    description = "Eksblowfish block cipher (Perl XS module, used by bcrypt)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/Crypt-Eksblowfish"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_perl_config(self):
        """Get Perl configuration paths dynamically using perl -V."""
        perl_bin = shutil.which("perl")
        if not perl_bin:
            for c in [os.path.join(os.path.expanduser("~"), "usr", "local", "bin", "perl"),
                      "/storage/Users/currentUser/usr/local/bin/perl", "/usr/bin/perl"]:
                if os.path.isfile(c) and os.access(c, os.X_OK):
                    perl_bin = c
                    break
        if not perl_bin:
            self.output.warning("perl not found, using fallback config")
            return {"sitelib": "", "archname": "aarch64-linux", "sitearch": "", "version": ""}
        result = subprocess.run(
            [perl_bin, "-V:sitelib", "-V:archname", "-V:sitearch", "-V:version"],
            capture_output=True, text=True, timeout=30
        )
        config = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if "=" in line:
                key, _, val = line.partition("=")
                config[key.strip()] = val.strip().rstrip(";").strip("'\"")
        if not config.get("sitelib"):
            config["sitelib"] = ""
        if not config.get("archname"):
            config["archname"] = "aarch64-linux"
        if not config.get("sitearch"):
            config["sitearch"] = ""
        if not config.get("version"):
            config["version"] = ""
        return config

    def _resolve_sysroot(self):
        sysroot = os.environ.get("OHOS_SYSROOT")
        if sysroot and os.path.isdir(sysroot):
            return sysroot
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot",
            os.path.expanduser("~/ohos-sdk/sysroot"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        raise ConanException("Cannot find OHOS SDK sysroot. Set OHOS_SYSROOT.")

    def _resolve_perl_lib(self):
        perl_lib = os.environ.get("PERL5LIB")
        if perl_lib:
            return perl_lib
        perl_config = self._get_perl_config()
        candidates = []
        sitelib = perl_config.get("sitelib", "")
        if sitelib:
            candidates.append(sitelib)
        sitearch = perl_config.get("sitearch", "")
        if sitearch and sitearch != sitelib:
            candidates.append(sitearch)
        home = os.path.expanduser("~")
        home_perl = os.path.join(home, "usr", "local", "lib", "perl5")
        if os.path.isdir(home_perl):
            candidates.append(home_perl)
        archname = perl_config.get("archname", "")
        if archname:
            home_perl_arch = os.path.join(home_perl, archname)
            if os.path.isdir(home_perl_arch):
                candidates.append(home_perl_arch)
        if sitelib:
            system_base = os.path.dirname(sitelib)
            if system_base and os.path.isdir(system_base):
                candidates.append(system_base)
        existing = [c for c in candidates if os.path.isdir(c)]
        return ":".join(existing) if existing else ""

    def generate(self):
        sysroot = self._resolve_sysroot()
        perl_lib = self._resolve_perl_lib()
        cpath = os.path.join(sysroot, "usr", "include")
        self.buildenv_info.define("CPATH", cpath)
        lib_path = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
        self.buildenv_info.define("LIBRARY_PATH", lib_path)
        sdk_native = os.path.dirname(os.path.normpath(sysroot))
        llvm_lib = os.path.join(sdk_native, "llvm", "lib")
        if os.path.isdir(llvm_lib):
            self.buildenv_info.define("LD_LIBRARY_PATH", llvm_lib)
        if perl_lib:
            self.buildenv_info.define("PERL5LIB", perl_lib)

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        perl_config = self._get_perl_config()
        archname = perl_config.get("archname", "aarch64-linux")
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")
        arch_lib_dir = os.path.join("lib", "perl5", archname)
        copy(self, "Eksblowfish.so",
             src=os.path.join(blib_arch, "auto", "Crypt", "Eksblowfish"),
             dst=os.path.join(pkg, arch_lib_dir, "auto", "Crypt", "Eksblowfish"))
        copy(self, "Eksblowfish.bs",
             src=os.path.join(blib_arch, "auto", "Crypt", "Eksblowfish"),
             dst=os.path.join(pkg, arch_lib_dir, "auto", "Crypt", "Eksblowfish"))
        copy(self, "Eksblowfish.pm",
             src=os.path.join(blib_lib, "Crypt"),
             dst=os.path.join(pkg, arch_lib_dir, "Crypt"))
        copy(self, "*.pm",
             src=os.path.join(blib_lib, "Crypt", "Eksblowfish"),
             dst=os.path.join(pkg, arch_lib_dir, "Crypt", "Eksblowfish"))

    def package_info(self):
        perl_config = self._get_perl_config()
        archname = perl_config.get("archname", "aarch64-linux")
        self.cpp_info.libs = []
        self.cpp_info.libdirs = [f"lib/perl5/{archname}/auto/Crypt/Eksblowfish"]
        self.cpp_info.includedirs = []
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        perl_arch_lib = os.path.join(self.package_folder, "lib", "perl5", archname)
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.runenv_info.append_path("PERL5LIB", perl_arch_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_arch_lib)
