#!/usr/bin/env python3
"""Conan recipe for Reply (Perl REPL) 0.42 — Perl EUMM (ExtUtils::MakeMaker) build.

CPAN module: Reply
Author: Jesse Luehrs <doy@tozt.net> (DOY)
License: MIT

Bundles pure-Perl runtime dependencies (Module::Runtime, Try::Tiny,
Config::INI, File::HomeDir, etc.) because they are not available as
separate Conan packages on OHOS. XS-backed modules (PadWalker,
Devel::LexAlias, PerlIO::utf8_strict) are either patched to use
pure-Perl fallbacks or treated as optional.
"""
import os
import shutil
import glob
import ssl
import tarfile
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# Pure-Perl CPAN dependencies to bundle (name, url)
PERL_DEPS = [
    ("Module-Runtime-0.016",     "https://cpan.metacpan.org/authors/id/Z/ZE/ZEFRAM/Module-Runtime-0.016.tar.gz"),
    ("Try-Tiny-0.32",            "https://cpan.metacpan.org/authors/id/E/ET/ETHER/Try-Tiny-0.32.tar.gz"),
    ("Config-INI-0.025",         "https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Config-INI-0.025.tar.gz"),
    ("Config-INI-Reader-Ordered-0.022", "https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Config-INI-Reader-Ordered-0.022.tar.gz"),
    ("File-HomeDir-1.006",       "https://cpan.metacpan.org/authors/id/R/RE/REHSACK/File-HomeDir-1.006.tar.gz"),
    ("File-Which-1.27",         "https://cpan.metacpan.org/authors/id/P/PL/PLICEASE/File-Which-1.27.tar.gz"),
    ("Eval-Closure-0.14",       "https://cpan.metacpan.org/authors/id/D/DO/DOY/Eval-Closure-0.14.tar.gz"),
    ("Package-Stash-0.40",      "https://cpan.metacpan.org/authors/id/E/ET/ETHER/Package-Stash-0.40.tar.gz"),
    ("Dist-CheckConflicts-0.11","https://cpan.metacpan.org/authors/id/D/DO/DOY/Dist-CheckConflicts-0.11.tar.gz"),
    ("Module-Implementation-0.09", "https://cpan.metacpan.org/authors/id/D/DR/DROLSKY/Module-Implementation-0.09.tar.gz"),
    ("Mixin-Linewise-0.111",    "https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Mixin-Linewise-0.111.tar.gz"),
    ("Sub-Exporter-0.991",      "https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Sub-Exporter-0.991.tar.gz"),
    ("Sub-Install-0.929",       "https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Sub-Install-0.929.tar.gz"),
    ("Params-Util-1.102",       "https://cpan.metacpan.org/authors/id/R/RE/REHSACK/Params-Util-1.102.tar.gz"),
    ("Data-OptList-0.114",      "https://cpan.metacpan.org/authors/id/R/RJ/RJBS/Data-OptList-0.114.tar.gz"),
]


class PerlReplyConan(ConanFile):
    name = "perl-reply"
    version = "0.42"
    description = "read, eval, print, loop, yay! — Perl REPL interactive environment"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Reply"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _install_perl_deps(self, dest_lib):
        """Download, extract and copy .pm files from pure-Perl CPAN deps."""
        deps_dir = os.path.join(self.build_folder, "_perl_deps")
        os.makedirs(deps_dir, exist_ok=True)
        os.makedirs(dest_lib, exist_ok=True)

        for name, url in PERL_DEPS:
            tarball = os.path.join(deps_dir, f"{name}.tar.gz")
            if not os.path.exists(tarball):
                self.output.info(f"Downloading {name}...")
                subprocess.run(
                    ["curl", "-sL", url, "-o", tarball],
                    check=True, timeout=120
                )

            # Extract
            extract_dir = os.path.join(deps_dir, name)
            if not os.path.exists(extract_dir):
                with tarfile.open(tarball, "r:gz") as tar:
                    tar.extractall(deps_dir)

            # Copy .pm files from lib/ (skip t/, inc/, xt/)
            for root, dirs, files in os.walk(extract_dir):
                # Skip test/inc dirs
                parts = os.path.relpath(root, extract_dir).split(os.sep)
                if any(p in ("t", "inc", "xt", "blib") for p in parts):
                    continue
                for f in files:
                    if not f.endswith(".pm"):
                        continue
                    src_file = os.path.join(root, f)
                    rel = os.path.relpath(src_file, os.path.join(extract_dir, "lib"))
                    if rel.startswith(".." + os.sep):
                        continue
                    dst_file = os.path.join(dest_lib, rel)
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)

        self.output.info(f"Bundled {len(PERL_DEPS)} pure-Perl dependency distributions")

    def _patch_platform_issues(self, lib_dir):
        """Patch pure-Perl deps for OHOS platform compatibility."""
        readers_pm = os.path.join(lib_dir, "Mixin", "Linewise", "Readers.pm")
        if os.path.exists(readers_pm):
            self.output.info("Patching Mixin::Linewise::Readers for PerlIO::utf8_strict...")
            with open(readers_pm, "r") as f:
                content = f.read()
            # Make PerlIO::utf8_strict optional (XS module, can't load on OHOS)
            content = content.replace(
                "use PerlIO::utf8_strict;",
                "# PerlIO::utf8_strict is XS; fall back to :utf8 on platforms without it\n"
                "my $HAS_UTF8_STRICT = eval { require PerlIO::utf8_strict; 1 } ? 1 : 0;\n"
                "my $DEFAULT_BINMODE = $HAS_UTF8_STRICT ? 'utf8_strict' : 'utf8';"
            )
            # Replace only the $dflt_enc default, not the variable definition itself
            content = content.replace(
                ": 'utf8_strict';",
                ": $DEFAULT_BINMODE;"
            )
            with open(readers_pm, "w") as f:
                f.write(content)

        # Patch Eval::Closure: make Devel::LexAlias optional (XS, can't load on OHOS)
        closure_pm = os.path.join(lib_dir, "Eval", "Closure.pm")
        if os.path.exists(closure_pm):
            self.output.info("Patching Eval::Closure for Devel::LexAlias optionality...")
            with open(closure_pm, "r") as f:
                content = f.read()
            content = content.replace(
                "        require Devel::LexAlias;\n"
                "        Devel::LexAlias::lexalias($code, $_, $captures->{$_})\n"
                "            for grep substr($_, 0, 1) ne '&', @capture_keys;",
                "        if (eval { require Devel::LexAlias; 1 }) {\n"
                "            Devel::LexAlias::lexalias($code, $_, $captures->{$_})\n"
                "                for grep substr($_, 0, 1) ne '&', @capture_keys;\n"
                "        }"
            )
            with open(closure_pm, "w") as f:
                f.write(content)

        # Patch Reply::App: remove [LexicalPersistence] from default config (needs PadWalker XS)
        app_pm = os.path.join(lib_dir, "Reply", "App.pm")
        if os.path.exists(app_pm):
            self.output.info("Patching Reply::App to remove LexicalPersistence from default config...")
            with open(app_pm, "r") as f:
                content = f.read()
            content = content.replace("[LexicalPersistence]\n", "")
            # Remove [ReadLine] (Term::ReadLine hangs on OHOS with non-tty stdin)
            content = content.replace("[ReadLine]\n", "")
            # Remove [FancyPrompt] (depends on ReadLine for terminal width)
            content = content.replace("[FancyPrompt]\n", "")
            with open(app_pm, "w") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Perl EUMM build: Makefile.PL + make
        self.run(f'cd "{src}" && perl Makefile.PL INSTALLDIRS=site')
        self.run(f'cd "{src}" && make -j1')

    def package(self):
        src = self.source_folder
        # Install Reply to DESTDIR staging
        self.run(f'cd "{src}" && make install DESTDIR="{self.package_folder}"')

        # Perl install tree: data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/
        perl_base = os.path.join(self.package_folder, "data", "service", "hnp",
                                 "perl.org", "perl_5.42.0", "lib", "site_perl",
                                 "5.42.0")
        dst_lib = os.path.join(self.package_folder, "lib", "perl5")

        # Copy all .pm files preserving directory structure
        if os.path.exists(perl_base):
            for root, dirs, files in os.walk(perl_base):
                for f in files:
                    if f.endswith('.pm'):
                        src_file = os.path.join(root, f)
                        rel = os.path.relpath(src_file, perl_base)
                        dst_file = os.path.join(dst_lib, rel)
                        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                        shutil.copy2(src_file, dst_file)

        # Install pure-Perl dependencies into lib/perl5
        self._install_perl_deps(dst_lib)

        # Patch platform-specific issues in bundled deps
        self._patch_platform_issues(dst_lib)

        # Patch the reply script: set env vars for pure-Perl mode before loading modules
        src_bin = os.path.join(self.package_folder, "data", "service", "hnp",
                               "perl.org", "perl_5.42.0", "bin")
        dst_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_bin, exist_ok=True)
        if os.path.exists(src_bin):
            copy(self, "*", src_bin, dst_bin)

        # Patch reply script: self-locate lib + force pure-Perl mode (XS .so can't load on OHOS)
        reply_script = os.path.join(dst_bin, "reply")
        if os.path.exists(reply_script):
            with open(reply_script, "r") as f:
                content = f.read()
            # Insert BEGIN block after "use warnings;" for self-locating lib + env vars
            if "PERL_PARAMS_UTIL_PP" not in content:
                content = content.replace(
                    "use warnings;\n",
                    "use warnings;\n"
                    "# OHOS platform: self-locate lib + force pure-Perl mode (SELinux restricts .so loading)\n"
                    "BEGIN {\n"
                    "    use File::Basename qw(dirname);\n"
                    "    use File::Spec;\n"
                    "    unshift @INC, File::Spec->catdir(dirname(File::Spec->rel2abs(__FILE__)), '..', 'lib', 'perl5');\n"
                    "    $ENV{PERL_PARAMS_UTIL_PP} ||= 1;\n"
                    "    $ENV{PACKAGE_STASH_IMPLEMENTATION} ||= 'PP';\n"
                    "}\n"
                )
                with open(reply_script, "w") as f:
                    f.write(content)
                self.output.info("Patched reply script for OHOS platform compatibility")

        # Clean up the raw Perl install tree (keep only lib/perl5 and bin)
        raw_tree = os.path.join(self.package_folder, "data")
        if os.path.exists(raw_tree):
            shutil.rmtree(raw_tree)

    def package_info(self):
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.runenv_info.append_path("PERL5LIB",
                                     os.path.join(self.package_folder,
                                                  "lib", "perl5"))
