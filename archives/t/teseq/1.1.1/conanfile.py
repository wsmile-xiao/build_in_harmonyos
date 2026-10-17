#!/usr/bin/env python3
"""Conan recipe for GNU teseq 1.1.1 — the Escape Sequence Illuminator.

teseq reads a stream/file containing terminal control sequences (ANSI/ECMA-48,
ISO 2022, VT100) and prints the sequences plus a readable description of what
they do; the companion ``reseq`` script reverses the transformation, which
makes teseq usable as a round-trippable terminal-demo editor and as a typescript
de-instrumenter.

Upstream is a GNU Autotools project building two artifacts:

* ``teseq``  — the C program (src/teseq.c + inputbuf/ringbuf/putter/csi)
* ``reseq``  — a Perl script generated from reseq.in by config.status

OHOS adaptation notes:

* ``configure`` (and the ``config.status`` template it embeds) create their
  temporary work directories with ``umask 077``, which yields ``drwx--S---``
  and ``drwxrws--x`` on HMDFS depending on the parent directory; the setgid
  directory created by ``mktemp -d ./confXXXXXX`` rejects writes even from its
  owner, so ``config.status`` aborts with
  ``./confObCbdF/subs1.awk: Permission denied`` /
  "could not setup config files machinery".  ``patches/0002-configure.patch``
  rewrites the two ``umask 077`` occurrences to ``umask 022`` (knowledge base
  E129 / E112 / E136), matching the accepted a52dec/0.7.4 fix.
* ``make check`` runs the whole upstream suite on the target: the 28 teseq
  shell cases, the 28 ``-r`` reseq cases, ``exercise-seqs`` and — through the
  ``check/0.15.2`` test_requires (PKG_CHECK_MODULES) — the two libcheck unit
  tests src/test-ringbuf / src/test-inputbuf.
* ``help2man`` and ``makeinfo`` are missing on OHOS, and the automake VTI
  rule relies on ``mdate-sh``, which cannot parse the ISO-8601 dates printed
  by the HarmonyOS ``ls`` (when parsing fails it dumps the environment into
  ``doc/version.texi``).  ``patches/0001-Makefile.in.patch`` turns the
  ``stamp-vti`` rule into a no-op so the shipped ``doc/teseq.info`` /
  ``doc/teseq.1`` / ``doc/reseq.1`` stay valid and are installed verbatim;
  the build is in-source (like a52dec/0.7.4).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class TeseqConan(ConanFile):
    name = "teseq"
    version = "1.1.1"
    description = (
        "Escape sequence illuminator: translates files containing terminal "
        "control sequences into human-readable form, and back (reseq)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/teseq/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("terminal", "control-sequences", "ansi", "ecma-48", "vt100",
              "gnu")

    # Command-line tool: publishes bin/teseq + bin/reseq, no libraries.
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "teseq targets POSIX systems (GNU Autotools + POSIX shell); "
                f"got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac probes check via PKG_CHECK_MODULES([libcheck], [check], , :);
        # when present, `make check` also builds and runs the two upstream
        # libcheck unit tests (src/test-ringbuf, src/test-inputbuf) besides
        # the 28+28 shell cases.  check is published on the ohpcd remote.
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-silent-rules")
        # texinfo (makeinfo), help2man and checkmk are unavailable on OHOS;
        # the release tarball already ships the generated info file and
        # manpages, and these overrides keep make from trying to regenerate
        # them if a timestamp ever looks stale.
        tc.make_args.append("HELP2MAN=true")
        tc.make_args.append("CHECKMK=true")
        tc.make_args.append("MAKEINFO=true")
        env = tc.environment()
        # The published check package ships both libcheck.a and libcheck.so;
        # the linker prefers the shared object, so its libdir must be on
        # LD_LIBRARY_PATH for the two libcheck unit tests to run.
        check = self.dependencies["check"]
        env.append_path("LD_LIBRARY_PATH",
                        check.cpp_info.aggregated_components().libdirs[0])
        # libcheck's open_tmp_file (check_msg.c) probes TEMP before the musl
        # P_tmpdir ("/tmp", read-only on OHOS, E002) and TMPDIR (E547), so the
        # whole build (and the check suite) gets a guaranteed-writable temp
        # root below the build folder.
        check_tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(check_tmp, exist_ok=True)
        env.define("TMPDIR", check_tmp)
        env.define("TEMP", check_tmp)
        tc.generate(env)
        # Publish the check test dependency to pkg-config so that the
        # PKG_CHECK_MODULES probe in configure.ac succeeds.
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Full upstream suite: tests/run-tests (28 teseq cases), run-tests -r
        # (28 reseq cases), exercise-seqs, and the two libcheck unit tests.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

        # Upstream ``make install`` installs bin/teseq + bin/reseq, and the
        # manpages come from the tarball; nothing else needs staging.

    def package_info(self):
        # Command-line tool: expose the binaries and their manpages so
        # downstream consumers can locate them without guessing.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        self.cpp_info.set_property("cmake_file_name", "teseq")
        self.cpp_info.set_property("cmake_target_name", "teseq::teseq")
        self.cpp_info.set_property("pkg_config_name", "teseq")
