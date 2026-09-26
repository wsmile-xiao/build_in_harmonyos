#!/usr/bin/env python3
"""Consumer-side assertions for the iniconfig package.

Runs inside test_package with env="conanrun", so PYTHONPATH points at the
packaged site-packages. The package folder arrives as argv[1] and the first
checks assert provenance explicitly, so every assertion below is tied to the
packaged module rather than a build-machine copy.

Every assertion is a single `check()` call, so the reported count is a
measurement that the MANIFEST figure can be reconciled against statically.
"""
import os
import sys

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

    import iniconfig
    from iniconfig import COMMENTCHARS, IniConfig, ParseError, iscommentline

    pkg_root = os.path.realpath(os.path.dirname(iniconfig.__file__))

    # 0) Provenance: what was imported must be the packaged tree. This machine
    #    also has an importable iniconfig in the user site directory, so without
    #    this check the test would still pass with the package folder emptied —
    #    which is what the destructive negative test in CI deliberately does,
    #    and a passing test there is reported as a fake test.
    check(
        os.path.isfile(os.path.join(expected_site, "iniconfig", "__init__.py")),
        f"packaged module missing: {expected_site}/iniconfig/__init__.py",
    )
    check(
        pkg_root.startswith(expected_site + os.sep),
        f"imported iniconfig is not the packaged tree: {pkg_root}",
    )

    # 1) The imported module is the packaged tree, laid out as a module dir.
    check(os.path.isdir(pkg_root), f"iniconfig package dir missing: {pkg_root}")
    check(
        os.path.basename(pkg_root) == "iniconfig",
        f"unexpected package directory name: {pkg_root}",
    )
    check(
        os.path.isfile(os.path.join(pkg_root, "__init__.py")),
        "iniconfig/__init__.py missing",
    )

    # 2) Every module and package-data file that pytest relies on is present.
    for rel in ("_parse.py", "exceptions.py", "_version.py", "py.typed"):
        check(
            os.path.isfile(os.path.join(pkg_root, rel)),
            f"iniconfig/{rel} missing from the packaged tree",
        )

    # 3) The setuptools-scm version file carries the released version, which is
    #    what makes this package self-describing without a build backend.
    sys.path.insert(0, os.path.dirname(pkg_root))
    try:
        from iniconfig import _version

        check(
            getattr(_version, "__version__", None) == "2.3.0",
            f"unexpected version in _version.py: "
            f"{getattr(_version, '__version__', None)!r}",
        )
    finally:
        sys.path.pop(0)

    # 4) dist-info landed beside the module so tooling can discover it.
    dist_info = os.path.join(os.path.dirname(pkg_root), "iniconfig-2.3.0.dist-info")
    check(os.path.isdir(dist_info), f"dist-info missing: {dist_info}")
    check(
        os.path.isfile(os.path.join(dist_info, "METADATA")),
        "dist-info METADATA missing",
    )
    check(
        os.path.isfile(os.path.join(dist_info, "top_level.txt")),
        "dist-info top_level.txt missing",
    )

    # 5) The documented public surface (upstream __all__) is exported.
    expected_all = sorted(["IniConfig", "ParseError", "COMMENTCHARS", "iscommentline"])
    check(
        sorted(getattr(iniconfig, "__all__", [])) == expected_all,
        f"unexpected __all__: {getattr(iniconfig, '__all__', None)!r}",
    )
    for name in expected_all:
        check(hasattr(iniconfig, name), f"public name missing from iniconfig: {name}")

    # 6) Comment handling — the parser's own helpers.
    check(COMMENTCHARS == "#;", f"unexpected COMMENTCHARS: {COMMENTCHARS!r}")
    check(iscommentline("# a comment") is True, "iscommentline missed a comment")
    check(iscommentline("[section]") is False, "iscommentline misfired on a section")

    # 7) Real parsing round-trip — the reason pytest depends on this package.
    config = IniConfig("probe.cfg", data="[section]\nkey = value\nnumber = 42\n")
    check(config.path == "probe.cfg", f"unexpected path: {config.path!r}")
    check(
        dict(config.sections) == {"section": {"key": "value", "number": "42"}},
        f"unexpected parse result: {dict(config.sections)!r}",
    )
    check(
        config["section"]["key"] == "value",
        f"section key lookup wrong: {config['section']['key']!r}",
    )
    check("section" in config, "section membership check failed")

    # 8) Continuation lines and comments behave as documented.
    config2 = IniConfig(
        "probe2.cfg", data="# comment\n[other]\nmulti = line one\n  line two\n"
    )
    check(
        sorted(config2.sections) == ["other"],
        f"comment handling produced unexpected sections: {sorted(config2.sections)}",
    )
    check(
        config2["other"]["multi"] == "line one\nline two",
        f"continuation handling wrong: {config2['other']['multi']!r}",
    )

    # 9) Malformed input raises ParseError carrying path/lineno/msg.
    try:
        IniConfig("bad.cfg", data="not a section\n")
        raised = False
    except ParseError as exc:
        raised = True
        check(exc.path == "bad.cfg", f"ParseError.path wrong: {exc.path!r}")
        check(isinstance(exc.lineno, int), f"ParseError.lineno wrong: {exc.lineno!r}")
        check(bool(exc.msg), "ParseError.msg empty")
    check(raised, "ParseError was not raised for malformed input")

    # 10) parse() applies the documented inline-comment default.
    stripped = IniConfig.parse("p3.cfg", data="[s]\nk = v # inline\n")
    kept = IniConfig.parse(
        "p4.cfg", data="[s]\nk = v # inline\n", strip_inline_comments=False
    )
    check(stripped["s"]["k"] == "v", f"inline comment not stripped: {stripped['s']['k']!r}")
    check(
        kept["s"]["k"] == "v # inline",
        f"inline comment not preserved: {kept['s']['k']!r}",
    )

    # 11) A fresh interpreter can import the package on its own, i.e. the
    #     package is usable rather than only working inside this process.
    import subprocess

    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import iniconfig, iniconfig._version; "
            "print(iniconfig._version.__version__)",
        ],
        capture_output=True,
        text=True,
        # PYTHONNOUSERSITE keeps the child from silently importing the copy
        # that happens to sit in the user site directory: with it, a successful
        # import proves the package is reachable through the packaged
        # PYTHONPATH.
        env={**os.environ, "PYTHONNOUSERSITE": "1"},
    )
    check(
        probe.returncode == 0,
        f"fresh interpreter could not import iniconfig: {probe.stderr.strip()[:200]}",
    )
    check(
        probe.stdout.strip() == "2.3.0",
        f"fresh interpreter reported version {probe.stdout.strip()!r}",
    )

    print(f"INICONFIG_CONSUMER=PASS assertions={assertions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
