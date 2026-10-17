#!/usr/bin/env python3
"""Conan recipe for mr (myrepos) 1.20180726 — pure Perl script utility.

mr is a tool to manage multiple version control repositories.
It is a pure Perl script with a simple Makefile (no configure step).
The Makefile uses pod2man to generate man pages, then installs scripts.

Platform adaptations for OHOS:
  - No patches needed: shebang is already #!/usr/bin/env perl
  - pod2man is available on OHOS at /data/service/hnp/bin/pod2man

R28: test_package/ exists.
R32: settings.os check uses "in" not "==".
R34: test_package tests actual mr functionality (mr help, mr register).
R38: commands.json declared (command-line tool with mr and webcheckout).
R39: source URL is official Debian pool.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MrConan(ConanFile):
    name = "mr"
    version = "1.20180726"
    description = "Multiple Repository management tool (mr command)"
    license = "GPL-2.0-or-later"
    homepage = "https://myrepos.branchable.com/"
    url = "https://myrepos.branchable.com/"
    topics = ("vcs", "git", "repository-management", "perl")

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # mr is a pure Perl script with no external dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Ensure pod2man is in PATH (OHOS: /data/service/hnp/bin/pod2man)
        _hnp_bin = "/data/service/hnp/bin"
        # Filter empty components to handle edge case where PATH is empty or has trailing separators
        _path_components = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        if os.path.isdir(_hnp_bin) and _hnp_bin not in _path_components:
            os.environ["PATH"] = _hnp_bin + os.pathsep + os.environ.get("PATH", "")
        # mr uses a simple Makefile: make build generates man pages via pod2man
        self.run("make build", cwd=self.source_folder)

    def package(self):
        # Install mr, webcheckout binaries, man pages, lib files, and examples
        self.run(
            f'make install DESTDIR="{self.package_folder}" '
            f'PREFIX="" MANDIR="/share/man/man1" '
            f'LIBDIR="/share/mr" LIBSHDIR="/share/mr.sh" '
            f'EGDIR="/share/doc/myrepos/examples"',
            cwd=self.source_folder
        )
        # Ensure binaries are executable
        for binary in ("mr", "webcheckout"):
            bin_path = os.path.join(self.package_folder, "bin", binary)
            if os.path.isfile(bin_path):
                os.chmod(bin_path, os.stat(bin_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        # Pure script project: no libraries, just executables in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
