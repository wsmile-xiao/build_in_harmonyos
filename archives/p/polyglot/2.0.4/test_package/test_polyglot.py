#!/usr/bin/env python3
"""Verify the packaged polyglot binary (R34 — executes the package's binary).

Test plan (all subcommands run standalone, no chess engine required):
1. make-book:  build a Polyglot book from an embedded two-game PGN
               (Scholar's mate 1-0 + Fool's mate 0-1) and assert the output
               book.bin exists, is non-empty and is a multiple of 16 bytes
               (each Polyglot book entry is exactly 16 bytes: key/move/weight/learn).
2. dump-book:  dump the book for white and black; assert exit code 0 and the
               generated line files contain move notation (e4, Qh4#).
3. no-args:    run the bare binary and assert the usage banner is printed
               (contains "PolyGlot" and version "2.0.4").
"""
import os
import subprocess
import sys
import tempfile

PGN = """[Event "Polyglot OHOS Test"]
[Site "OHOS PC"]
[Date "2026.09.03"]
[Round "1"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0

[Event "Polyglot OHOS Test"]
[Site "OHOS PC"]
[Date "2026.09.03"]
[Round "2"]
[White "Carol"]
[Black "Dave"]
[Result "0-1"]

1. f3 e5 2. g4 Qh4# 0-1
"""

failures = []


def check(label, cond, detail=""):
    if cond:
        print(f"  [OK] {label}")
    else:
        failures.append(label)
        print(f"  [FAIL] {label} {detail}")


def run(binary, args, cwd=None):
    return subprocess.run([binary] + args, capture_output=True, text=True, cwd=cwd)


def main(binary):
    assert os.path.isfile(binary), f"binary not found: {binary}"

    with tempfile.TemporaryDirectory() as workdir:
        pgn = os.path.join(workdir, "test.pgn")
        with open(pgn, "w") as f:
            f.write(PGN)

        # --- 1. make-book -------------------------------------------------
        book = os.path.join(workdir, "book.bin")
        r = run(binary, ["make-book", "-pgn", pgn, "-bin", book, "-min-game", "1"], cwd=workdir)
        size = os.path.getsize(book) if os.path.exists(book) else -1
        check("make-book exit code 0", r.returncode == 0, f"rc={r.returncode} {r.stderr[-200:]}")
        check("book.bin exists and size > 0", size > 0, f"size={size}")
        check("book.bin size is multiple of 16 (entry format)",
              size > 0 and size % 16 == 0, f"size={size}")

        # --- 2. dump-book -------------------------------------------------
        # dump-book writes book_white.txt / book_black.txt into the process cwd
        r_white = run(binary, ["dump-book", "-bin", book, "-color", "white"], cwd=workdir)
        check("dump-book white exit code 0", r_white.returncode == 0,
              f"rc={r_white.returncode} {r_white.stderr[-200:]}")
        white_txt = os.path.join(workdir, "book_white.txt")
        white_lines = ""
        if os.path.exists(white_txt):
            with open(white_txt) as f:
                white_lines = f.read()
        check("white dump contains move notation (e4/Qxf7#)",
              ("e4" in white_lines and "Qxf7" in white_lines), f"lines={white_lines!r}")

        r_black = run(binary, ["dump-book", "-bin", book, "-color", "black"], cwd=workdir)
        check("dump-book black exit code 0", r_black.returncode == 0,
              f"rc={r_black.returncode} {r_black.stderr[-200:]}")
        black_txt = os.path.join(workdir, "book_black.txt")
        black_lines = ""
        if os.path.exists(black_txt):
            with open(black_txt) as f:
                black_lines = f.read()
        check("black dump contains move notation (Qh4#)",
              "Qh4" in black_lines, f"lines={black_lines!r}")

        # --- 3. merge-book (bonus: third subcommand) -----------------------
        book2 = os.path.join(workdir, "book2.bin")
        merged = os.path.join(workdir, "merged.bin")
        run(binary, ["make-book", "-pgn", pgn, "-bin", book2, "-min-game", "1"], cwd=workdir)
        r_merge = run(binary, ["merge-book", "-in1", book, "-in2", book2, "-out", merged], cwd=workdir)
        msize = os.path.getsize(merged) if os.path.exists(merged) else -1
        check("merge-book exit code 0 and merged.bin valid",
              r_merge.returncode == 0 and msize > 0 and msize % 16 == 0,
              f"rc={r_merge.returncode} size={msize}")

    # --- 4. no-args usage banner ------------------------------------------
    r_bare = run(binary, [])
    combined = (r_bare.stdout or "") + (r_bare.stderr or "")
    check("no-args run prints PolyGlot banner",
          "PolyGlot" in combined and "2.0.4" in combined, f"out={combined!r}")

    # --- verdict -----------------------------------------------------------
    total = 9
    if failures:
        print(f"HMBS_TEST_PACKAGE_RESULT: FAIL ({len(failures)}/{total} assertions failed)")
        sys.exit(1)
    print(f"HMBS_TEST_PACKAGE_RESULT: PASS ({total}/{total} assertions passed)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_polyglot.py <path-to-polyglot-binary>")
        sys.exit(2)
    main(sys.argv[1])
