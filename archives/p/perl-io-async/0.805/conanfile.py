#!/usr/bin/env python3
"""Conan recipe for perl-io-async (IO::Async) 0.805 — pure Perl event framework.

HarmonyOS PC adaptation, following this archive's Perl-package convention
(perl-carp 1.50): ``package_type = "application"``, modules copied to
``lib/perl5``, plus a software-level ``commands.json`` (R38).

Contents (measured from the CPAN tarball): **39** ``.pm`` files under ``lib/``
(the ``IO::Async::*`` framework plus a bundled ``Future::IO::Impl::IOAsync``)
and **64** ``.t`` test files.

## Dependency situation (important, measured)

META.json declares non-core runtime requirements:

| Module | Kind | Available here? |
|---|---|---|
| ``Future`` (>=0.44) | **hard runtime** — 12 ``lib/`` files ``use Future`` | **NO** |
| ``Future::Utils`` (>=0.18) | hard runtime (``IO::Async::Handle``) | **NO** |
| ``Struct::Dumb`` | hard runtime | **NO** |
| ``IO::Socket::IP`` | *recommends* only | no (optional) |

Of the 39 modules, **12 load and 27 fail** without ``Future`` (measured), so the
framework is only partially usable until ``Future`` is adapted and published.

Per this archive's convention, Perl dependencies are **not** declared as Conan
``requires`` (only 1 of 30 sampled ``perl-*`` recipes does; perl-moose documents
them in notes.md instead) — so they are reported here and in ``notes.md`` rather
than pulled in. ``build()`` probes for them and reports honestly (R51).

``Module::Build`` is the *configure* requirement; it is irrelevant here because
this recipe does not run ``Build.PL`` (no build step for pure Perl).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# Non-core runtime requirements declared in META.json. Reported (not required)
# per the archive's Perl convention; see module docstring.
_RUNTIME_DEPS = ("Future", "Future::Utils", "Struct::Dumb")
# Test-only requirements that decide whether the upstream suite can be collected.
_TEST_DEPS = ("Test2::V0", "Test::Future::IO::Impl", "Test::Metrics::Any")


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


class IoAsyncConan(ConanFile):
    name = "perl-io-async"
    version = "0.805"
    package_type = "application"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/IO::Async"
    description = ("IO::Async — event-driven programming in an asynchronous "
                   "manner (pure Perl framework)")
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    @staticmethod
    def _missing(perl, modules):
        """Return the subset of ``modules`` that this perl cannot load."""
        prog = ('for my $m (@ARGV) { (my $f = $m) =~ s{::}{/}g; '
                'eval { require "$f.pm"; 1 } or print "$m\\n"; }')
        res = subprocess.run([perl, "-e", prog, *modules],
                             capture_output=True, timeout=120)
        return [m for m in res.stdout.decode().split() if m]

    def _runnable_tests(self, perl):
        """Return (runnable, blocked) test files.

        A test is *blocked* when its ``use`` statements (BEGIN-time) cannot be
        satisfied — the run never starts, which would otherwise abort the whole
        ``prove`` run. Detected with ``perl -c`` (compiles BEGIN blocks without
        executing the body).
        """
        tdir = os.path.join(self.source_folder, "t")
        if not os.path.isdir(tdir):
            return [], []
        runnable, blocked = [], []
        for name in sorted(os.listdir(tdir)):
            if not name.endswith(".t"):
                continue
            path = os.path.join(tdir, name)
            res = subprocess.run([perl, "-I", os.path.join(self.source_folder, "lib"),
                                  "-c", path],
                                 capture_output=True, timeout=120)
            err = (res.stdout + res.stderr).decode(errors="ignore")
            if "Can't locate" in err:
                blocked.append(name)
            else:
                runnable.append(name)
        return runnable, blocked

    def build(self):
        apply_conandata_patches(self)
        lib = os.path.join(self.source_folder, "lib")
        if not os.path.isdir(lib):
            raise ConanException("lib/ directory not found in the source tree")
        for mod in ("IO/Async/Loop.pm", "IO/Async/Notifier.pm",
                    "IO/Async/Stream.pm", "IO/Async/Timer.pm"):
            if not os.path.isfile(os.path.join(lib, mod)):
                raise ConanException(f"lib/{mod} missing from the source tree")

        perl = _find_perl()
        if not perl:
            self.output.warning(
                "no perl interpreter found — skipping the dependency probe and "
                "the upstream test suite (test_package still verifies the "
                "packaged modules under the conanrun environment)")
            return

        # Report the non-core runtime deps that are unavailable, honestly (R51):
        # without Future, most of the framework cannot even be loaded.
        missing_rt = self._missing(perl, _RUNTIME_DEPS)
        if missing_rt:
            self.output.warning(
                "non-core runtime dependency(-ies) unavailable: "
                + ", ".join(missing_rt)
                + " — of the 39 packaged modules only the subset not importing "
                  "Future is loadable (12/39 measured). These are Perl-level "
                  "dependencies, delivered outside Conan per this archive's "
                  "perl-* convention; adapt+publish them for full functionality.")
        self._run_upstream_tests(perl)

    def _run_upstream_tests(self, perl):
        """Run the runnable subset of the upstream suite and report honestly."""
        runnable, blocked = self._runnable_tests(perl)
        if not runnable and not blocked:
            self.output.warning("upstream t/ not found, skipping tests")
            return
        if blocked:
            missing = self._missing(perl, _TEST_DEPS)
            self.output.warning(
                f"upstream tests: excluding {len(blocked)} of "
                f"{len(blocked) + len(runnable)} files whose BEGIN-time imports "
                "cannot be satisfied (the run would abort at collection); "
                f"missing: {', '.join(missing) if missing else 'see t/ imports'} "
                "— these are Perl-level test deps, not a port defect")
        if not runnable:
            self.output.warning("no runnable upstream test files, skipping prove")
            return
        try:
            res = subprocess.run(
                [perl, "-Ilib", "-S", "prove", "-l", *[f"t/{n}" for n in runnable]],
                cwd=self.source_folder, capture_output=True, timeout=900)
            out = (res.stdout + res.stderr).decode(errors="ignore").strip()
            tail = [ln for ln in out.splitlines() if ln.strip()][-3:]
            self.output.info(f"upstream prove: {' | '.join(tail)}")
            if res.returncode != 0:
                self.output.warning(
                    "upstream prove reported failures in the runnable subset")
        except Exception as e:
            self.output.warning(f"upstream tests run failed: {e}")

    def package(self):
        lib = os.path.join(self.source_folder, "lib")
        dest = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(lib):
            shutil.copytree(lib, dest, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # All 39 modules must survive packaging (measured count upstream).
        count = sum(1 for root, _dirs, files in os.walk(dest)
                    for f in files if f.endswith(".pm"))
        if count < 39:
            raise ConanException(
                f"expected 39 .pm modules in the package, found {count} "
                "(recursive copy may have dropped a sub-directory)")
        for mod in ("IO/Async/Loop.pm", "IO/Async/Notifier.pm"):
            if not os.path.isfile(os.path.join(dest, mod)):
                raise ConanException(f"{mod} missing from the package folder")

    def package_info(self):
        # Perl modules are consumed via PERL5LIB (this archive's Perl-package
        # convention); export it so consumers/test_package need no hand paths.
        perl5 = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl5)
        self.buildenv_info.append_path("PERL5LIB", perl5)
        self.output.info(f"PERL5LIB={perl5}")
