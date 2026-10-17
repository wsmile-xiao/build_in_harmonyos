#!/usr/bin/env python3
"""Consumer-side assertions for the interrogate package.

Runs inside test_package with env="conanrun", so PYTHONPATH *and* PATH point
at the packaged tree. The assertions check both halves of the contract an
application consumer depends on: the importable module (via PYTHONPATH) and
the program (via PATH). The package folder arrives as argv[1], optional
name=folder arguments carry the runtime dependencies so each import's
provenance can be asserted instead of trusted.
"""
import importlib
import os
import shutil
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
    global assertions
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    package_folder = os.path.realpath(sys.argv[1])
    expected_site = os.path.join(package_folder, "lib", "python3.12", "site-packages")
    dep_folders = {}
    for arg in sys.argv[2:]:
        if "=" in arg:
            name, _, folder = arg.partition("=")
            dep_folders[name] = os.path.realpath(folder)

    import interrogate
    import py
    from py import io as py_io

    pkg_root = os.path.realpath(os.path.dirname(interrogate.__file__))

    # 0) Provenance: what was imported must be the packaged tree. Without
    #    this check a user-site copy could answer the import and the test
    #    would still pass with the package folder emptied -- exactly what
    #    the CI destructive negative test does on purpose.
    check(
        os.path.isfile(os.path.join(expected_site, "interrogate", "__init__.py")),
        f"packaged module missing: {expected_site}/interrogate/__init__.py",
    )
    check(
        pkg_root.startswith(expected_site + os.sep),
        f"imported interrogate is not the packaged tree: {pkg_root}",
    )
    check(
        os.environ.get("PYTHONNOUSERSITE") == "1",
        "PYTHONNOUSERSITE is not set: a user-site copy can mask a missing module",
    )

    # 0b) The vendored py tree ships inside the package and answers the
    #     `from py import io` import interrogate/utils.py does at module
    #     top level. Its provenance is asserted the same way.
    py_root = os.path.realpath(os.path.dirname(py.__file__))
    check(
        py_root.startswith(expected_site + os.sep),
        f"vendored py is not inside the packaged tree: {py_root}",
    )
    check(
        os.path.isfile(os.path.join(expected_site, "py", "_io", "terminalwriter.py")),
        "vendored py/_io/terminalwriter.py missing (OutputFormatter dependency)",
    )
    check(hasattr(py_io, "TerminalWriter"), "py.io.TerminalWriter not exposed")

    # 0c) The runtime dependencies must come from their own package
    #     folders -- the regression guard for the "Skipped binaries" failure
    #     mode the pytest/9.1.1 recipe measured. NOTE: the attrs package
    #     ships its module under the name `attr` (the conan recipe stages
    #     src/attr only), which is also the name interrogate's config.py
    #     imports; importing the dist name `attrs` instead would resolve to
    #     a host interpreter copy (attrs is a dependency of conan itself)
    #     and defeat the provenance check.
    check(
        bool(dep_folders),
        "no dependency folders were passed: provenance cannot be verified",
    )
    import_names = {"attrs": "attr"}
    for name, folder in sorted(dep_folders.items()):
        module = importlib.import_module(import_names.get(name, name))
        origin = os.path.realpath(getattr(module, "__file__", "") or "")
        check(
            origin.startswith(folder + os.sep) or origin == folder,
            f"{name} was imported from outside its package folder: "
            f"{origin} (expected under {folder})",
        )

    # 1) Module surface: version and the submodules the CLI drives.
    check(interrogate.__version__ == "1.7.0",
          f"unexpected version: {interrogate.__version__!r}")
    from interrogate import badge_gen, cli, config, coverage, utils, visit

    check(callable(cli.main), "cli.main is not callable")
    check(hasattr(config, "InterrogateConfig"), "InterrogateConfig missing")
    check(hasattr(coverage, "InterrogateCoverage"), "InterrogateCoverage missing")
    check(hasattr(utils.OutputFormatter, "get_table_formatter"),
          "OutputFormatter.get_table_formatter missing")

    # 2) dist-info landed beside the module with the console_scripts entry.
    dist_info = os.path.join(expected_site, "interrogate-1.7.0.dist-info")
    check(os.path.isdir(dist_info), f"dist-info missing: {dist_info}")
    entry_points = os.path.join(dist_info, "entry_points.txt")
    check(os.path.isfile(entry_points), "dist-info entry_points.txt missing")
    if os.path.isfile(entry_points):
        content = open(entry_points, encoding="utf-8").read()
        check("interrogate = interrogate.cli:main" in content,
              "entry_points.txt does not declare the interrogate command")

    # 3) The badge template directory travels with the package
    #    (badge_gen serves it through importlib.resources).
    badge_dir = os.path.join(pkg_root, "badge")
    check(os.path.isdir(badge_dir), f"badge template directory missing: {badge_dir}")
    check(
        any(name.endswith("-style.svg") for name in os.listdir(badge_dir)),
        "badge templates (svg) missing from the packaged tree",
    )

    # 4) The console entry point resolves through PATH and really runs --
    #    --version exercises click's version_option, and a coverage run on
    #    a crafted tree asserts both exit codes of the fail-under contract.
    interrogate_bin = shutil.which("interrogate")
    check(interrogate_bin is not None, "interrogate program not found on PATH")
    if interrogate_bin:
        check(os.access(interrogate_bin, os.X_OK),
              f"interrogate program on PATH is not executable: {interrogate_bin}")
        with open(interrogate_bin, encoding="utf-8") as handle:
            shebang = handle.readline().strip()
        check(shebang.startswith("#!") and "python" in shebang,
              f"interrogate program lacks a python shebang: {shebang!r}")
        python3_on_path = shutil.which("python3") is not None
        argv = [interrogate_bin] if python3_on_path else [sys.executable, interrogate_bin]
        version_out = subprocess.run(
            argv + ["--version"], capture_output=True, text=True)
        check(version_out.returncode == 0,
              f"interrogate --version failed: {version_out.stderr[-200:]}")
        check("1.7.0" in version_out.stdout,
              f"--version did not report 1.7.0: {version_out.stdout!r}")

    with tempfile.TemporaryDirectory() as tmp:
        good = os.path.join(tmp, "good.py")
        with open(good, "w", encoding="utf-8") as handle:
            handle.write(
                '"""A fully documented sample module."""\n'
                "\n"
                "def documented_function():\n"
                '    """A documented function."""\n'
                "    return 42\n"
            )
        bad = os.path.join(tmp, "bad.py")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("def undocumented():\n    return 1\n")

        run_argv = argv if interrogate_bin else [sys.executable, "-m", "interrogate"]
        ok_run = subprocess.run(
            run_argv + ["-f", "80", good], capture_output=True, text=True)
        check(ok_run.returncode == 0,
              f"documented file should pass fail-under: {ok_run.stdout[-200:]}")
        check("actual: 100.0%" in ok_run.stdout,
              f"coverage percentage missing from output: {ok_run.stdout!r}")
        bad_run = subprocess.run(
            run_argv + ["-f", "80", bad], capture_output=True, text=True)
        check(bad_run.returncode == 1,
              f"undocumented file should fail fail-under (rc=1): rc={bad_run.returncode}")

        # 5) Badge generation writes a real SVG through the packaged
        #    templates (the -g/--generate-badge path).
        badge_path = os.path.join(tmp, "badge.svg")
        badge_run = subprocess.run(
            run_argv + ["-g", badge_path, good],
            capture_output=True, text=True,
        )
        check(badge_run.returncode == 0,
              f"badge generation failed: {badge_run.stderr[-200:]}")
        check(os.path.isfile(badge_path), "badge file was not written")
        if os.path.isfile(badge_path):
            with open(badge_path, encoding="utf-8") as handle:
                badge_content = handle.read()
            check(
                badge_content.lstrip().startswith("<svg") and "</svg>" in badge_content,
                f"badge content is not a complete svg document: "
                f"{badge_content[:80]!r}",
            )
            check(
                "interrogate" in badge_content.lower(),
                "badge text label does not mention interrogate",
            )

    print(f"INTERROGATE_CONSUMER=PASS assertions={assertions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
