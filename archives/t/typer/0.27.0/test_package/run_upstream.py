#!/usr/bin/env python3
"""Run the upstream pytest suite packaged under upstream_tests/.

The upstream typer repo ships tests/ and docs_src/ with ~1400 pytest
cases.  This runner:

1. Installs typer's runtime deps (rich, shellingham, annotated-doc,
   click) plus the test deps (pytest, coverage, pytest-cov,
   pytest-xdist, dirty-equals) into a private target dir on PYTHONPATH,
   so we don't touch the system site-packages.
2. Drops a sitecustomize.py next to the suite that stubs
   shellingham.detect_shell — on HarmonyOS PC the sandbox blocks
   reads of /proc/1/stat which shellingham walks.  This stub is
   auto-loaded by every child Python process (e.g. the
   `python -m coverage run` subprocesses spawned by the suite).
3. Exports COLUMNS=200 so rich doesn't truncate file names in narrow
   test-runner terminals (e.g. test_file_error expects the full file
   path in the error output).
4. Runs pytest from inside upstream_tests/ so cases that load fixtures
   from cwd find them.

Usage:
    python3 run_upstream.py <upstream_tests_dir> <pkg_dir>
"""
import os
import subprocess
import sys


# Runtime deps declared in typer's pyproject.toml [project.dependencies].
# Version constraints loosened to "any" so the HarmonyOS PC PyPI mirror
# (which lags upstream) can satisfy them.  The mirror hosts recent-enough
# versions for the suite to run.
RUNTIME_DEPS = [
    "rich",
    "shellingham",
    "annotated-doc",
    "click",
]

# Test deps declared in typer's pyproject.toml [tool.pdm.dev-dependencies].
TEST_DEPS = [
    "pytest",
    "coverage",
    "pytest-cov",
    "pytest-xdist",
    "pytest-sugar",
    "dirty-equals",
    "typing_extensions",
]

# sitecustomize.py stub content — auto-loaded by CPython at startup.
SITECUSTOMIZE = '''"""Auto-loaded stub that bypasses shellingham /proc access.

On HarmonyOS PC the sandbox blocks reads of /proc/1/stat which
shellingham.detect_shell walks while detecting the current shell.
We stub detect_shell before any typer import triggers the walk.
"""
try:
    import shellingham
except ImportError:
    shellingham = None

if shellingham is not None and not getattr(
    shellingham, "_ohos_stubbed", False
):
    def _stub_detect_shell(pid=None, max_depth=10):
        return ("bash", "/bin/bash")

    shellingham.detect_shell = _stub_detect_shell
    shellingham._ohos_stubbed = True
'''


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <upstream_tests_dir> <pkg_dir>",
              file=sys.stderr)
        return 2

    upstream = sys.argv[1]
    pkg_dir = sys.argv[2]

    if not os.path.isdir(upstream):
        print(f"upstream_tests dir not found: {upstream}", file=sys.stderr)
        return 2

    # Some upstream docs_src tests (e.g.
    # docs_src/multiple_values/arguments_with_multiple_values/tutorial001_py310.py)
    # call ``path.is_file()`` on ``README.md`` and ``pyproject.toml`` in
    # the current working directory.  The packaged upstream_tests/ ships
    # ``pyproject.toml`` but not ``README.md``; create a placeholder so
    # those tests don't spuriously fail.
    readme = os.path.join(upstream, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w") as f:
            f.write("# typer placeholder README for upstream test run\n")

    # 1. Install runtime + test deps into a private target dir.
    deps = RUNTIME_DEPS + TEST_DEPS
    target = os.path.join(upstream, ".ohos-deps")
    os.makedirs(target, exist_ok=True)
    pip_cmd = [
        sys.executable, "-m", "pip", "install",
        "--no-build-isolation",
        "--target", target,
    ] + deps
    print(f"[run_upstream] installing {len(deps)} deps into {target}")
    proc = subprocess.run(pip_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"[run_upstream] pip install failed (rc={proc.returncode}):",
              file=sys.stderr)
        print(proc.stderr[-1500:], file=sys.stderr)
        return 1
    print(f"[run_upstream] deps installed: {len(proc.stdout.splitlines())} lines")

    # 2. Drop sitecustomize.py so child processes auto-stub shellingham.
    sc_path = os.path.join(target, "sitecustomize.py")
    with open(sc_path, "w") as f:
        f.write(SITECUSTOMIZE)
    print(f"[run_upstream] sitecustomize.py written to {sc_path}")

    # 3. Build the child-process environment.
    env = dict(os.environ)
    # Put the deps target + the packaged typer on PYTHONPATH so the suite
    # imports the packaged typer (R34: tests must exercise the real API).
    pp_parts = [target, pkg_dir]
    existing_pp = env.get("PYTHONPATH", "")
    if existing_pp:
        pp_parts.append(existing_pp)
    env["PYTHONPATH"] = os.path.pathsep.join(pp_parts)
    # rich uses COLUMNS to wrap output; force a wide terminal so file
    # paths aren't truncated (test_file_error expects the full path).
    env["COLUMNS"] = "200"
    # pytest's tmpdir factory skips the rootdir-ownership check when
    # we point --basetemp at a dir owned by the current user.
    basetemp = os.path.join(upstream, ".ohos-basetemp")
    os.makedirs(basetemp, exist_ok=True)

    # 4. Run the full upstream suite (tests/ + docs_src/).
    #    Use -p no:xdist (serial) so the coverage data file isn't
    #    contended by parallel workers writing to the same path.
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        os.path.join(upstream, "tests"),
        os.path.join(upstream, "docs_src"),
        "-q", "--no-header",
        "--no-cov",
        "--basetemp", basetemp,
        "-o", "addopts=",
        "-p", "no:cacheprovider",
        "-p", "no:xdist",
    ]
    print(f"[run_upstream] running: {' '.join(pytest_cmd)}")
    proc = subprocess.run(pytest_cmd, env=env, cwd=upstream)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
