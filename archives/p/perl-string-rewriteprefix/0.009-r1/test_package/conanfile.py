#!/usr/bin/env python3
"""Conan test_package — perl-string-rewriteprefix 0.009-r1 (pure Perl module).

Perl-based functional test: verifies String::RewritePrefix works correctly
on OHOS by running test.pl which exercises the core rewrite API.
"""
import os

from conan import ConanFile


class PerlStringRewriteprefixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _install_perl_deps(self):
        """Install pure Perl dependencies (Sub::Exporter chain) to system PERL5LIB."""
        import urllib.request, tarfile, io, os, shutil

        perl_lib = "/storage/Users/currentUser/usr/local/perl5/lib/perl5"

        if os.path.isfile(os.path.join(perl_lib, "Sub", "Exporter.pm")):
            return

        deps = [
            ("https://cpan.metacpan.org/authors/id/R/RE/REHSACK/Params-Util-1.102.tar.gz",
             "Params-Util-1.102"),
            ("https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Sub-Install-0.928.tar.gz",
             "Sub-Install-0.928"),
            ("https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Data-OptList-0.110.tar.gz",
             "Data-OptList-0.110"),
            ("https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Sub-Exporter-0.988.tar.gz",
             "Sub-Exporter-0.988"),
        ]

        tmp_dir = os.path.join(os.environ.get("TMPDIR", "/tmp"), "perl_deps_install")

        for url, dirname in deps:
            self.output.info(f"Downloading {dirname} from CPAN...")
            response = urllib.request.urlopen(url, timeout=60)
            data = response.read()

            tar = tarfile.open(fileobj=io.BytesIO(data), mode='r:gz')
            tar.extractall(tmp_dir)
            tar.close()

            lib_dir = os.path.join(tmp_dir, dirname, "lib")
            if os.path.isdir(lib_dir):
                for root, dirs, files in os.walk(lib_dir):
                    for f in files:
                        if f.endswith('.pm'):
                            src = os.path.join(root, f)
                            rel = os.path.relpath(src, lib_dir)
                            dest = os.path.join(perl_lib, rel)
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            shutil.copy2(src, dest)
                            self.output.info(f"  Installed: {rel}")

    def build(self):
        self._install_perl_deps()

    def test(self):
        # Run the Perl-based functional test
        test_script = os.path.join(self.source_folder, "test.pl")

        # Build PERL5LIB: system paths + conan package path
        perl5lib = (
            "/storage/Users/currentUser/usr/local/perl5/lib/perl5:"
            "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux:"
            "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"
        )

        # Add the conan package's Perl lib path (Conan 2 API)
        try:
            dep = self.dependencies["perl-string-rewriteprefix"]
            pkg_folder = str(dep.package_folder)
            pkg_perl_lib = os.path.join(
                pkg_folder,
                "data", "service", "hnp", "perl.org",
                "perl_5.42.0", "lib", "site_perl", "5.42.0"
            )
            if os.path.isdir(pkg_perl_lib):
                perl5lib = pkg_perl_lib + ":" + perl5lib
        except (KeyError, AttributeError):
            pass  # Package not yet resolved — fall back to system Perl paths

        # Use shell inline env vars (Conan 2 env=list doesn't always work)
        cmd = (
            'PERL_PARAMS_UTIL_PP=1 '
            'PERL5LIB="{}" '
            'perl {}'
        ).format(perl5lib, test_script)

        self.run(cmd)
