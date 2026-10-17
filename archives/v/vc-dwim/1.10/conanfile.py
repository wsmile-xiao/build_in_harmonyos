#!/usr/bin/env python3
"""Conan recipe for vc-dwim 1.10 — VC-agnostic ChangeLog diff & commit tools.

vc-dwim is a pair of script tools (no compilation):
  * vc-dwim    — Perl script: warns when a ChangeLog entry does not match the
                 working-tree diff, shows/commits the diff (`--diff` mode).
  * vc-chlog   — POSIX sh script: generates a GCS-style ChangeLog entry from a
                 unified diff (uses awk / patch / ctags at runtime).

OHOS adaptation points:
  * Pure script package: package_type="application"; autotools is bypassed and
    the @VAR@ template substitutions normally done by configure/automake are
    performed here deterministically (abcselect/1.5 precedent).
  * Patch 0001 makes the perl module lookup relocatable (resolves
    ../share/vc-dwim relative to the script instead of a baked-in absolute
    datadir) and relaxes `umask 077` temp dirs to 022 (E129: HMDFS setgid +
    umask 077 makes config/script temp dirs unwritable even for the owner).
  * Requires perl-pod-parser/1.67: perl 5.42 removed Pod::PlainText from core;
    the module is provided via the dependency's PERL5LIB runenv_info.
  * Requires ctags/6.2.1: vc-chlog uses `ctags -x` for function-name extraction.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class VcDwimConan(ConanFile):
    name = "vc-dwim"
    version = "1.10"
    description = ("vc-dwim — version-control-agnostic ChangeLog diff and "
                   "commit tool, with vc-chlog ChangeLog entry generator")
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/vc-dwim/"
    url = "https://ftp.gnu.org/gnu/vc-dwim/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pod::PlainText (removed from perl 5.42 core) via PERL5LIB runenv
        self.requires("perl-pod-parser/1.67")
        # `ctags -x` used by vc-chlog function-name extraction
        self.requires("ctags/6.2.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        """No compilation: materialise the two scripts with the same @VAR@
        substitutions automake would do (GNUmakefile vc-dwim/vc-chlog rules).
        """
        src = self.source_folder
        subs = {
            "@VERSION@": self.version,
            "@PACKAGE@": self.name,
            "@PACKAGE_BUGREPORT@": "bug-vc-dwim@gnu.org",
            "@PATH_SEPARATOR@": ":",
            "@SHELL@": "/bin/sh",
            "@datadir@": "share",
            '@ctags_strip_type_column@': "yes",  # Universal Ctags -x layout
        }
        self._subst(os.path.join(src, "vc-dwim.pl"),
                    os.path.join(src, "vc-dwim"), subs, shebang=None)
        chlog_subs = dict(subs)
        chlog_subs.update({
            '@AWK@': "awk",
            '@CTAGS@': "ctags",
            '@PATCH@': "patch",
        })
        # vc-chlog.in has no shebang line; automake prepends #!/bin/sh
        self._subst(os.path.join(src, "vc-chlog.in"),
                    os.path.join(src, "vc-chlog"), chlog_subs,
                    shebang="#!/bin/sh")
        # sanity: no leftover template tokens
        for out in ("vc-dwim", "vc-chlog"):
            with open(os.path.join(src, out)) as fh:
                body = fh.read()
            if "@VERSION@" in body or "@PACKAGE_BUGREPORT@" in body:
                raise ConanException(f"unsubstituted template token in {out}")
        os.chmod(os.path.join(src, "vc-dwim"), 0o755)
        os.chmod(os.path.join(src, "vc-chlog"), 0o755)

    @staticmethod
    def _subst(infile, outfile, subs, shebang):
        with open(infile) as fh:
            body = fh.read()
        for k, v in subs.items():
            body = body.replace(k, v)
        if shebang is not None:
            body = shebang + "\n" + body
        with open(outfile, "w") as fh:
            fh.write(body)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        bindir = os.path.join(pkg, "bin")
        perllib = os.path.join(pkg, "share", "vc-dwim")
        mandir = os.path.join(pkg, "share", "man", "man1")
        for d in (bindir, perllib, mandir):
            os.makedirs(d, exist_ok=True)

        for script in ("vc-dwim", "vc-chlog"):
            shutil.copy2(os.path.join(src, script), os.path.join(bindir, script))
        for pm in ("VC.pm", "Coda.pm", "ProcessStatus.pm"):
            shutil.copy2(os.path.join(src, pm), os.path.join(perllib, pm))
        for man in ("vc-dwim.1", "vc-chlog.1"):
            manpage = os.path.join(src, "man", man)
            if os.path.isfile(manpage):
                shutil.copy2(manpage, os.path.join(mandir, man))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # scripts resolve their .pm modules relative to the script location
        # (patch 0001), so no PERL5LIB is needed for the package's own modules.
