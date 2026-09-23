#!/usr/bin/env python3
"""Verify the packaged poster binary (R34 — executes the package's binary).

poster is a stdin->stdout PostScript pipeline tool, so every assertion below
runs the real binary in pipe mode (PS in -> PS out) and inspects the emitted
PostScript structure (assertion targets were derived from observed behaviour
of the tool, not guessed):

1. default run:     A4 input | poster            -> rc=0, PS header, single
                    page (%%Pages: 1), A4 media/bounding box
2. tile run:        poster -p2x2A4               -> rc=0, %%Pages: 4, four
                    %%Page: (row,col) tile marks, "in 2x2 tiles" comment
3. media switch:    poster -mA2                  -> rc=0, media/bounding box
                    switch from A4 (595x842) to A2 (1190x1684)
4. scale run:       poster -s2 -mA4              -> rc=0, magnification 2,
                    4x2 tiles (%%Pages: 8)

Note: poster's tmpinfile() honours the TEMP env var (not TMPDIR); on OHOS
/tmp is read-only (E002), so the test exports TEMP to its workdir.
"""
import os
import subprocess
import sys
import tempfile

PS_INPUT = """\
%!PS-Adobe-3.0
%%BoundingBox: 0 0 595 842
%%Pages: 1
%%Page: 1 1
10 10 moveto 300 400 lineto stroke
/Helvetica findfont 24 scalefont setfont 50 700 moveto (Hello Poster) show
showpage
%%EOF
"""

failures = []


def check(label, cond, detail=""):
    if cond:
        print(f"  [OK] {label}")
    else:
        failures.append(label)
        print(f"  [FAIL] {label} {detail}")


def run_pipe(binary, args, ps_text, workdir):
    """Run poster in stdin->stdout pipe mode with TEMP redirected to workdir."""
    env = dict(os.environ)
    env["TEMP"] = workdir  # poster uses TEMP (not TMPDIR); /tmp is RO on OHOS
    return subprocess.run(
        [binary] + args,
        input=ps_text,
        capture_output=True,
        text=True,
        env=env,
        cwd=workdir,
    )


def count_tile_marks(out):
    return out.count("%%Page: (")


def main(binary):
    assert os.path.isfile(binary), f"binary not found: {binary}"

    with tempfile.TemporaryDirectory() as workdir:

        # --- 1. default run (implicit -mA4, 1:1 scale) --------------------
        r = run_pipe(binary, [], PS_INPUT, workdir)
        check("default run exit code 0", r.returncode == 0,
              f"rc={r.returncode} stderr={r.stderr[-200:]!r}")
        out = r.stdout or ""
        check("default output is PostScript (%!PS-Adobe header)",
              out.startswith("%!PS-Adobe"), out[:60])
        check("default output single page (%%Pages: 1)",
              "%%Pages: 1" in out)
        check("default A4 bounding box (0 0 595 842)",
              "%%BoundingBox: 0 0 595 842" in out)
        check("default A4 media declaration",
              "%%DocumentMedia: A4 595 842" in out)
        check("default output has Prolog/EndComments structure",
              "%%BeginProlog" in out and "%%EndComments" in out)

        # --- 2. tile run -p2x2A4 ------------------------------------------
        r = run_pipe(binary, ["-p2x2A4"], PS_INPUT, workdir)
        check("-p2x2A4 exit code 0", r.returncode == 0,
              f"rc={r.returncode} stderr={r.stderr[-200:]!r}")
        out = r.stdout or ""
        check("-p2x2A4 emits 4 pages (%%Pages: 4)",
              "%%Pages: 4" in out)
        check("-p2x2A4 emits 4 tile marks (%%Page: (r,c))",
              count_tile_marks(out) == 4, f"got {count_tile_marks(out)}")
        check("-p2x2A4 header says 2x2 tiles",
              "in 2x2 tiles" in out)
        check("-p2x2A4 magnification reported (1.8)",
              "with 1.8 magnification" in out)

        # --- 3. media switch -mA2 ------------------------------------------
        r = run_pipe(binary, ["-mA2"], PS_INPUT, workdir)
        check("-mA2 exit code 0", r.returncode == 0,
              f"rc={r.returncode} stderr={r.stderr[-200:]!r}")
        out = r.stdout or ""
        check("-mA2 declares A2 media (1190x1684)",
              "%%DocumentMedia: A2 1190 1684" in out)
        check("-mA2 switches bounding box to A2",
              "%%BoundingBox: 0 0 1190 1684" in out)

        # --- 4. scale run -s2 ----------------------------------------------
        r = run_pipe(binary, ["-s2", "-mA4"], PS_INPUT, workdir)
        check("-s2 exit code 0", r.returncode == 0,
              f"rc={r.returncode} stderr={r.stderr[-200:]!r}")
        out = r.stdout or ""
        check("-s2 header says magnification 2",
              "with 2 magnification" in out)
        check("-s2 tiles the scaled poster (4x2 tiles)",
              "in 4x2 tiles" in out)
        check("-s2 emits 8 tile pages (%%Pages: 8)",
              "%%Pages: 8" in out and count_tile_marks(out) == 8,
              f"marks={count_tile_marks(out)}")

    # --- verdict -----------------------------------------------------------
    total = 18
    if failures:
        print(f"HMBS_TEST_PACKAGE_RESULT: FAIL ({len(failures)}/{total} assertions failed)")
        sys.exit(1)
    print(f"HMBS_TEST_PACKAGE_RESULT: PASS ({total}/{total} assertions passed)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_poster.py <path-to-poster-binary>")
        sys.exit(2)
    main(sys.argv[1])
