#!/usr/bin/env python3
import pathlib
import subprocess
import sys
import tempfile


def main():
    ninja = sys.argv[1]
    out = subprocess.check_output([ninja, "--version"], text=True).strip()
    if out != "1.13.2":
        raise SystemExit(f"unexpected ninja version: {out!r}")

    with tempfile.TemporaryDirectory() as tmp:
        workdir = pathlib.Path(tmp)
        python = sys.executable.replace("\\", "/")
        (workdir / "input.txt").write_text("hello\n", encoding="utf-8")
        (workdir / "build.ninja").write_text(
            "rule copy\n"
            f"  command = \"{python}\" -c \"import pathlib; "
            "pathlib.Path('output.txt').write_text(pathlib.Path('input.txt').read_text())\"\n"
            "build output.txt: copy input.txt\n"
            "default output.txt\n",
            encoding="utf-8",
        )
        subprocess.check_call([ninja, "-v"], cwd=workdir)
        if (workdir / "output.txt").read_text(encoding="utf-8") != "hello\n":
            raise SystemExit("ninja minimal build produced unexpected output")
        subprocess.check_call([ninja, "-n"], cwd=workdir)


if __name__ == "__main__":
    main()
