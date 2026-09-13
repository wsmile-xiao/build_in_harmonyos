#!/usr/bin/env python3
"""Consumer test driver for coco-cpp/20120102 (runs the packaged cococpp).

Usage: python3 test_cococpp.py <package_folder> <work_dir>
Generates a scanner/parser from an embedded real grammar and asserts the
generated sources.
"""
import os
import shutil
import sys

SAMPLE_ATG = """COMPILER Sample
CHARACTERS
  letter = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz".
  digit = "0123456789".
TOKENS
  ident = letter { letter | digit }.
  number = digit { digit }.
IGNORE "\\n" + "\\r" + "\\t" + " "
PRODUCTIONS
  Sample = { ident | number } .
END Sample.
"""


def main():
    pkg_folder, work = sys.argv[1], sys.argv[2]
    tool = os.path.join(pkg_folder, "bin", "cococpp")
    resdir = os.path.join(pkg_folder, "res")

    # Coco reads the frame files from the grammar's directory
    for frame in ("Scanner.frame", "Parser.frame", "Copyright.frame"):
        shutil.copy(os.path.join(resdir, frame), work)
    atg = os.path.join(work, "Sample.atg")
    with open(atg, "w") as f:
        f.write(SAMPLE_ATG)

    import subprocess
    subprocess.run([tool, atg], check=True, cwd=work)

    scanner = os.path.join(work, "Scanner.cpp")
    parser = os.path.join(work, "Parser.cpp")
    for gen in (scanner, parser):
        assert os.path.isfile(gen), "%s not generated" % os.path.basename(gen)
    with open(scanner) as f:
        stext = f.read()
    with open(parser) as f:
        ptext = f.read()
    assert "Scanner" in stext, "scanner content unexpected"
    assert "Sample" in ptext, "parser content lacks grammar name"

    print("cococpp consumer test: OK (grammar -> scanner+parser generated)")


if __name__ == "__main__":
    main()
