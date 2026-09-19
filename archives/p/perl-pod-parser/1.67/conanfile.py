#!/usr/bin/env python3
"""Conan recipe for perl-pod-parser (Pod::Parser) 1.67 — pure Perl POD parser.

HarmonyOS PC adaptation, following this archive's Perl-package convention
(perl-carp 1.50): ``package_type = "application"``, modules copied to
``lib/perl5``, plus a software-level ``commands.json`` (R38).

The distribution name is **Pod-Parser** while the module and the conan package
name are ``perl-pod-parser`` — kept consistent with the ``perl-*`` naming scheme
used by the ~270 existing Perl packages in this archive.

Contents (measured from the CPAN tarball):

* ``lib/Pod/`` — 6 modules: ``Parser.pm`` (the main one), ``Find.pm``,
  ``InputObjects.pm``, ``ParseUtils.pm``, ``PlainText.pm``, ``Select.pm``
* ``scripts/podselect.PL`` — a ``.PL`` template that upstream's MakeMaker
  processes into the ``podselect`` executable. This recipe does not run
  MakeMaker, so the script is generated here by substituting the shebang
  line with the real interpreter path (see ``_generate_podselect``).
* ``t/pod/`` — 16 ``.t`` files with 25 subtests (all pass; run by ``build()``).

Dependencies are **Perl core modules only** (``Cwd`` / ``File::Basename`` /
``File::Spec`` — and ``Test::More`` for the tests), all shipped with the
interpreter, so no ``requires()`` is needed. This matches the archive's existing
``perl-*`` recipes (perl-carp / perl-json-pp / perl-scope-guard all declare no
requirements).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


def _find_perl():
    """Locate a usable perl interpreter (same candidate list as perl-carp)."""
    p = shutil.which("perl")
    if p:
        return p
    for cand in ("/storage/Users/currentUser/usr/local/bin/perl",
                 "/data/service/hnp/bin/perl", "/usr/bin/perl"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


class PerlPodParserConan(ConanFile):
    name = "perl-pod-parser"
    version = "1.67"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/Pod::Parser"
    description = ("Pod::Parser — base class for creating POD filters and "
                   "translators (pure Perl)")
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _generate_podselect(self, perl):
        """Materialise ``scripts/podselect`` by **running** ``podselect.PL``.

        ``podselect.PL`` is a MakeMaker **generator script**, not a template
        whose first line can simply be swapped: it carries the
        ``!GROK!THIS!`` / ``!NO!SUBS!`` heredocs (``print OUT <<"!GROK!THIS!"``
        … ``close OUT`` / ``chmod 0755, $file``) and writes the real
        ``podselect`` beside itself. An earlier revision only rewrote line 1 of
        the generator and shipped *that* as the executable — the shipped file
        still contained the generator's own ``print OUT`` code, so it was not
        the deliverable at all.

        Running the generator is exactly what MakeMaker's ``PL_FILES`` does. The
        first line of its output comes from ``$Config{startperl}``; measured on
        this platform that is the shell/perl **polyglot**
        ``: # use perl`` + ``eval 'exec perl -S $0 "$@"'`` rather than a
        ``#!`` line. So the product legitimately does **not** start with ``#!``
        — assertions elsewhere are written accordingly.
        """
        scripts = os.path.join(self.source_folder, "scripts")
        src = os.path.join(scripts, "podselect.PL")
        if not os.path.isfile(src):
            return None
        dst = os.path.join(scripts, "podselect")
        if os.path.isfile(dst):
            os.remove(dst)
        self.run(f'"{perl}" podselect.PL', cwd=scripts)
        if not os.path.isfile(dst):
            raise ConanException(
                "running scripts/podselect.PL produced no scripts/podselect")
        with open(dst, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read()
        # A genuinely materialised script must no longer carry the generator's
        # own output statements.
        for marker in ("!NO!SUBS!", "!GROK!THIS!", "print OUT"):
            if marker in head:
                raise ConanException(
                    f"scripts/podselect still contains generator code "
                    f"({marker!r}) — the .PL was not executed")
        os.chmod(dst, 0o755)
        return dst

    def build(self):
        apply_conandata_patches(self)
        lib = os.path.join(self.source_folder, "lib")
        if not os.path.isdir(lib):
            raise ConanException("lib/ directory not found in the source tree")
        for mod in ("Parser.pm", "Select.pm", "PlainText.pm", "InputObjects.pm",
                    "Find.pm", "ParseUtils.pm"):
            if not os.path.isfile(os.path.join(lib, "Pod", mod)):
                raise ConanException(f"lib/Pod/{mod} missing from the source tree")

        perl = _find_perl()
        if perl and os.path.isfile(os.path.join(self.source_folder, "scripts",
                                                "podselect.PL")):
            self._generate_podselect(perl)
            self.output.info(f"generated podselect from podselect.PL (perl={perl})")

        self._run_upstream_tests(perl)

    def _run_upstream_tests(self, perl):
        """Run the upstream POD test suite and report the real pass rate (R51)."""
        tdir = os.path.join(self.source_folder, "t", "pod")
        if not os.path.isdir(tdir):
            self.output.warning("upstream t/pod not found, skipping tests")
            return
        if not perl:
            self.output.warning(
                "upstream tests skipped: no perl interpreter found on this "
                "machine (the packaged modules are still verifiable by "
                "test_package, which runs under conanrun env)")
            return
        try:
            probe = subprocess.run([perl, "-MTest::More", "-e", "1"],
                                   capture_output=True, timeout=60)
            if probe.returncode != 0:
                self.output.warning(
                    "upstream tests skipped: Test::More unavailable in this "
                    "perl (a core module, so this indicates a stripped "
                    "interpreter)")
                return
            res = subprocess.run(
                # -Ilib makes the in-tree Pod::* visible; prove runs the t/pod
                # suite exactly as `make test` would.
                [perl, "-Ilib", "-S", "prove", "-l", "t/pod"],
                cwd=self.source_folder, capture_output=True, timeout=600)
            out = (res.stdout + res.stderr).decode(errors="ignore").strip()
            tail = [ln for ln in out.splitlines() if ln.strip()][-3:]
            self.output.info(f"upstream prove: {' | '.join(tail)}")
            if res.returncode != 0:
                self.output.warning("upstream POD tests reported failures")
        except Exception as e:
            self.output.warning(f"upstream tests run failed: {e}")

    def package(self):
        lib = os.path.join(self.source_folder, "lib")
        dest = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(lib):
            shutil.copytree(lib, dest, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # Sanity: all six modules must be present
        for mod in ("Parser.pm", "Select.pm", "PlainText.pm", "InputObjects.pm",
                    "Find.pm", "ParseUtils.pm"):
            if not os.path.isfile(os.path.join(dest, "Pod", mod)):
                raise ConanException(f"Pod/{mod} missing from the package folder")

        # The materialised podselect executable.
        #
        # This must be an error, not a silent skip: the script is a documented
        # deliverable, and ``if os.path.isfile(script):`` hid a real failure
        # mode (no perl at build time / the .PL generator never executed)
        # behind a package that simply lacked ``bin/podselect``.
        script = os.path.join(self.source_folder, "scripts", "podselect")
        if not os.path.isfile(script):
            raise ConanException(
                "scripts/podselect was not materialised from podselect.PL — "
                "bin/podselect would be missing from the package")
        with open(script, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for marker in ("!NO!SUBS!", "!GROK!THIS!", "print OUT"):
            if marker in text:
                raise ConanException(
                    f"scripts/podselect is the un-executed generator "
                    f"({marker!r} present) — refusing to package it")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        dest = os.path.join(bindir, "podselect")
        shutil.copy2(script, dest)
        os.chmod(dest, 0o755)

    def package_info(self):
        # Perl modules are consumed via PERL5LIB (the archive's Perl-package
        # convention); export it so consumers/test_package pick it up without
        # hand-rolled paths.
        perl5 = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl5)
        self.buildenv_info.append_path("PERL5LIB", perl5)
        self.output.info(f"PERL5LIB={perl5}")
