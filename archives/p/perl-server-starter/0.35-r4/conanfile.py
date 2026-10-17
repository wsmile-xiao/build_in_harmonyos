#!/usr/bin/env python3
"""Conan recipe for perl-server-starter 0.35-r4

A superdaemon for hot-deploying server programs (Server::Starter).
Pure Perl module — no C compilation required.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlServerStarterConan(ConanFile):
    name = "perl-server-starter"
    version = "0.35-r4"
    description = "A superdaemon for hot-deploying server programs (Server::Starter)"
    license = "perl_5"
    homepage = "https://github.com/kazuho/p5-Server-Starter"
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

    def build(self):
        # R32: Platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        apply_conandata_patches(self)
        # Source ships Build.PL (Module::Build) but Module::Build is not available.
        # Generate Makefile.PL for ExtUtils::MakeMaker (R6: only source files)
        work_dir = self.source_folder
        makefile_pl = os.path.join(work_dir, "Makefile.PL")
        if not os.path.exists(makefile_pl):
            content = (
                "use 5.008;\nuse strict;\nuse warnings;\nuse ExtUtils::MakeMaker;\n\n"
                "WriteMakefile(\n"
                "    NAME         => 'Server::Starter',\n"
                "    VERSION_FROM => 'lib/Server/Starter.pm',\n"
                "    ABSTRACT     => 'a superdaemon for hot-deploying server programs',\n"
                "    AUTHOR       => 'Kazuho Oku',\n"
                "    LICENSE      => 'perl_5',\n"
                "    PREREQ_PM    => { 'perl' => '5.008' },\n"
                "    EXE_FILES    => [glob('script/*')],\n"
                ");\n"
            )
            with open(makefile_pl, "w") as f:
                f.write(content)
        # Pure Perl module: use Makefile.PL + ExtUtils::MakeMaker
        self.run("perl Makefile.PL", cwd=work_dir)
        self.run("make -j2", cwd=work_dir)

    def package(self):
        work_dir = self.source_folder
        pkg = self.package_folder

        # Install to staging area via DESTDIR
        self.run(f'make install DESTDIR="{pkg}"', cwd=work_dir)

        # Perl install tree: data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/
        perl_base = os.path.join(pkg, "data", "service", "hnp",
                                 "perl.org", "perl_5.42.0", "lib", "site_perl",
                                 "5.42.0")
        dst_lib = os.path.join(pkg, "lib", "perl5")

        # Copy all .pm files preserving directory structure (R21: product integrity)
        if os.path.exists(perl_base):
            for root, dirs, files in os.walk(perl_base):
                for f in files:
                    if f.endswith('.pm'):
                        src_file = os.path.join(root, f)
                        rel = os.path.relpath(src_file, perl_base)
                        dst_file = os.path.join(dst_lib, rel)
                        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                        shutil.copy2(src_file, dst_file)
            self.output.info(f"Copied .pm files to {dst_lib}")

        # Copy start_server script to bin/
        src_bin = os.path.join(pkg, "data", "service", "hnp",
                               "perl.org", "perl_5.42.0", "bin")
        dst_bin = os.path.join(pkg, "bin")
        os.makedirs(dst_bin, exist_ok=True)
        if os.path.exists(src_bin):
            copy(self, "*", src_bin, dst_bin)
            self.output.info(f"Copied scripts to {dst_bin}")

        # Patch start_server to self-locate lib/perl5 for module loading
        start_server = os.path.join(dst_bin, "start_server")
        if os.path.exists(start_server):
            with open(start_server, "r") as f:
                content = f.read()
            if "self-locate" not in content:
                # Insert BEGIN block after the shebang line
                lines = content.split("\n")
                new_lines = [lines[0]]  # keep shebang
                new_lines.append("")
                new_lines.append("# Self-locate lib/perl5 for module loading on OHOS")
                new_lines.append("BEGIN {")
                new_lines.append("    use File::Basename qw(dirname);")
                new_lines.append("    use File::Spec;")
                new_lines.append("    unshift @INC, File::Spec->catdir(")
                new_lines.append("        dirname(File::Spec->rel2abs(__FILE__)),")
                new_lines.append("        '..', 'lib', 'perl5'")
                new_lines.append("    );")
                new_lines.append("}")
                new_lines.extend(lines[1:])
                with open(start_server, "w") as f:
                    f.write("\n".join(new_lines))
                os.chmod(start_server, 0o755)
                self.output.info("Patched start_server for self-locating lib")

        # Clean up the raw Perl install tree (keep only lib/perl5 and bin)
        raw_tree = os.path.join(pkg, "data")
        if os.path.exists(raw_tree):
            shutil.rmtree(raw_tree)
            self.output.info("Cleaned up raw Perl install tree")

    def package_info(self):
        # Pure Perl module: no C libraries (R27)
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # Set PERL5LIB to the package's site_perl path (R28, R29)
        self.runenv_info.append_path("PERL5LIB",
                                     os.path.join(self.package_folder,
                                                  "lib", "perl5"))
        # Add bin/ to PATH so start_server is callable from test_package
        # prepend to ensure package's start_server takes precedence over any system-installed one
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))
