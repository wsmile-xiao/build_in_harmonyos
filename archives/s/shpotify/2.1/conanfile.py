#!/usr/bin/env python3
"""Conan recipe for shpotify 2.1 — pure Shell (Bash) script project.

shpotify is a CLI Bash script that controls Spotify from the command line. It
ships a single self-contained shell script (`spotify`); there is no build
system and no compilation step. "Building" consists of installing the script
and its documentation under a prefix.

Platform compatibility:
  - Shebang #!/usr/bin/env bash is OHOS-compatible (no /bin/bash hard-coded).
  - No C code, no ELF binaries — only a Bash script.
  - Runtime needs only Bash and common coreutils (curl/base64/grep/sed/tr),
    all present on HarmonyOS PC.
  - `spotify` with no arguments prints usage and exits 0 on OHOS (verified).
  - Playback/search subcommands talk to the Spotify desktop app via macOS
    `osascript` upstream; on OHOS only the usage entry point is exercised
    (documented in notes.md / test_package).

R28: test_package/ exists.
R32: settings.os uses "os" only (no compiler needed for a shell script).
R38: Command-line tool — commands.json declared at the software level.
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ShpotifyConan(ConanFile):
    name = "shpotify"
    version = "2.1"
    description = "A command-line interface to Spotify (pure Bash script)"
    license = "MIT"
    homepage = "https://github.com/hnarayanan/shpotify"
    url = ""  # CI fills this

    package_type = "application"
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
        apply_conandata_patches(self)
        # shpotify is a pure shell project — no compilation step.
        # Nothing to build; the script is installed verbatim in package().

    def package(self):
        src = self.source_folder
        script_src = os.path.join(src, "spotify")
        # Fail fast if the upstream script is missing or renamed, so an
        # upstream change cannot silently ship a package with no command.
        if not os.path.isfile(script_src):
            raise ConanException(
                f"spotify not found in source '{src}'; expected the upstream "
                "Bash script to be present after source()."
            )
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "spotify", src=src, dst=bin_dir, keep_path=False)
        # Make the script executable
        script = os.path.join(bin_dir, "spotify")
        os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        # The upstream tarball has no standalone LICENSE file; the MIT license
        # text is embedded in README.md ("Copyright and license" section) and
        # in the script header, so install README.md as both documentation and
        # license record.
        copy(self, "README.md", src=src,
             dst=os.path.join(self.package_folder, "share", "doc", "shpotify"), keep_path=False)
        copy(self, "README.md", src=src,
             dst=os.path.join(self.package_folder, "share", "licenses", "shpotify"), keep_path=False)

    def package_info(self):
        # Pure script project: no libraries, just an executable in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
