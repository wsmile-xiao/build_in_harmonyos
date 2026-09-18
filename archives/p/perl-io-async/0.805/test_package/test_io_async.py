#!/usr/bin/env python3
"""Consumer-side check for the packaged perl-io-async 0.805 (R34: real API).

Drives the packaged ``IO::Async::*`` modules through the perl interpreter, the
same approach this archive's other perl-* test_packages use. Assertions are
based on measurements, not assumptions.

Measured facts pinned here:

* The distribution ships **39** ``.pm`` modules under ``lib/``.
* Of those, **12 load and 27 fail** in an environment without the non-core
  runtime dependency ``Future`` (which no perl on this machine provides). The
  failures are all ``Can't locate Future.pm`` — i.e. an *environmental*
  dependency gap, not a packaging defect.
* ``IO::Async::Loop`` (and the other 11 Future-free modules) load fine, which is
  what proves the packaged tree itself is intact and importable.

So this test verifies the **packaging** thoroughly (all 39 present, the
loadable subset actually loads, the Future gap is exactly as expected) rather
than pretending the framework is fully functional — see notes.md.
"""
import os
import shutil
import subprocess
import sys

PERL_CANDIDATES = (
    "/storage/Users/currentUser/usr/local/bin/perl",
    "/data/service/hnp/bin/perl",
    "/usr/bin/perl",
)

# Modules that load without the non-core Future dependency. This list was
# MEASURED by loading all 39 packaged modules one by one with the real
# interpreter (12 succeeded) — it is deliberately not guessed. Note there is no
# ``IO::Async::Time`` in this distribution (an earlier draft assumed one and
# failed); the platform-specific OS::* modules are excluded so the check stays
# portable.
FUTURE_FREE = (
    "IO::Async",
    "IO::Async::OS",
    "IO::Async::Loop",
    "IO::Async::Debug",
    "IO::Async::Test",
)
# A representative module that *does* require Future (must fail identically to
# upstream behaviour, proving the failure is dependency-driven).
FUTURE_DEPENDENT = "IO::Async::Notifier"


def find_perl():
    p = shutil.which("perl")
    if p:
        return p
    for cand in PERL_CANDIDATES:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def run_perl(perl, lib, program, args=()):
    res = subprocess.run([perl, f"-I{lib}", "-e", program, *args],
                         capture_output=True, timeout=180)
    return res.returncode, (res.stdout + res.stderr).decode(errors="ignore")


def main():
    pkg = sys.argv[1]
    perl5 = os.path.join(pkg, "lib", "perl5")
    if not os.path.isdir(perl5):
        print(f"FAIL: lib/perl5 not found under {pkg}", file=sys.stderr)
        return 1

    # --- all 39 upstream modules are packaged -------------------------------
    found = []
    for root, _dirs, files in os.walk(perl5):
        for f in files:
            if f.endswith(".pm"):
                found.append(os.path.relpath(os.path.join(root, f), perl5))
    assert len(found) == 39, f"expected 39 .pm modules, found {len(found)}"
    assert any(p.endswith("IO/Async/Loop.pm") for p in found), found
    assert any(p.endswith("IO/Async/Notifier.pm") for p in found), found
    assert any(p.endswith("Future/IO/Impl/IOAsync.pm") for p in found), found

    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # --- the Future-free subset really loads --------------------------------
    for mod in FUTURE_FREE:
        rc, out = run_perl(perl, perl5, f'require {mod}; print "loaded\\n";')
        if rc != 0 or "loaded" not in out:
            print(f"FAIL: {mod} should load but did not:\n{out}", file=sys.stderr)
            return 1

    # --- version of the main module ------------------------------------------
    rc, out = run_perl(perl, perl5,
                       'require IO::Async::Loop; '
                       'print $IO::Async::Loop::VERSION // "undef", "\\n";')
    if rc != 0:
        print(f"FAIL: reading VERSION failed:\n{out}", file=sys.stderr)
        return 1
    assert out.strip().splitlines()[-1] == "0.805", out

    # --- a real API call on a loadable module -------------------------------
    # IO::Async::Loop->new constructs a concrete loop object backed by the
    # packaged framework — real behaviour, not merely an import.
    rc, out = run_perl(perl, perl5, (
        'use IO::Async::Loop;'
        'my $loop = IO::Async::Loop->new;'
        'print ref($loop), "\\n";'))
    if rc != 0:
        print(f"FAIL: IO::Async::Loop->new failed:\n{out}", file=sys.stderr)
        return 1
    assert "IO::Async::Loop" in out, out

    # --- the Future gap behaves exactly as measured -------------------------
    # rc is checked FIRST, and the "Can't locate Future.pm" text only decides
    # *which* explanation applies. An earlier revision branched on the message
    # alone and never inspected rc in that branch, so any *other* load failure
    # (missing Future::Utils, a packaging regression, a syntax error) fell into
    # the "Future is now available" NOTE path and still returned 0 — the test
    # reported success while asserting the opposite of the truth. Reproduced by
    # pointing FUTURE_DEPENDENT at a module that does not exist at all:
    # the old code printed "Future appears to be available now" and PASSed.
    rc, out = run_perl(perl, perl5,
                       f'require {FUTURE_DEPENDENT}; print "loaded\\n";')
    if rc == 0:
        # Loading succeeded: Future is available now. That is a strict
        # improvement (the full framework is usable), never a failure — but the
        # dependency report in notes.md is then stale and must be re-measured.
        if "loaded" not in out:
            print(f"FAIL: {FUTURE_DEPENDENT} exited 0 without loading:\n{out}",
                  file=sys.stderr)
            return 1
        print(f"NOTE: {FUTURE_DEPENDENT} loaded in this environment — Future is "
              f"available; the dependency report in notes.md should be "
              f"re-measured.", file=sys.stderr)
        print("  (Future available: full framework usable)")
    elif "Can't locate Future.pm" in out:
        # Expected in this environment: the module fails, and it fails
        # *specifically because Future is missing* — dependency-driven, not a
        # port defect. This is the measured, documented gap.
        print(f"  {FUTURE_DEPENDENT} fails with 'Can't locate Future.pm' "
              f"(environmental, as documented)")
    else:
        # Failed for some reason *other* than the documented Future gap. That
        # could be a genuine packaging regression, so it must fail loudly: the
        # point of this probe is that the failure is attributable to Future.
        print(f"FAIL: {FUTURE_DEPENDENT} failed for a reason other than the "
              f"documented Future gap (rc={rc}):\n{out}", file=sys.stderr)
        return 1

    print(f"perl-io-async (IO::Async 0.805) consumer API: PASS "
          f"({len(found)} modules packaged, {len(FUTURE_FREE)} future-free samples load)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
