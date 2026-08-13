#!/usr/bin/env python3
"""Conan recipe for perl-params-util — Perl XS module (Makefile.PL + XS).

Build system: perl Makefile.PL + make + make install
XS module: Util.xs → Util.c → Util.so
Has pure Perl fallback (Params::Util::PP) activated via PERL_PARAMS_UTIL_PP=1.

On OHOS:
  - OHOS clang sysroot provides musl headers (sys/types.h etc.) and libc by default
  - Optional: set MUSL_PREFIX to inject extra -I/-L flags for custom musl install
  - CRT workaround: -nostartfiles -nodefaultlibs -lc
  - XS .so may fail to load at runtime due to ELF signing (pure Perl fallback works)
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlparamsutilConan(ConanFile):
    name = "perl-params-util"
    version = "1.102"
    description = "Simple, compact and correct param-checking functions (Perl XS module)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Params-Util"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        import hashlib
        import tarfile

        sources = self.conan_data["sources"]
        url = sources["url"]
        expected_sha256 = sources["sha256"]
        filename = url.split("/")[-1]

        # Download using curl — Python's urllib lacks SSL on CI
        tarball = os.path.join(self.source_folder, filename)
        self.run(f'curl -sL "{url}" -o "{tarball}"')

        # Verify SHA256
        h = hashlib.sha256()
        with open(tarball, "rb") as f:
            h.update(f.read())
        if h.hexdigest() != expected_sha256:
            raise Exception(f"SHA256 mismatch: expected {expected_sha256}, got {h.hexdigest()}")

        # Extract with strip_root (remove top-level directory)
        with tarfile.open(tarball, "r:*") as tar:
            members = tar.getmembers()
            top = members[0].name.split("/")[0]
            for m in members:
                if m.name == top:
                    continue
                m.name = m.name[len(top) + 1:]
                tar.extract(m, self.source_folder)

        # Clean up tarball
        os.remove(tarball)

    def build(self):
        # Apply conandata patches (if any)
        apply_conandata_patches(self)

        # MUSL_PREFIX is optional: on OHOS the clang sysroot already
        # provides musl headers (sys/types.h etc.) and libc in the
        # default search paths.  Local dev with a custom musl install
        # can set MUSL_PREFIX to inject extra -I/-L flags.
        musl_prefix = os.environ.get("MUSL_PREFIX", "")
        musl_inc = os.path.join(musl_prefix, "include") if musl_prefix else ""
        musl_lib = os.path.join(musl_prefix, "lib") if musl_prefix else ""

        # Step 1: Generate Makefile via Makefile.PL
        # Pass INC via Makefile.PL parameter to add musl include path to CCFLAGS
        # (avoids modifying the generated Makefile — R6 compliance)
        inc_arg = f" INC='-I{musl_inc}'" if musl_inc else ""
        self.run(f"perl Makefile.PL{inc_arg}", cwd=self.source_folder)

        # Step 2: Build with CRT workaround via make OTHERLDFLAGS
        # -nostartfiles -nodefaultlibs bypasses missing CRT files on OHOS;
        # -lc links against musl libc (found via compiler default search path,
        # or via -L{musl_lib} when MUSL_PREFIX is set).
        # Using OTHERLDFLAGS (not regex on Makefile) — R6 compliance
        other_ldflags = "-nostartfiles -nodefaultlibs"
        if musl_lib:
            other_ldflags += f" -L{musl_lib}"
        other_ldflags += " -lc"
        self.run(f'make -j1 OTHERLDFLAGS="{other_ldflags}"', cwd=self.source_folder)

    def package(self):
        # Install with DESTDIR to package folder
        dest = os.path.join(self.package_folder, "")
        self.run(f'make install DESTDIR="{dest}"', cwd=self.source_folder)

        # Also copy .so to standard lib/ for package integrity checks
        import glob
        import shutil
        so_matches = glob.glob(
            os.path.join(dest, "**", "auto", "Params", "Util", "Util.so"),
            recursive=True,
        )
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        if so_matches:
            shutil.copy2(so_matches[0], os.path.join(lib_dst, "Util.so"))
        else:
            self.output.warn("Util.so not found in install output; XS module may not be available")

    def package_info(self):
        # Perl XS module — loaded at runtime by Perl's DynaLoader,
        # not a C/C++ link library; no cpp_info declarations needed.
        pass
