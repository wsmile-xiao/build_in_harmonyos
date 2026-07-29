#!/usr/bin/env python3
"""Smoke tests for the packaged latexdiff tools."""
import os
import shutil
import stat
import subprocess
import sys
import tempfile


def assert_executable(path):
    if not os.path.isfile(path):
        raise AssertionError(f"Missing file: {path}")
    mode = os.stat(path).st_mode
    if not mode & stat.S_IXUSR:
        raise AssertionError(f"File is not executable: {path}")


def run_command(args, *, cwd=None, env=None):
    try:
        return subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=60,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(f"Command timed out after 60 seconds: {args[0]}") from exc


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_latexdiff.py <package-folder>", file=sys.stderr)
        return 2

    pkg = sys.argv[1]
    bin_dir = os.path.join(pkg, "bin")
    libexec = os.path.join(pkg, "libexec", "latexdiff")
    man_dir = os.path.join(pkg, "share", "man", "man1")

    for command in ("latexdiff", "latexdiff-fast", "latexdiff-vc", "latexrevise"):
        wrapper_path = os.path.join(bin_dir, command)
        assert_executable(wrapper_path)
        with open(wrapper_path, "r", encoding="utf-8") as handle:
            shebang = handle.readline().rstrip("\r\n")
        if shebang != "#!/bin/sh":
            raise AssertionError(f"Unexpected wrapper shebang: {command}: {shebang}")

    for script in ("latexdiff-so", "latexdiff-fast", "latexdiff-vc", "latexrevise"):
        script_path = os.path.join(libexec, script)
        assert_executable(script_path)
        with open(script_path, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        if "github.com/ftilmann/latexdiff" not in content:
            raise AssertionError(f"Unexpected script contents: {script}")

    latexdiff_script = os.path.join(libexec, "latexdiff-so")
    with open(latexdiff_script, "r", encoding="utf-8", errors="replace") as handle:
        latexdiff_content = handle.read()
    if "LATEXDIFF 1.4.0" not in latexdiff_content:
        raise AssertionError("latexdiff version marker not found")

    for manpage in ("latexdiff.1", "latexdiff-vc.1", "latexrevise.1"):
        if not os.path.isfile(os.path.join(man_dir, manpage)):
            raise AssertionError(f"Missing manpage: {manpage}")

    perl = shutil.which("perl")
    if not perl:
        raise AssertionError("perl is required to execute latexdiff tests")

    result = run_command([os.path.join(bin_dir, "latexdiff"), "--version"])
    if result.returncode != 0 or "LATEXDIFF 1.4.0" not in result.stdout:
        raise AssertionError(f"Unexpected latexdiff --version output: {result.stdout}")

    path_env = os.environ.copy()
    path_env["PATH"] = bin_dir + os.pathsep + path_env.get("PATH", "")
    with tempfile.TemporaryDirectory() as unrelated_cwd:
        path_result = run_command(
            ["latexdiff", "--version"],
            cwd=unrelated_cwd,
            env=path_env,
        )
    if path_result.returncode != 0 or "LATEXDIFF 1.4.0" not in path_result.stdout:
        raise AssertionError(
            f"PATH invocation did not resolve the packaged wrapper: {path_result.stdout}"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        old_tex = os.path.join(tmpdir, "old.tex")
        new_tex = os.path.join(tmpdir, "new.tex")
        with open(old_tex, "w", encoding="utf-8") as handle:
            handle.write("\\documentclass{article}\n\\begin{document}\nOld sentence.\n\\end{document}\n")
        with open(new_tex, "w", encoding="utf-8") as handle:
            handle.write("\\documentclass{article}\n\\begin{document}\nNew sentence.\n\\end{document}\n")

        diff = run_command([os.path.join(bin_dir, "latexdiff"), old_tex, new_tex])
        if diff.returncode != 0:
            raise AssertionError(f"latexdiff failed: {diff.stdout}")

    required_diff_markers = [
        "\\DIFdelbegin",
        "\\DIFaddbegin",
        "\\DIFdel{Old",
        "\\DIFadd{New",
        "sentence.",
    ]
    missing = [marker for marker in required_diff_markers if marker not in diff.stdout]
    if missing:
        raise AssertionError(f"latexdiff output missing markers {missing}: {diff.stdout}")

    print("PASS: latexdiff scripts, wrappers, manpages, version output, and TeX diff are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
