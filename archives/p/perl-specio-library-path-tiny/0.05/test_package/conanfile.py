#!/usr/bin/env python3
"""Conan test_package — perl-specio-library-path-tiny 0.05

Tests that Specio::Library::Path::Tiny can be loaded and used to
declare Path::Tiny type constraints (Path, AbsPath, RealPath, File,
AbsFile, RealFile, Dir, AbsDir, RealDir).
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlSpecioLibraryPathTinyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _ensure_perl_deps(self):
        """Install Perl runtime deps (Path::Tiny, Specio + deps) from CPAN.

        These modules are not available on CI workers. Download and install
        them to a local lib directory so the load test can run.
        Returns list of PERL5LIB paths, or empty list if already available.
        """
        import shutil

        # Find bash (not always in PATH inside Conan test env)
        bash = shutil.which("bash") or os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"

        # Find perl
        perl = shutil.which("perl") or "perl"

        # Check if deps are already available from system paths
        try:
            result = subprocess.run(
                [perl, "-e",
                 'eval { require Path::Tiny; require Specio; print "DEPS_OK" }'],
                capture_output=True, text=True, timeout=10,
                env={**os.environ, "SPECIO_IMPLEMENTATION": "PP"},
            )
            if "DEPS_OK" in result.stdout:
                self.output.info("Perl deps (Path::Tiny, Specio) already available from system")
                return []
        except Exception:
            pass

        # Install to local lib
        perl_lib = os.path.join(os.environ.get("TMPDIR", "/tmp"), "perl-cpan-libs")
        local_perl5 = os.path.join(perl_lib, "lib", "perl5")
        local_arch = os.path.join(local_perl5, "aarch64-linux")

        # If already installed (cached), just return paths
        if os.path.isfile(os.path.join(local_perl5, "Specio.pm")):
            self.output.info("Perl deps already installed in local cache")
            return [local_perl5, local_arch]

        # Run install script
        script = os.path.join(self.source_folder, "install_perl_deps.sh")
        self.output.info("Installing Perl deps from CPAN...")
        result = subprocess.run(
            [bash, script, perl_lib],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            self.output.warning(f"Perl dep install failed: {result.stderr[-500:]}")
            return []

        # Script outputs ONLY the PERL5LIB paths on the last stdout line
        lines = result.stdout.strip().splitlines()
        last_line = lines[-1] if lines else ""
        paths = last_line.split(":") if last_line else []
        if paths:
            self.output.info(f"Perl deps installed to {paths[0]}")
        return paths

    def _get_perl5lib(self, pkg_folder):
        """Build PERL5LIB from package lib + system Perl paths."""
        parts = []
        # Package lib
        for site_lib in glob.glob(os.path.join(pkg_folder, "lib", "perl5", "site_perl", "*")):
            if os.path.isdir(site_lib):
                parts.append(site_lib)
                break
        base_perl = os.path.join(pkg_folder, "lib", "perl5")
        if os.path.isdir(base_perl):
            parts.append(base_perl)
        # System Perl paths for runtime dependencies
        for sys_path in [
            "/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0",
            "/storage/Users/currentUser/usr/local/lib/perl5",
            "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0",
        ]:
            if os.path.isdir(sys_path):
                parts.append(sys_path)
        existing = os.environ.get("PERL5LIB", "")
        if existing:
            parts.append(existing)
        return ":".join(parts)

    def test(self):
        # Find Tiny.pm in the package folder
        pkg = self.dependencies["perl-specio-library-path-tiny"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Tiny.pm"), recursive=True)
        if not pm_files:
            raise Exception("Specio/Library/Path/Tiny.pm not found in package")
        self.output.info(f"Found Tiny.pm: {pm_files[0]}")

        # Verify version in .pm file
        with open(pm_files[0]) as f:
            content = f.read()
        if "0.05" not in content:
            raise Exception("Version 0.05 not found in Tiny.pm")
        self.output.info("Version 0.05 verified in Tiny.pm content")

        # Check for Path::Tiny reference
        if "Path::Tiny" in content:
            self.output.info("Path::Tiny reference found in module")
        if "Specio" in content:
            self.output.info("Specio reference found in module")

        # Ensure Perl runtime deps (Path::Tiny, Specio) are available
        dep_paths = self._ensure_perl_deps()

        # Set up PERL5LIB — use os.environ directly (env= param not reliable in test_package)
        perl5lib = self._get_perl5lib(pkg_folder)
        # Prepend CPAN-installed deps so they take priority
        if dep_paths:
            perl5lib = ":".join(dep_paths) + ":" + perl5lib
        self.output.info(f"PERL5LIB={perl5lib}")
        os.environ["PERL5LIB"] = perl5lib
        os.environ["SPECIO_IMPLEMENTATION"] = "PP"

        # Test 1: Load module
        self.run(
            'perl -MSpecio::Library::Path::Tiny -e '
            '"print qq{Specio::Library::Path::Tiny loaded OK\n}"',
        )
        self.output.success("Module loaded successfully")

        # Test 2: Check version
        self.run(
            'perl -MSpecio::Library::Path::Tiny -e '
            '"print qq{VERSION=$Specio::Library::Path::Tiny::VERSION\n}"',
        )
        self.output.info("Version check completed")

        # Test 3: Run consumer-perspective Perl test script
        test_script = os.path.join(self.source_folder, "test_specio_library_path_tiny.pl")
        self.run(f'perl "{test_script}"')

        self.output.info("perl-specio-library-path-tiny 0.05 package structure verified OK")
