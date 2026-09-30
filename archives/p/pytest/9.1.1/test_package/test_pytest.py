#!/usr/bin/env python3
"""Consumer-side assertions for the pytest package.

Runs inside test_package with env="conanrun", so PYTHONPATH *and* PATH point at
the packaged tree. The assertions check both halves of the contract a consumer
such as xkeyboard-config depends on: upstream meson only registers its pytest
suite when the interpreter can `import pytest` AND a `pytest` program resolves
on PATH (`enable_pytest = python.found() and pytest.found()`).
"""
import importlib
import os
import subprocess
import sys
import tempfile

assertions = 0


def check(condition, message):
    global assertions
    if not condition:
        raise AssertionError(message)
    assertions += 1


def main():
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    package_folder = os.path.realpath(sys.argv[1])
    expected_site = os.path.join(package_folder, "lib", "python3.12", "site-packages")
    # Optional name=folder arguments for the runtime dependencies. The caller
    # passes them so this script can prove where each dependency was imported
    # from instead of trusting that the import simply succeeded.
    dep_folders = {}
    for arg in sys.argv[2:]:
        if "=" in arg:
            name, _, folder = arg.partition("=")
            dep_folders[name] = os.path.realpath(folder)

    import pytest

    pkg_root = os.path.realpath(os.path.dirname(pytest.__file__))

    # 0) Provenance: what was imported must be the packaged tree. This machine
    #    also has an importable pytest in the user site directory, so without
    #    this check the test would still pass with the package folder emptied —
    #    which is what the destructive negative test in CI deliberately does,
    #    and a passing test there is reported as a fake test.
    check(
        os.path.isfile(os.path.join(expected_site, "pytest", "__init__.py")),
        f"packaged module missing: {expected_site}/pytest/__init__.py",
    )
    check(
        pkg_root.startswith(expected_site + os.sep),
        f"imported pytest is not the packaged tree: {pkg_root}",
    )

    # 0b) The runtime dependencies must come from the packaged chain too. This
    #     is the regression guard for the failure CI caught and this machine
    #     did not: the four dependencies were listed under Conan's "Skipped
    #     binaries", so their PYTHONPATH entries never reached a consumer, and
    #     `import pytest` died with "No module named 'pluggy'". Locally the
    #     user-site copy answered the import instead, so the run looked green.
    #     The caller sets PYTHONNOUSERSITE=1; re-check it here so a future edit
    #     that drops it fails loudly instead of silently restoring the mask.
    check(
        os.environ.get("PYTHONNOUSERSITE") == "1",
        "PYTHONNOUSERSITE is not set: a user-site copy can mask a missing dependency",
    )
    check(
        bool(dep_folders),
        "no dependency folders were passed: provenance of the runtime "
        "dependencies cannot be verified",
    )
    for name, folder in sorted(dep_folders.items()):
        module = importlib.import_module(name)
        origin = os.path.realpath(getattr(module, "__file__", "") or "")
        check(
            origin.startswith(folder + os.sep),
            f"{name} was imported from outside its packaged folder: "
            f"{origin} (expected under {folder})",
        )

    # 1) The imported module is the packaged tree, shaped as a module dir.
    check(os.path.isdir(pkg_root), f"pytest package dir missing: {pkg_root}")
    check(
        os.path.basename(pkg_root) == "pytest",
        f"unexpected package directory name: {pkg_root}",
    )
    check(
        os.path.isfile(os.path.join(pkg_root, "__init__.py")),
        "pytest/__init__.py missing",
    )

    # 2) The engine package sits beside it, and the module-level py.py shim that
    #    pytest ships (pylib's replacement) is present — `_pytest` imports `py`
    #    at collection time, so without it every run dies before any test.
    site = os.path.dirname(pkg_root)
    check(os.path.isdir(os.path.join(site, "_pytest")), "_pytest package missing")
    check(
        os.path.isfile(os.path.join(site, "py.py")),
        "pytest's py.py compatibility shim missing (import py would fail)",
    )
    check(
        os.path.isdir(os.path.join(site, "_pytest", "_py")),
        "_pytest/_py vendored pylib replacement missing",
    )

    # 3) The released version is baked in and reported consistently.
    check(
        pytest.__version__ == "9.1.1",
        f"unexpected pytest version: {pytest.__version__!r}",
    )
    from _pytest import __version__ as engine_version

    check(
        engine_version == "9.1.1",
        f"_pytest.__version__ disagrees: {engine_version!r}",
    )

    # 4) dist-info landed beside the module, including console_scripts metadata.
    dist_info = os.path.join(site, "pytest-9.1.1.dist-info")
    check(os.path.isdir(dist_info), f"dist-info missing: {dist_info}")
    check(
        os.path.isfile(os.path.join(dist_info, "METADATA")),
        "dist-info METADATA missing",
    )
    entry_points = os.path.join(dist_info, "entry_points.txt")
    check(os.path.isfile(entry_points), "dist-info entry_points.txt missing")
    if os.path.isfile(entry_points):
        content = open(entry_points, encoding="utf-8").read()
        check("pytest" in content, "entry_points.txt does not declare pytest")

    # 5) The py.py shim is importable and wires up the vendored replacements.
    import py  # noqa: F401  (pytest's shim, not the pylib package)

    check(hasattr(py, "path"), "py shim did not expose py.path")
    check(hasattr(py, "error"), "py shim did not expose py.error")

    # 6) The console entry point is reachable through PATH and really runs —
    #    this is the half of meson's probe that PYTHONPATH alone cannot satisfy.
    import shutil

    pytest_bin = shutil.which("pytest")
    check(pytest_bin is not None, "pytest program not found on PATH")
    if pytest_bin:
        check(
            os.access(pytest_bin, os.X_OK),
            f"pytest program on PATH is not executable: {pytest_bin}",
        )
        with open(pytest_bin, encoding="utf-8") as handle:
            shebang = handle.readline().strip()
        check(
            shebang.startswith("#!") and "python" in shebang,
            f"pytest program does not start with a python shebang: {shebang!r}",
        )
        # The packaged script carries the standard `#!/usr/bin/env python3`
        # shebang, so running it directly also needs a python3 on PATH. The CI
        # sandbox PATH is minimal and need not provide one — that would be a
        # property of the environment, not of this package — so the direct
        # invocation is used only when a python3 resolves; otherwise the same
        # script is executed through this interpreter, which is how the
        # pygments test_package runs its console script too. Either way the
        # script's own code path runs: an entry point that is merely present
        # but broken still fails here.
        python3_on_path = shutil.which("python3") is not None
        argv = [pytest_bin] if python3_on_path else [sys.executable, pytest_bin]
        print(
            "entry point invocation: "
            + ("direct (shebang)" if python3_on_path else "through the interpreter")
            + " " + " ".join(argv)
        )
        probe = subprocess.run(argv + ["--version"], capture_output=True, text=True)
        check(
            probe.returncode == 0,
            f"pytest --version failed: {(probe.stderr or '').strip()[:160]}",
        )
        check(
            "9.1.1" in (probe.stdout + probe.stderr),
            f"unexpected pytest --version output: {probe.stdout.strip()!r}",
        )

    # 7) The documented public surface is exported.
    for name in ("main", "raises", "fixture", "mark", "skip", "fail", "approx",
                 "importorskip", "ExitCode", "Config", "Parser"):
        check(hasattr(pytest, name), f"public name missing from pytest: {name}")

    # 8) A real collection + run through the module entry point, i.e. the
    #    runner actually works rather than merely importing.
    with tempfile.TemporaryDirectory(prefix="pytest-consumer-") as workdir:
        sample = os.path.join(workdir, "test_sample.py")
        with open(sample, "w", encoding="utf-8") as handle:
            handle.write(
                "import pytest\n"
                "\n"
                "def test_ok():\n"
                "    assert 1 + 1 == 2\n"
                "\n"
                "def test_parametrized():\n"
                "    assert pytest.approx(0.1 + 0.2, abs=1e-9) == 0.3\n"
            )
        run = subprocess.run(
            [
                sys.executable, "-m", "pytest", sample,
                "-q", "--no-header", "-p", "no:cacheprovider",
                "--basetemp", os.path.join(workdir, "bt"),
            ],
            capture_output=True,
            text=True,
            cwd=workdir,
        )
        combined = run.stdout + run.stderr
        check(
            run.returncode == 0,
            f"running a sample test failed (rc={run.returncode}): {combined[-300:]}",
        )
        check(
            "2 passed" in combined,
            f"expected 2 passing cases, got: {combined[-200:]!r}",
        )

    # 9) The in-process API a consumer recipe uses works too.
    check(
        pytest.ExitCode.OK.value == 0,
        f"unexpected ExitCode.OK: {pytest.ExitCode.OK!r}",
    )

    print(f"PYTEST_CONSUMER=PASS assertions={assertions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
