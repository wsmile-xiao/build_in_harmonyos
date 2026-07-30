#!/usr/bin/env python3
"""Conan recipe — man2html 3.0.1

man2html is a Perl program to convert formatted nroff output to HTML.
Build system: custom (Perl install.me installer, no C compilation required).

Source: https://www.mhonarc.org/release/misc/man2html3.0.1.tar.gz
License: GPL-2.0-or-later

References:
  - R1: parameter minimalism — only -batch -binpath -manpath -perlpath
  - R28: test_package/ present
  - R32: settings.os check uses in ("Linux", "OHOS")
  - R34: test must exercise the actual man2html binary (not a stub)
  - R38: command-line tool — commands.json declared at software level
  - R39: source URL is the official mhonarc.org release
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Man2HtmlConan(ConanFile):
    name = "man2html"
    version = "3.0.1"
    description = "Convert nroff man pages to HTML (Perl program)"
    license = "GPL-2.0-or-later"
    homepage = "https://savannah.nongnu.org/projects/man2html/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Perl is a system runtime dependency (not a Conan package).
        # The build host must have perl installed and on PATH.
        pass

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"man2html supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # install.me is a Perl installer script.
        # -batch: non-interactive mode
        # -binpath: where to install the man2html executable
        # -manpath: where to install the man page
        # -perlpath: pathname of perl (install.me rewrites the #! shebang line
        #            of the installed man2html script to use this perl)
        #            CRITICAL on OHOS where perl is at /data/service/hnp/bin/perl
        #            but the source shebang is #!/usr/local/bin/perl (non-existent).
        bin_dir = os.path.join(self.build_folder, "bin")
        # install.me installs man pages to <manpath>/man1/<name>.1
        # but does not create the man1 subdirectory — pre-create it.
        man_dir = os.path.join(self.build_folder, "man")
        man1_dir = os.path.join(man_dir, "man1")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man1_dir, exist_ok=True)

        # Detect perl path on the build host
        perl_path = shutil.which("perl") or "/usr/bin/perl"

        self.run(
            f"{perl_path} install.me -batch "
            f"-binpath {bin_dir} "
            f"-manpath {man_dir} "
            f"-perlpath {perl_path}"
        )

        # Diagnostic: verify man2html was installed to build bin/
        installed = os.path.join(bin_dir, "man2html")
        if os.path.exists(installed):
            self.output.info(f"man2html installed to {installed}")
            with open(installed, "r", errors="replace") as f:
                self.output.info(f"shebang: {f.readline().strip()}")
        else:
            raise Exception(
                f"man2html not found in {bin_dir} after install.me. "
                f"Contents: {os.listdir(bin_dir)}"
            )

    def package(self):
        # Copy installed man2html executable to package bin/
        copy(self, "man2html", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # Copy man page to package man/man1/
        copy(self, "man2html.1",
             src=os.path.join(self.build_folder, "man", "man1"),
             dst=os.path.join(self.package_folder, "man", "man1"))
        # Diagnostic: verify package contents
        pkg_bin = os.path.join(self.package_folder, "bin")
        if os.path.isdir(pkg_bin):
            self.output.info(f"package bin/ contents: {os.listdir(pkg_bin)}")
        else:
            self.output.warn(f"package bin/ does not exist: {pkg_bin}")

    def package_info(self):
        # man2html is a command-line tool (no C libraries)
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
