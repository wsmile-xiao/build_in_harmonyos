#!/usr/bin/env python3
"""Conan recipe — Perl EUMM (ExtUtils::MakeMaker) module.
ExtUtils-CppGuess 0.27 — Guess C++ compiler and flags compatible with
the C compiler that your Perl was built with.

Pure Perl module, no C/C++ compilation.
Build dependency: Capture::Tiny (downloaded and installed during build if missing).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ExtUtilsCppGuessConan(ConanFile):
    name = "extutils-cppguess"
    version = "0.27"
    description = "Guess C++ compiler and flags compatible with the C compiler that your Perl was built with"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/pod/ExtUtils::CppGuess"
    url = ""

    # Pure Perl module — only os and arch matter
    settings = "os", "arch"

    _capture_tiny_lib = None

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_capture_tiny(self):
        """Download and install Capture::Tiny if not already available."""
        # Use self.run with a no-op check (catch failure via try/except)
        try:
            self.run("perl -MCapture::Tiny -e 'exit 0'", env="conanrun", quiet=True)
            return  # Already available
        except Exception:
            pass  # Capture::Tiny not installed, proceed to install

        capture_tiny_url = (
            "https://cpan.metacpan.org/authors/id/D/DA/DAGOLDEN/Capture-Tiny-0.48.tar.gz"
        )
        tmp_dir = os.path.join(self.build_folder, "_capture_tiny")
        os.makedirs(tmp_dir, exist_ok=True)

        self.run(
            'cd "{}" && curl -k -L "{}" -o Capture-Tiny.tar.gz && '
            "tar -xzf Capture-Tiny.tar.gz".format(tmp_dir, capture_tiny_url),
            env="conanrun",
        )
        ct_src = os.path.join(tmp_dir, "Capture-Tiny-0.48")
        ct_install = os.path.join(tmp_dir, "perl5lib")
        self.run(
            'cd "{}" && perl Makefile.PL INSTALL_BASE="{}" && make && '
            'make install INSTALL_BASE="{}"'.format(ct_src, ct_install, ct_install),
            env="conanrun",
        )
        self._capture_tiny_lib = os.path.join(ct_install, "lib", "perl5")

    def _perl_env_prefix(self):
        """Return PERL5LIB export prefix for commands, or empty string."""
        if self._capture_tiny_lib:
            current = os.environ.get("PERL5LIB", "")
            perl5lib = self._capture_tiny_lib + (":" + current if current else "")
            return 'PERL5LIB="{}" '.format(perl5lib)
        return ""

    def build(self):
        apply_conandata_patches(self)
        self._ensure_capture_tiny()
        prefix = self._perl_env_prefix()
        # Pure Perl module using ExtUtils::MakeMaker
        self.run("{}perl Makefile.PL INSTALLDIRS=site".format(prefix), env="conanrun")
        self.run("{}make -j1".format(prefix), env="conanrun")

    def package(self):
        prefix = self._perl_env_prefix()
        # Install to package folder using DESTDIR
        self.run('{}make install DESTDIR="{}"'.format(prefix, self.package_folder), env="conanrun")
        # Copy .pm files to standard lib/ for Conan artifact detection (G4)
        for root, dirs, files in os.walk(self.package_folder):
            for f in files:
                if f.endswith(".pm"):
                    rel = os.path.relpath(os.path.join(root, f), self.package_folder)
                    parts = rel.split(os.sep)
                    for i, part in enumerate(parts):
                        if part == "ExtUtils":
                            new_rel = os.path.join(*parts[i:])
                            dst = os.path.join(self.package_folder, "lib", new_rel)
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                            if not os.path.exists(dst):
                                shutil.copy2(os.path.join(root, f), dst)
                            break

    def package_info(self):
        # Pure Perl module - no C/C++ libraries
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
