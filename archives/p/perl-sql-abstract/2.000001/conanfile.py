#!/usr/bin/env python3
"""Conan recipe for perl-sql-abstract 2.000001 (Perl EUMM build system).

SQL::Abstract — generate SQL from Perl data structures.
Pure Perl module, no C compilation required.
"""
import os
import subprocess
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlSqlAbstractConan(ConanFile):
    name = "perl-sql-abstract"
    version = "2.000001"
    description = "Generate SQL from Perl data structures"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/SQL-Abstract"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def _get_perl(self):
        """Find perl interpreter at runtime (no PATH dependency)."""
        # Check PERL env var
        perl_env = os.environ.get("PERL")
        if perl_env and os.path.isfile(perl_env):
            return perl_env
        # Check known OHOS locations directly
        for p in ["/data/service/hnp/bin/perl", "/usr/bin/perl", "/usr/local/bin/perl"]:
            if os.path.isfile(p):
                return p
        # Try PATH as last resort
        found = shutil.which("perl")
        if found:
            return found
        raise ConanInvalidConfiguration(
            "Perl interpreter not found. Set PERL env var or install perl."
        )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Perl runtime dependencies (not yet available as @ohpcd/stable packages):
        #   perl-moo/2.005005, perl-sub-quote/2.006009, perl-hash-merge/0.302,
        #   perl-mro-compat/0.15, perl-text-balanced/2.06
        # These are pure Perl modules installed via PERL5LIB, not Conan-managed yet.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_perl5lib(self):
        """Build PERL5LIB from Conan dependency paths + Perl's default @INC."""
        paths = []
        # Query Perl for its default library paths (@INC)
        result = subprocess.run(
            [self._get_perl(), "-e", 'print join(":", @INC)'],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            for p in result.stdout.strip().split(":"):
                if p and p != ".":
                    paths.append(p)
        existing = os.environ.get("PERL5LIB", "")
        if existing:
            paths.append(existing)
        return ":".join(paths)

    def build(self):
        # Apply patches if any (R3)
        apply_conandata_patches(self)

        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

        # Perl EUMM build: perl Makefile.PL && make
        # Do NOT set INSTALL_BASE here — it would nest with DESTDIR in package()
        build_env = dict(os.environ)
        build_env["PERL5LIB"] = self._get_perl5lib()
        build_env["PERL_MM_USE_DEFAULT"] = "1"

        src_dir = self.source_folder
        subprocess.run(
            [self._get_perl(), "Makefile.PL"],
            cwd=src_dir, env=build_env, check=True,
        )
        subprocess.run(
            ["make", "-j1"],
            cwd=src_dir, env=build_env, check=True,
        )

    def package(self):
        # Install via make install with DESTDIR staging
        # INSTALL_BASE was not set in build(), so Perl uses its default prefix.
        # DESTDIR prepends to the prefix, resulting in {package_folder}/{prefix}/lib/perl5/...
        env = dict(os.environ)
        env["PERL5LIB"] = self._get_perl5lib()
        env["PERL_MM_USE_DEFAULT"] = "1"
        subprocess.run(
            ["make", "install", f"DESTDIR={self.package_folder}"],
            cwd=self.source_folder, env=env, check=True,
        )

        # Flatten the nested install structure into package root
        # Perl installs to {DESTDIR}/{prefix}/lib/perl5/... — move .pm files to lib/
        for root, _, files in os.walk(self.package_folder):
            for f in files:
                if f.endswith(".pm") or f.endswith(".packlist") or f == "perllocal.pod":
                    src = os.path.join(root, f)
                    rel = os.path.relpath(src, self.package_folder)
                    # Find the "lib/perl5" or "lib" portion and rebase
                    if "lib/perl5/" in rel:
                        rel_after = rel[rel.index("lib/perl5/"):]
                    elif "lib/" in rel:
                        rel_after = rel[rel.index("lib/"):]
                    else:
                        continue
                    dst = os.path.join(self.package_folder, rel_after)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(src, dst)

        # Clean up empty directories left behind after flattening
        for item in os.listdir(self.package_folder):
            item_path = os.path.join(self.package_folder, item)
            if os.path.isdir(item_path) and item not in ("lib",):
                shutil.rmtree(item_path)

    def package_info(self):
        # Pure Perl module — no C libraries to link
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers — find module root directories under lib/
        # Perl module dirs start with uppercase (SQL, DBIx); internal dirs are
        # lowercase (site_perl, 5.42.0). PERL5LIB must point to the directory
        # that contains the top-level module directory.
        import glob
        perl5lib_roots = set()
        lib_dir = os.path.join(self.package_folder, "lib")
        for pm in glob.glob(os.path.join(lib_dir, "**", "*.pm"), recursive=True):
            rel = os.path.relpath(pm, lib_dir)
            parts = rel.split(os.sep)
            root_parts = []
            for part in parts[:-1]:  # skip filename
                if part and part[0].isupper():
                    break
                root_parts.append(part)
            root = os.path.join(lib_dir, *root_parts) if root_parts else lib_dir
            perl5lib_roots.add(root)
        for d in sorted(perl5lib_roots, key=len, reverse=True):
            self.runenv_info.append_path("PERL5LIB", d)
