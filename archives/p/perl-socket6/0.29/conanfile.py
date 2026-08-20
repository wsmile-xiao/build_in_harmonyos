#!/usr/bin/env python3
"""Conan recipe — perl-socket6 0.29 (Perl EUMM / XS module).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is an XS(C) module providing IPv6 socket support for Perl.

Key adaptations for OHOS:
- configure step uses bundled autotools configure (config.status HMDFS issue → manual config)
- XS link flags: -nostartfiles -nodefaultlibs -lc (missing CRT files on OHOS)
- PERL5LIB includes site_perl path for dependency resolution
- configure script needs chmod +x after extraction
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chmod
from conan.tools.layout import basic_layout


class PerlSocket6Conan(ConanFile):
    name = "perl-socket6"
    version = "0.29"
    description = "XS IPv6 socket support for Perl (Socket6 module)"
    license = "BSD-3-Clause"
    homepage = "https://metacpan.org/release/Socket6"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Ensure configure is executable
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            chmod(self, configure_path, 0o755)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        src_dir = self.source_folder
        self.output.info(f"Source folder: {src_dir}")

        # Step 1: Try running configure (may fail on config.status due to HMDFS)
        # Use subprocess to avoid Conan run() error handling issues
        configure_path = os.path.join(src_dir, "configure")
        result = subprocess.run(
            ["/bin/sh", configure_path],
            cwd=src_dir,
            env={**os.environ, "CC": "clang", "CFLAGS": "-fPIC -O2"},
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            self.output.warning(f"configure exited with code {result.returncode} (expected on HMDFS)")
            self.output.info(f"configure stderr: {result.stderr[-500:]}")

        # Check if config.pl exists; if not, create manually
        config_pl_path = os.path.join(src_dir, "config.pl")
        if not os.path.exists(config_pl_path):
            self.output.info("Creating config.pl and config.h manually (HMDFS workaround)")
            self._create_config_files(src_dir)

        # Step 2: Run Makefile.PL (patch already applied via apply_conandata_patches)
        self.run("perl Makefile.PL", cwd=src_dir)

        # Step 3: Build
        self.run("make -j1", cwd=src_dir)

    def _create_config_files(self, src_dir):
        """Manually create config.pl and config.h when autotools config.status fails on HMDFS."""
        config_pl = os.path.join(src_dir, "config.pl")
        with open(config_pl, "w") as f:
            f.write("$cc = 'clang';\n$libs = '';\n\n1;\n")

        config_h = os.path.join(src_dir, "config.h")
        with open(config_h, "w") as f:
            f.write("""/* config.h - manually generated for OHOS */
#define CAN_INET_NTOP 1
#define HAVE_GETADDRINFO 1
#define HAVE_GETHOSTBYNAME2 1
/* #undef HAVE_GETIPNODEBYADDR */
/* #undef HAVE_GETIPNODEBYNAME */
#define HAVE_GETNAMEINFO 1
#define HAVE_INET_NTOP 1
#define HAVE_INET_PTON 1
#define HAVE_PL_SV_UNDEF 1
#define HAVE_SOCKADDR_IN6_SIN6_SCOPE_ID 1
/* #undef HAVE_SOCKADDR_SA_LEN */
#define HAVE_SOCKLEN_T 1
""")

    def package(self):
        src_dir = self.source_folder
        # Install using DESTDIR pattern
        self.run(f"make install DESTDIR={self.package_folder}", cwd=src_dir)

        # Also copy .so to lib/ for G4 compatibility (Perl installs to deep site_perl tree)
        import shutil
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)

        # Find the installed .so and .pm files
        for root, dirs, files in os.walk(self.package_folder):
            for f in files:
                if f == "Socket6.so":
                    src_so = os.path.join(root, f)
                    dst_so = os.path.join(lib_dir, f)
                    if not os.path.exists(dst_so):
                        shutil.copy2(src_so, dst_so)
                        self.output.info(f"Copied {f} to lib/")
                if f == "Socket6.pm" and "site_perl" in root:
                    src_pm = os.path.join(root, f)
                    dst_pm = os.path.join(lib_dir, f)
                    if not os.path.exists(dst_pm):
                        shutil.copy2(src_pm, dst_pm)
                        self.output.info(f"Copied {f} to lib/")

    def package_info(self):
        # Perl XS module: no cpp_info.libs needed for C/C++ consumers
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("perl_module", "Socket6")
