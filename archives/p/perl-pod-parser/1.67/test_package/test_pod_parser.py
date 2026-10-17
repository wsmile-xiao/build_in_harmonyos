#!/usr/bin/env python3
"""Consumer-side check for the packaged perl-pod-parser 1.67 (R34: real API).

Drives the packaged ``Pod::*`` modules through the perl interpreter — the same
approach as this archive's other perl-* test_packages (perl-carp). Nothing is
asserted from file presence alone: a real POD document is parsed by a real
subclass, and ``Pod::Select::podselect`` extracts real sections.

Measured facts pinned here (all verified against a local probe first):

* The callback signatures are ``command($parser, $cmd, $paragraph, $line)`` /
  ``verbatim($parser, $paragraph, $line)`` / ``textblock($parser, $paragraph,
  $line)`` and the ``$paragraph`` argument arrives as a **plain string**
  (``ref()`` is empty) — *not* a Pod::InputObjects object as one might assume
  from naming.
* ``Pod::PlainText`` reports VERSION **2.07** while every other module in the
  distribution (Parser / Select / InputObjects / Find / ParseUtils) reports
  **1.67** — an upstream inconsistency, pinned rather than assumed.
* ``Pod::Parser`` offers ``parse_from_file`` / ``parse_from_filehandle`` /
  ``parse_text`` / ``parse_paragraph`` — there is **no** ``parse_from_string``.
* ``Pod::Find`` does **not** export ``find_pod``; its useful entries are
  ``pod_where`` / ``contains_pod`` / ``pod_find``.
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


def find_perl():
    p = shutil.which("perl")
    if p:
        return p
    for cand in PERL_CANDIDATES:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def run_perl(perl, lib, program, extra_args=()):
    """Run a perl one-liner with -I<lib> and return (rc, stdout+stderr)."""
    cmd = [perl, f"-I{lib}", "-e", program, *extra_args]
    res = subprocess.run(cmd, capture_output=True, timeout=120)
    out = (res.stdout + res.stderr).decode(errors="ignore")
    return res.returncode, out


def main():
    pkg = sys.argv[1]
    perl5 = os.path.join(pkg, "lib", "perl5")
    pod_dir = os.path.join(perl5, "Pod")

    # --- packaged files -----------------------------------------------------
    modules = ("Parser.pm", "Select.pm", "PlainText.pm", "InputObjects.pm",
               "Find.pm", "ParseUtils.pm")
    for mod in modules:
        path = os.path.join(pod_dir, mod)
        if not os.path.isfile(path):
            print(f"FAIL: Pod/{mod} not found under {pod_dir}", file=sys.stderr)
            return 1

    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # --- all six modules load, and their VERSIONs ---------------------------
    rc, out = run_perl(perl, perl5, (
        'for my $m (qw(Parser Select PlainText InputObjects Find ParseUtils)) {'
        '  (my $f = "Pod::$m") =~ s/::/\\//g;'
        '  require "$f.pm";'
        '  no strict "refs";'
        '  printf "%s=%s\\n", $m, ${"Pod::${m}::VERSION"} // "undef";'
        '}'))
    if rc != 0:
        print(f"FAIL: loading modules failed:\n{out}", file=sys.stderr)
        return 1
    versions = dict(ln.split("=", 1) for ln in out.strip().splitlines() if "=" in ln)
    assert versions.get("Parser") == "1.67", versions
    assert versions.get("Select") == "1.67", versions
    assert versions.get("InputObjects") == "1.67", versions
    assert versions.get("Find") == "1.67", versions
    assert versions.get("ParseUtils") == "1.67", versions
    # upstream inconsistency: PlainText ships its own version line
    assert versions.get("PlainText") == "2.07", versions

    # --- subclass Pod::Parser and parse a real document ---------------------
    pod = ("=head1 NAME\n\nFoo - demo\n\n=head2 USAGE\n\n"
           "  indented code\n\nSome B<bold> text.\n\n=cut\n")
    tmp_pod = os.path.join(os.path.dirname(os.path.abspath(pkg)), "_probe.pod")
    with open(tmp_pod, "w", encoding="utf-8") as fh:
        fh.write(pod)
    try:
        program = (
            'package MyParser; use base qw(Pod::Parser);'
            # One log entry must stay on one line: verbatim paragraphs contain
            # embedded newlines, so they are escaped to literal \n (otherwise a
            # single entry is split across lines when Python reads stdout).
            'sub _one { my $s = shift; $s =~ s/\\r//g; $s =~ s/\\n/\\\\n/g; return $s; }'
            'sub command { my ($self,$cmd,$para,$line)=@_;'
            '  push @main::log, sprintf("CMD:%s|line=%d|ref=%s", $cmd, $line, (ref($para)||"SCALAR")); }'
            'sub verbatim { my ($self,$para,$line)=@_;'
            '  push @main::log, sprintf("VERB:%s|ref=%s", _one($para), (ref($para)||"SCALAR")); }'
            'sub textblock { my ($self,$para,$line)=@_;'
            '  push @main::log, "TXT:" . _one($para); return 1; }'
            'sub interior_sequence { my ($self,$cmd,$arg)=@_; return "*$arg*"; }'
            'package main;'
            'MyParser->new()->parse_from_file($ARGV[0]);'
            'print "$_\\n" for @main::log;')
        rc, out = run_perl(perl, perl5, program, extra_args=(tmp_pod,))
        if rc != 0:
            print(f"FAIL: parsing failed:\n{out}", file=sys.stderr)
            return 1

        log = out.strip().splitlines()
        # The =head1/=head2 directives surface as command() calls with the
        # right command name and the right POD line number.
        assert any(l.startswith("CMD:head1|") for l in log), log
        assert any(l.startswith("CMD:head2|") for l in log), log
        # $paragraph arrives as a plain SCALAR (measured) — pin it so a future
        # change to an object would be noticed.
        assert all("ref=SCALAR" in l for l in log if l.startswith(("CMD:", "VERB:"))), log
        # textblock saw the module description as text
        assert any("Foo - demo" in l for l in log), log
        # verbatim captured the indented code block
        assert any(l.startswith("VERB:") and "indented" in l for l in log), log
    finally:
        if os.path.isfile(tmp_pod):
            os.remove(tmp_pod)

    # --- Pod::Select::podselect extracts sections for real -------------------
    rc, out = run_perl(perl, perl5, (
        'use Pod::Select;'
        'my $fh; open($fh, ">", \\my $buf) or die $!;'
        'podselect({-sections => ["NAME"], -output => $fh}, $ARGV[0]);'
        'close($fh);'
        'print length($buf), "\\n", (split /\\n/, $buf)[0] // "", "\\n";'),
        extra_args=(os.path.join(pod_dir, "Find.pm"),))
    if rc != 0:
        print(f"FAIL: podselect failed:\n{out}", file=sys.stderr)
        return 1
    lines = out.strip().splitlines()
    assert int(lines[0]) > 0, out
    assert lines[1].startswith("=head1 NAME"), out

    # --- Pod::Find API surface ----------------------------------------------
    rc, out = run_perl(perl, perl5, (
        'use Pod::Find;'
        'printf "where=%s contains=%s\\n",'
        '  (defined &Pod::Find::pod_where ? "y" : "n"),'
        '  (defined &Pod::Find::contains_pod ? "y" : "n");'))
    if rc != 0:
        print(f"FAIL: Pod::Find probe failed:\n{out}", file=sys.stderr)
        return 1
    assert "where=y contains=y" in out, out

    # --- materialised podselect executable ----------------------------------
    # This block is deliberately *not* conditional. An earlier revision wrapped
    # it in ``if os.path.isfile(script):`` and therefore silently skipped the
    # one check that validates the ``.PL`` materialisation — the very defect
    # this PR's own draft forbids (forbid_2: "只断言文件存在即认为脚本可用"). A
    # missing script must fail the test, not be quietly tolerated.
    script = os.path.join(pkg, "bin", "podselect")
    if not os.path.isfile(script):
        print(f"FAIL: materialised executable missing: {script}", file=sys.stderr)
        return 1
    if not os.access(script, os.X_OK):
        print(f"FAIL: {script} is not executable", file=sys.stderr)
        return 1

    with open(script, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    first_line = text.split("\n", 1)[0]

    # ``podselect.PL`` is a MakeMaker *generator*; it must have been executed,
    # not merely copied with its first line patched. If generator code survives
    # into the package, the deliverable is the generator, not the tool.
    for marker in ("!NO!SUBS!", "!GROK!THIS!", "print OUT"):
        if marker in text:
            print(f"FAIL: {script} is the un-executed generator "
                  f"({marker!r} present)", file=sys.stderr)
            return 1

    # The first line must be a *usable* invocation form. Two are legitimate:
    #   · a ``#!`` shebang, or
    #   · the shell/perl **polyglot** that MakeMaker emits from
    #     ``$Config{startperl}``, i.e. ``: # use perl`` followed by
    #     ``eval 'exec perl -S $0 "$@"' if 0;``.
    # Measured on this platform: ``$Config{startperl}`` is ``: # use perl``, so
    # the product does NOT start with ``#!``. An earlier revision asserted
    # ``#!`` and would therefore have rejected a perfectly good script.
    if first_line.startswith("#!"):
        interp = first_line[2:].strip().split()[0]
        if not (interp and os.path.isfile(interp) and os.access(interp, os.X_OK)):
            print(f"FAIL: unusable shebang interpreter {interp!r} "
                  f"(from {first_line!r})", file=sys.stderr)
            return 1
    elif first_line.startswith(": # use perl"):
        if "exec perl" not in text.split("\n", 3)[1]:
            print(f"FAIL: polyglot header is incomplete; second line should "
                  f"re-exec perl, got {text.split(chr(10), 3)[1]!r}",
                  file=sys.stderr)
            return 1
    else:
        print(f"FAIL: unexpected first line in {script}: {first_line!r}",
              file=sys.stderr)
        return 1

    # Execute it **the way a consumer does**: through a shell. A polyglot header
    # relies on the shell's ENOEXEC fallback (the kernel rejects it, the shell
    # retries it with ``sh``), so ``subprocess.run([script, ...])`` would raise
    # "Exec format error" for a *correct* script. An earlier revision invoked
    # ``[perl, script, "-help"]`` instead, which bypasses the header entirely.
    env = dict(os.environ)
    env["PERL5LIB"] = perl5 + os.pathsep + env.get("PERL5LIB", "")
    res = subprocess.run(["/bin/sh", script, "-help"], capture_output=True,
                         timeout=120, env=env)
    help_out = (res.stdout + res.stderr).decode(errors="ignore")
    if res.returncode not in (0, 1, 2) or "podselect" not in help_out.lower():
        print(f"FAIL: podselect unusable via shell "
              f"(rc={res.returncode}):\n{help_out}", file=sys.stderr)
        return 1

    # And a real invocation: extract a section from a POD file.
    res2 = subprocess.run(["/bin/sh", script, "-sections", "NAME",
                           os.path.join(pod_dir, "Find.pm")],
                          capture_output=True, timeout=120, env=env)
    sect = (res2.stdout + res2.stderr).decode(errors="ignore")
    if res2.returncode != 0 or "=head1 NAME" not in sect:
        print(f"FAIL: podselect did not extract sections "
              f"(rc={res2.returncode}):\n{sect}", file=sys.stderr)
        return 1
    print(f"  podselect materialised (header: {first_line!r}), executed via "
          f"shell and extracted sections ({script})")

    print(f"perl-pod-parser (Pod::Parser {versions.get('Parser')}) "
          f"consumer API: PASS ({perl5})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
