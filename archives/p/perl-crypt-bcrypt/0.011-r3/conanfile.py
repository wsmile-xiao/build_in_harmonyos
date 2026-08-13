#!/usr/bin/env python3
"""Conan recipe — Crypt::Bcrypt (Perl XS module).

Crypt::Bcrypt is a modern bcrypt implementation for Perl.
It uses ExtUtils::MakeMaker (Makefile.PL) and includes a C XS extension
(Bcrypt.xs → Bcrypt.c) plus the crypt_blowfish C library.

Build: perl Makefile.PL → make → make install
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class PerlCryptBcryptConan(ConanFile):
    name = "perl-crypt-bcrypt"
    version = "0.011-r3"
    description = "A modern bcrypt implementation for Perl (XS module)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://github.com/Leont/crypt-bcrypt"
    url = ""  # CI fills this

    # XS module compiles C code — needs compiler/build_type
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: Only configure build env on Linux/OHOS
        if self.settings.os in ("Linux", "OHOS"):
            env = Environment()
            # Auto-detect OHOS SDK path from standard installation directory.
            # Scans /data/service/hnp/ohos-sdk.org/ for installed SDK versions.
            sdk_base = "/data/service/hnp/ohos-sdk.org"
            sdk_dirs = sorted(
                d for d in os.listdir(sdk_base) if d.startswith("ohos-sdk_")
            ) if os.path.isdir(sdk_base) else []
            if sdk_dirs:
                sdk_root = os.path.join(sdk_base, sdk_dirs[-1], "ohos/native")
                sysroot = os.path.join(sdk_root, "sysroot/usr")
                llvm_lib = os.path.join(sdk_root, "llvm/lib/aarch64-linux-ohos")
                c_include = f"{sysroot}/include:{sysroot}/include/aarch64-linux-ohos"
                library_path = f"{sysroot}/lib/aarch64-linux-ohos:{llvm_lib}"
                env.define("C_INCLUDE_PATH", c_include)
                env.define("LIBRARY_PATH", library_path)
                self.output.info(f"Configuring Perl XS build environment for {self.settings.os}")
                self.output.info(f"  SDK: {sdk_root}")
                self.output.info(f"  C_INCLUDE_PATH: {c_include}")
                self.output.info(f"  LIBRARY_PATH: {library_path}")
            else:
                self.output.warning(f"OHOS SDK not found at {sdk_base}, skipping env setup")
            env.vars(self).save_script("perl_bcrypt_env")

    def build(self):
        # Apply patches if any
        apply_conandata_patches(self)
        # Build env list: perl_bcrypt_env only exists on Linux/OHOS
        env_list = ["conanbuild", "perl_bcrypt_env"] if self.settings.os in ("Linux", "OHOS") else ["conanbuild"]
        # Perl XS module: use Makefile.PL (ExtUtils::MakeMaker)
        self.run("perl Makefile.PL", cwd=self.source_folder, env=env_list)
        self.run("make -j1", cwd=self.source_folder, env=env_list)
        # Create static library from pure C object (no Perl XS dependencies)
        self.run("ar rcs libcrypt_blowfish.a crypt_blowfish.o", cwd=self.source_folder, env=env_list)

    def package(self):
        # Build env list: perl_bcrypt_env only exists on Linux/OHOS
        env_list = ["conanbuild", "perl_bcrypt_env"] if self.settings.os in ("Linux", "OHOS") else ["conanbuild"]
        # Install to a temporary DESTDIR
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run("make install DESTDIR={}".format(dest_dir), cwd=self.source_folder, env=env_list)

        # Find and copy the compiled .so (XS shared library)
        so_files = glob.glob(os.path.join(dest_dir, "**", "auto", "Crypt", "Bcrypt", "Bcrypt.so"), recursive=True)
        if so_files:
            # Copy to Perl autoload path for Perl DynaLoader
            perl_target = os.path.join(self.package_folder, "lib", "perl5", "auto", "Crypt", "Bcrypt")
            os.makedirs(perl_target, exist_ok=True)
            shutil.copy2(so_files[0], perl_target)

        # Copy static C library for C consumers (pure C, no Perl XS deps)
        static_lib = os.path.join(self.source_folder, "libcrypt_blowfish.a")
        if os.path.exists(static_lib):
            lib_dir = os.path.join(self.package_folder, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            shutil.copy2(static_lib, lib_dir)

        # Find and copy the .pm (Perl module file)
        pm_files = glob.glob(os.path.join(dest_dir, "**", "Crypt", "Bcrypt.pm"), recursive=True)
        if pm_files:
            target_dir = os.path.join(self.package_folder, "lib", "perl5", "Crypt")
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(pm_files[0], target_dir)

        # Copy the C header for direct C usage
        header_src = os.path.join(self.source_folder, "crypt_blowfish.h")
        if os.path.exists(header_src):
            inc_dir = os.path.join(self.package_folder, "include")
            os.makedirs(inc_dir, exist_ok=True)
            shutil.copy2(header_src, inc_dir)

    def package_info(self):
        # C library interface (crypt_blowfish functions in libcrypt_blowfish.a)
        self.cpp_info.set_property("cmake_file_name", "CryptBcrypt")
        self.cpp_info.set_property("cmake_target_name", "CryptBcrypt::CryptBcrypt")
        self.cpp_info.libs = ["crypt_blowfish"]
        self.cpp_info.libdirs = ["lib"]
        # Set PERL5LIB for consumers at runtime
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
