#!/usr/bin/env python3
"""Conan recipe — crashmail 1.7 (CrashMail II, FidoNet mail tosser suite).

CrashMail II is a portable FidoNet mail processor ("tosser") plus its
companion command-line utilities.  Upstream ships hand-written recursive
GNU Makefiles (no autotools/cmake/meson) with one target per platform:
`make linux` builds the POSIX implementation and drops eight executables
into `bin/`.

OHOS adaptation (details and evidence in notes.md):

  * The Linux makefiles hard-wire the compiler as
    ``CC = gcc $(CPPFLAGS) ...`` — command-line ``make CC=clang`` would
    replace the whole definition and silently drop ``$(DEFS)`` and the
    ``-I`` flags.  A small patch introduces ``CC_BIN`` so only the
    compiler binary is redirected while the makefile keeps owning its
    flags; the recipe then passes ``CC_BIN="$CC"`` from the Conan
    toolchain (R33: compiler comes from the Conan graph, never from an
    undefined shell variable).
  * ``src/jamlib/mbase.c`` uses ``struct flock``/``F_SETLK`` but only
    includes ``<sys/file.h>``; glibc re-exports ``<fcntl.h>`` from there,
    musl/OHOS does not — patched to include ``<fcntl.h>`` explicitly.
  * ``lastt`` is a tentative file-scope definition in both ``handle.c``
    and ``pkt.c``.  It linked only under GCC's historical ``-fcommon``
    (implicit sharing of the two module counters); clang defaults to
    ``-fno-common``, so both are made ``static`` — which is also what the
    two call sites actually need.
  * ``STRIP`` is disabled (``STRIP=:``): the OHOS lld stamps a
    ``.codesign`` section whose header records the signed image length,
    and any byte change inside that range invalidates the signature — the
    kernel then refuses to exec the file with EPERM (exit 126).  ``strip``
    shrinks the image, so stripping produces non-runnable binaries.
  * Upstream's test runner ``tests/roundup`` starts with ``#!/bin/bash``;
    OHOS has no ``/bin/bash``, so the suite is started through bash
    resolved from CONFIG_SHELL/PATH instead of the shebang.

R38: command-line tools — commands.json declared at software level.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# The eight executables produced by `make linux`.
_TOOLS = (
    "crashmail", "crashstats", "crashlist", "crashgetnode",
    "crashmaint", "crashwrite", "crashexport", "crashlistout",
)


def _bash():
    """Resolve a usable bash; OHOS has no /bin/bash (see module docstring)."""
    for candidate in (os.environ.get("CONFIG_SHELL"),
                      shutil.which("bash"),
                      "/data/service/hnp/bin/bash"):
        if candidate and os.path.exists(candidate):
            return candidate
    return "bash"


class CrashmailConan(ConanFile):
    name = "crashmail"
    version = "1.7"
    package_type = "application"

    description = ("CrashMail II - FidoNet mail tosser and scanner suite "
                   "(crashmail, crashwrite, crashlist, crashgetnode, "
                   "crashmaint, crashstats, crashexport, crashlistout)")
    homepage = "http://ftnapps.sourceforge.net/crashmail.html"
    # CrashMail itself carries a custom permissive notice (Debian calls it
    # "permissive"); the bundled JAMLIB is LGPL-2.1-or-later.  See the
    # README "Copyright" section and src/jamlib/LICENSE in the sources.
    license = "LicenseRef-CrashMail-permissive AND LGPL-2.1-or-later"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: must check in ("Linux", "OHOS"), not == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "crashmail only supports Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # Only used for the conanbuild environment (CC/CFLAGS/CPPFLAGS/
        # LDFLAGS) consumed by the upstream Makefiles; upstream has no
        # configure script.  No extra flags are needed: the OHOS clang/lld
        # default output is already PIE with GNU_RELRO and BIND_NOW.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # `make linux` recurses into src/{cmnllib,jamlib,oslib_linux} and
        # then src/, producing all eight tools in <source_folder>/bin.
        # Device default parallelism: -j1 (workflow 2.1).
        self.run('make -j1 linux CC_BIN="$CC" STRIP=:',
                 env="conanbuild", cwd=self.source_folder)

        # Upstream test suite: tests/roundup drives five shell test plans
        # that exercise the freshly built binaries.  Started through bash
        # because the shebang is #!/bin/bash and OHOS has no /bin/bash.
        self.run('"%s" ./roundup' % _bash(),
                 env="conanbuild",
                 cwd=os.path.join(self.source_folder, "tests"))

    def package(self):
        top = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "*", os.path.join(top, "bin"), bindir, keep_path=False)

        # Guard: the build must produce exactly the eight documented tools.
        # `make linux` can silently skip a target (e.g. if one is later
        # removed upstream), and every downstream claim - commands.json,
        # README, MANIFEST.yml - is written against this set. Fail loudly
        # here instead of shipping a package with tools missing.
        #
        # `copy()` does not create the destination when nothing matches, so
        # bindir may not exist at all; tolerate that here so the failure is
        # the explicit ConanException below rather than a bare
        # FileNotFoundError from os.listdir.
        listed = os.listdir(bindir) if os.path.isdir(bindir) else []
        packaged = sorted(f for f in listed
                          if os.path.isfile(os.path.join(bindir, f)))
        if packaged != sorted(_TOOLS):
            raise ConanException(
                "expected exactly %d tools %s but bin/ contains %s"
                % (len(_TOOLS), sorted(_TOOLS), packaged)
            )

        copy(self, "*.1", os.path.join(top, "man"),
             os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "*", os.path.join(top, "doc"),
             os.path.join(self.package_folder, "share", "doc", "crashmail"),
             keep_path=False)
        # JAMLIB is the only file in the tree carrying an actual licence text.
        copy(self, "LICENSE", os.path.join(top, "src", "jamlib"),
             os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # Make the tools reachable from VirtualRunEnv (test_package).
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
