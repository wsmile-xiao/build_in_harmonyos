#!/usr/bin/env python3
"""Conan recipe — perl-dbd-sqlite 1.78 (auto-generated for Perl 5.42.2 rebuild)"""
import os, shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

class PerlDbdSqlite(ConanFile):
    name = "perl-dbd-sqlite"
    version = "1.78"
    description = "Perl DBI driver for SQLite"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/DBD-SQLite"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _install_dbi_from_cpan(self):
        """Download and install DBI from CPAN when not readable on CI."""
        import urllib.request, ssl, tarfile, tempfile

        install_base = os.path.join(os.path.expanduser("~"), ".local")
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        dbi_ver = "1.643"
        dbi_url = f"https://cpan.metacpan.org/authors/id/T/TI/TIMB/DBI-{dbi_ver}.tar.gz"
        dbi_tar = os.path.join(tmpdir, f"DBI-{dbi_ver}.tar.gz")
        dbi_src = os.path.join(tmpdir, f"DBI-{dbi_ver}")

        self.output.info(f"DBI not readable, downloading from {dbi_url}")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(dbi_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
            with open(dbi_tar, "wb") as f:
                f.write(resp.read())

        with tarfile.open(dbi_tar) as tar:
            tar.extractall(tmpdir)

        self.output.info(f"Building DBI {dbi_ver} to {install_base}")
        self.run(f"perl Makefile.PL INSTALL_BASE={install_base}", cwd=dbi_src)
        self.run("make -j2", cwd=dbi_src)
        self.run("make install", cwd=dbi_src)
        self.output.info("DBI installed successfully")

    def build(self):

        src = self.source_folder
        apply_conandata_patches(self)

        # Ensure DBI is available. CI workers may not have read access to
        # user-installed Perl modules (file permissions -rw-rw---- with
        # group file_manager; CI runs as a different user).
        # If DBI is not readable, download and install it from CPAN.
        dbi_pm = os.path.join(os.path.expanduser("~"),
                              "usr/local/lib/perl5/aarch64-linux/DBI.pm")
        if not os.access(dbi_pm, os.R_OK):
            self._install_dbi_from_cpan()

        # Set PERL5LIB to include user-installed Perl library paths so DBI
        # and other modules are findable.
        user_perl_libs = []
        for p in [
            os.path.join(os.path.expanduser("~"), ".local/lib/perl5/aarch64-linux"),
            os.path.join(os.path.expanduser("~"), ".local/lib/perl5"),
            os.path.join(os.path.expanduser("~"), "usr/local/lib/perl5/aarch64-linux"),
            os.path.join(os.path.expanduser("~"), "usr/local/lib/perl5"),
            os.path.join(os.path.expanduser("~"), "usr/local/lib/site_perl/5.42.0"),
        ]:
            if os.path.isdir(p):
                user_perl_libs.append(p)
        if user_perl_libs:
            existing = os.environ.get("PERL5LIB", "")
            os.environ["PERL5LIB"] = ":".join(user_perl_libs) + (":" + existing if existing else "")

        self.run("perl Makefile.PL", cwd=src)
        # HarmonyOS: patch Makefile for CRT linker flags + fix DBI paths (R32: OHOS-only)
        if self.settings.os == "OHOS":
            makefile = os.path.join(src, "Makefile")
            if os.path.exists(makefile):
                with open(makefile, "r") as mf:
                    content = mf.read()
                # Fix DBI instarch dir: patch hardcodes original install path
                # which CI workers can't read. Replace with ~/.local if needed.
                old_dbi_dir = os.path.join(os.path.expanduser("~"),
                    "usr/local/lib/perl5/site_perl/5.42.0/aarch64-linux/auto/DBI")
                if not os.access(os.path.join(old_dbi_dir, "Driver.xst"), os.R_OK):
                    new_dbi_dir = os.path.join(os.path.expanduser("~"),
                        ".local/lib/perl5/aarch64-linux/auto/DBI")
                    if os.path.isdir(new_dbi_dir):
                        content = content.replace(
                            os.path.dirname(os.path.dirname(old_dbi_dir)),
                            os.path.dirname(os.path.dirname(new_dbi_dir)))
                if "-nostartfiles" not in content:
                    content = content.replace("LDDLFLAGS =", "LDDLFLAGS = -nostartfiles -nodefaultlibs -L/system/lib64 -lc")
                with open(makefile, "w") as mf:
                    mf.write(content)
        self.run("make -j1", cwd=src)

    def package(self):
        dest = self.package_folder
        src = self.source_folder
        self.run("make install DESTDIR=" + dest, cwd=src)

        for root, dirs, files in os.walk(dest):
            for fn in files:
                if fn.endswith(".so"):
                    lib_dir = os.path.join(dest, "lib")
                    os.makedirs(lib_dir, exist_ok=True)
                    shutil.copy2(os.path.join(root, fn), lib_dir)

    def package_info(self):
        # The shared library is SQLite.so (Perl XS extension)
        self.cpp_info.libs = ["SQLite"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
