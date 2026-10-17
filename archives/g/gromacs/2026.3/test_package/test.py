#!/usr/bin/env python3
"""Exercise the packaged gmx frontend with a deterministic PDB conversion."""

import os
import pathlib
import subprocess
import sys
import tempfile


checks = 0


def require(condition, message):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)


def run(command, cwd=None):
    return subprocess.run(
        command,
        cwd=cwd,
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main():
    gmx = pathlib.Path(sys.argv[1]).resolve()
    require(gmx.is_file(), f"gmx does not exist: {gmx}")

    version = run([str(gmx), "--version"])
    require(version.returncode == 0, version.stdout)
    require("GROMACS version" in version.stdout, version.stdout)
    require("2026.3" in version.stdout, version.stdout)

    pdb = (
        "ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N  \n"
        "ATOM      2  CA  ALA A   1       1.500   0.000   0.000  1.00  0.00           C  \n"
        "TER\n"
        "END\n"
    )
    with tempfile.TemporaryDirectory(prefix="gromacs-consumer-") as temp:
        work = pathlib.Path(temp)
        source = work / "input.pdb"
        output = work / "output.gro"
        source.write_text(pdb, encoding="ascii")
        editconf = run(
            [str(gmx), "editconf", "-f", str(source), "-o", str(output)],
            cwd=work,
        )
        require(editconf.returncode == 0, editconf.stdout)
        require(output.is_file(), "gmx editconf did not create output.gro")
        lines = output.read_text(encoding="utf-8").splitlines()
        require(len(lines) >= 5, f"unexpected GRO output: {lines!r}")
        require(lines[1].strip() == "2", f"unexpected GRO atom count: {lines[1]!r}")
        require(lines[2][10:15].strip() == "N", f"unexpected first atom: {lines[2]!r}")
        require(lines[3][10:15].strip() == "CA", f"unexpected second atom: {lines[3]!r}")

    print(f"PASS: packaged gmx consumer (1 flow, {checks}/10 assertions)")


if __name__ == "__main__":
    main()
