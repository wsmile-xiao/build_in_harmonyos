#!/usr/bin/env python3
"""Conan recipe for clitest 0.5.0 — a tester for Unix command lines.

clitest reads a plain text or Markdown file, runs every command found after a
prompt marker and compares the real output with the expected output written in
the file. It is a single, self-contained POSIX shell script: no compilation
units, no build system (the upstream Makefile only wraps `docker run` for the
maintainer's lint/test workflow), and no Conan dependencies — the runtime needs
`sh`, `sed`, `grep`, `diff`, `cat`, `mktemp`, `awk` and `tr`, which are
operating-system tools rather than packages.

HarmonyOS adaptation (patches/0001-clitest.patch — two behavioural changes,
3 diff hunks: shebang, the new tt_temp_base declaration, and the temp dir
selection itself):
  1. shebang `#!/bin/sh` -> `#!/system/bin/sh`. HarmonyOS has no traditional
     `/bin` directory; `sh` lives in `/system/bin/sh` (knowledge entry E165).
     Without this the installed tool cannot be exec'd directly, which is what
     the software-level commands.json declaration expects.
  2. Temp dir base. Upstream hardcodes `${TMPDIR:-/tmp}`; `/tmp` is read-only
     on HarmonyOS (knowledge entry E002), so with $TMPDIR unset clitest aborts
     with "cannot create temporary dir". The patch only changes the *default*
     (unset $TMPDIR) to "/tmp when writable, else $HOME"; an explicitly set
     $TMPDIR is still honoured verbatim so upstream's "invalid TMPDIR must fail
     loudly" semantics — and its test case for it — stay intact.

Verification of the patch is functional, not cosmetic: with a read-only /tmp
and $TMPDIR unset the unpatched script exits with an error while the patched
one runs the test suite successfully (see notes.md for the transcript).
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class ClitestConan(ConanFile):
    name = "clitest"
    version = "0.5.0"
    description = ("Tester for Unix command lines: runs the commands found in a "
                   "text/Markdown file and checks their output")
    license = "MIT"
    homepage = "https://github.com/aureliojargas/clitest"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("testing", "shell", "cli", "posix", "script", "ohos")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # No compilation: the upstream artifact is a finished POSIX shell
        # script. Patches are applied here, the prevailing convention among
        # this repo's no_copy_source recipes (archives/l/lynis/3.1.7.1 is the
        # closest shell-tool precedent); package_id keeps only `os`, so the
        # shared source folder is patched once per recipe revision.
        apply_conandata_patches(self)

        script = os.path.join(self.source_folder, "clitest")
        if not os.path.isfile(script):
            raise ConanException("upstream clitest script missing from source archive")

        # Fail early if the portability patch did not land: the OHOS shebang is
        # what makes the installed tool directly executable on the device.
        with open(script, "r", encoding="utf-8") as fh:
            shebang = fh.readline().strip()
        if shebang != "#!/system/bin/sh":
            raise ConanException(f"unexpected shebang after patching: {shebang!r}")
        self.output.info("Validated patched clitest script; no compilation required")

    def package(self):
        copy(self, "clitest", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        for doc in ("README.md", "CHANGELOG.md"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "doc", "clitest"),
                 keep_path=False)

        # Best-effort exec bit: on HMDFS (HarmonyOS) chmod is frequently
        # ignored or normalised, so the tests invoke the script through an
        # explicit interpreter instead of asserting on the permission bits.
        binary = os.path.join(self.package_folder, "bin", "clitest")
        try:
            os.chmod(binary, 0o755)
        except OSError as exc:  # pragma: no cover - defensive
            self.output.warning(f"chmod on {binary} failed: {exc}")

    def package_id(self):
        # Pure shell script: independent of arch/compiler/build_type. `os` is
        # kept because the packaged script carries a HarmonyOS-specific shebang.
        del self.info.settings.arch
        del self.info.settings.compiler
        del self.info.settings.build_type

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
