#!/usr/bin/env python3
"""Conan recipe for arename v4.1 — Perl audio file renaming tool.

arename is a Perl script tool that renames audio files based on tag information.
Build: make genperlscripts PERL=... (generates scripts from .in templates)
Package: direct file copy (avoids install.sh exec issues on OHOS)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file


class ArenameConan(ConanFile):
    name = "arename"
    version = "4.1"
    description = "Automatically rename audio files by tagging information"
    license = "BSD-2-Clause"
    homepage = "https://github.com/ft/arename"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: Platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        apply_conandata_patches(self)

        # E165 workaround: Fix gps script to call getversion.sh via sh explicitly
        # (Perl's exec fails on OHOS when trying to exec scripts with shebangs
        #  in the Conan build directory due to SELinux policy)
        replace_in_file(self, "bin/gps",
            "q{./bin/getversion.sh build |}",
            "q{sh ./bin/getversion.sh build |}")

        # R33: Do not depend on undefined shell environment variables
        perl_bin = "/data/service/hnp/bin/perl"
        if not os.path.isfile(perl_bin):
            for candidate in ["/usr/bin/perl", "/usr/local/bin/perl"]:
                if os.path.isfile(candidate):
                    perl_bin = candidate
                    break

        # Create VERSION file (tarball doesn't include it; getversion.sh needs it)
        version_file = os.path.join(self.build_folder, "VERSION")
        if not os.path.exists(version_file):
            with open(version_file, "w") as f:
                f.write("4.1\n")

        # Step 1: Generate Perl scripts from .in templates
        self.run(f'make genperlscripts PERL={perl_bin}')

        # Step 2: Generate documentation directly (avoid shell script exec issues)
        self.run('pod2man --name=arename ./arename > arename.1')
        self.run('pod2html ./arename > arename.html && rm -f *.tmp')
        self.run('pod2man --name=ataglist ./ataglist > ataglist.1')
        self.run('pod2html ./ataglist > ataglist.html && rm -f *.tmp')

    def package(self):
        pkg = self.package_folder
        src = self.build_folder

        # Install scripts to bin/
        copy(self, "arename", src=src, dst=os.path.join(pkg, "bin"))
        copy(self, "ataglist", src=src, dst=os.path.join(pkg, "bin"))

        # Install Perl modules to lib/site_perl/
        mod_src = os.path.join(src, "modules")
        lib_dst = os.path.join(pkg, "lib/site_perl")
        copy(self, "ARename.pm", src=mod_src, dst=lib_dst)
        copy(self, "ARename/*.pm", src=mod_src, dst=lib_dst)
        copy(self, "ARename/Template/*.pm", src=mod_src, dst=lib_dst)
        copy(self, "ARename/Util/*.pm", src=mod_src, dst=lib_dst)

        # Install documentation
        doc_dst = os.path.join(pkg, "share/doc/arename")
        for docfile in ["README", "UPGRADING", "REPORTING_BUGS", "LICENCE",
                        "CHANGES", "asdump", "arename.html", "ataglist.html"]:
            copy(self, docfile, src=src, dst=doc_dst)
        copy(self, "_arename", src=src, dst=os.path.join(pkg, "share/doc/arename/examples"))

        # Install man pages
        copy(self, "arename.1", src=src, dst=os.path.join(pkg, "share/man/man1"))
        copy(self, "ataglist.1", src=src, dst=os.path.join(pkg, "share/man/man1"))

    def package_info(self):
        # R38: Command-line tool — set bindirs for executable discovery
        self.cpp_info.bindirs = ["bin"]
        # Perl module path for consumers that need to use ARename.pm
        self.cpp_info.libdirs = ["lib/site_perl"]
