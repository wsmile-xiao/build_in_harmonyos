#!/usr/bin/env python3
"""Consumer-side assertions for the lazy-loader package.

Runs inside test_package with env="conanrun", so PYTHONPATH points at the
packaged site-packages. The package folder arrives as argv[1] and the first
checks assert provenance explicitly, so every assertion below is tied to the
packaged module rather than a build-machine copy.

The functional assertions mirror the upstream contract that consumers
(scikit-image and other scientific-python projects) rely on: attach() wires
module-level __getattr__ (PEP 562), load() returns the real module and
records it in sys.modules, and the delayed-error placeholder keeps a failed
import from raising until attribute access.
"""
import os
import sys
import types

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

    import lazy_loader as lazy

    pkg_root = os.path.realpath(os.path.dirname(lazy.__file__))

    # 0) Provenance: what was imported must be the packaged tree. This
    #    machine also has an importable lazy_loader in the user site
    #    directory, so without this check the test would still pass with the
    #    package folder emptied — which is what the destructive negative test
    #    in CI deliberately does, and a passing test there is reported as a
    #    fake test.
    check(
        os.path.isfile(os.path.join(expected_site, "lazy_loader", "__init__.py")),
        f"packaged module missing: {expected_site}/lazy_loader/__init__.py",
    )
    check(
        pkg_root.startswith(expected_site + os.sep),
        f"imported lazy_loader is not the packaged tree: {pkg_root}",
    )

    # 1) The imported module is the packaged tree, shaped as a module dir,
    #    carrying the released version and the documented public surface.
    check(os.path.isdir(pkg_root), f"lazy_loader package dir missing: {pkg_root}")
    check(
        os.path.basename(pkg_root) == "lazy_loader",
        f"unexpected package directory name: {pkg_root}",
    )
    check(
        os.path.isfile(os.path.join(pkg_root, "__init__.py")),
        "lazy_loader/__init__.py missing",
    )
    check(lazy.__version__ == "0.4", f"unexpected version: {lazy.__version__!r}")
    check(
        sorted(getattr(lazy, "__all__", [])) == ["attach", "attach_stub", "load"],
        f"unexpected __all__: {getattr(lazy, '__all__', None)!r}",
    )

    # 2) The shipped test resources are packaged too (the sdist and the wheel
    #    both carry lazy_loader/tests, and upstream's own suite lives there).
    check(
        os.path.isfile(
            os.path.join(pkg_root, "tests", "test_lazy_loader.py")
        ),
        "lazy_loader/tests/test_lazy_loader.py missing from the packaged tree",
    )
    check(
        os.path.isfile(os.path.join(pkg_root, "tests", "fake_pkg", "__init__.pyi")),
        "lazy_loader/tests/fake_pkg/__init__.pyi missing from the packaged tree",
    )

    # 3) dist-info landed beside the module so tooling can discover it.
    dist_info = os.path.join(expected_site, "lazy_loader-0.4.dist-info")
    check(os.path.isdir(dist_info), f"dist-info missing: {dist_info}")
    check(
        os.path.isfile(os.path.join(dist_info, "METADATA")),
        "dist-info METADATA missing",
    )
    check(
        os.path.isfile(os.path.join(dist_info, "top_level.txt")),
        "dist-info top_level.txt missing",
    )

    # 4) load() returns the real module and records it in sys.modules; a
    #    missing module stays deferred and raises on attribute access.
    import math

    loaded = lazy.load("math")
    check(isinstance(loaded, types.ModuleType), "load() did not return a module")
    check(loaded.sin(loaded.pi) == 0.0 or abs(loaded.sin(loaded.pi)) < 1e-6,
          "loaded math module is not usable")
    check("math" in sys.modules, "load() did not register the module in sys.modules")

    not_real = lazy.load("anything_not_real_xyz")
    check(
        isinstance(not_real, lazy.DelayedImportErrorModule),
        "missing module did not produce a DelayedImportErrorModule",
    )
    try:
        not_real.pi
        raise AssertionError("attribute access on a missing module should raise")
    except ModuleNotFoundError:
        pass
    assertions += 1

    # 5) attach() wires module-level __getattr__ (PEP 562). The upstream
    #    suite (test_lazy_attach) execs the attach() call into a namespace
    #    and checks the returned triple, because attribute resolution itself
    #    requires the package to be importable — the packaged fake_pkg below
    #    is that importable package, exactly how upstream's
    #    test_attach_same_module_and_attr_name exercises the path.
    locls = {"attach": lazy.attach, "name": "mymod",
             "submods": ["mysubmodule", "anothersubmodule"],
             "myall": {"not_real_submod": ["some_var_or_func"]}}
    exec(
        "__getattr__, __lazy_dir__, __all__ = attach(name, submods, myall)",
        {}, locls,
    )
    check(callable(locls["__getattr__"]), "attach() did not return a __getattr__ hook")
    check(callable(locls["__lazy_dir__"]), "attach() did not return a __lazy_dir__ hook")
    check(
        sorted(locls["__all__"])
        == ["anothersubmodule", "mysubmodule", "some_var_or_func"],
        f"attach() derived __all__ mismatch: {sorted(locls['__all__'])!r}",
    )
    # Real attribute resolution through the packaged test package: the
    # fake_pkg's __init__ wires attach() with submod_attrs={"some_func": ...}.
    from lazy_loader.tests import fake_pkg

    check(
        isinstance(fake_pkg.some_func, types.FunctionType),
        "fake_pkg.some_func did not resolve to a function via __getattr__",
    )
    check(
        isinstance(fake_pkg.some_func, types.FunctionType),
        "second attribute access did not stay consistent",
    )
    from lazy_loader.tests.fake_pkg.some_func import some_func as direct_func

    check(
        isinstance(direct_func, types.FunctionType),
        "direct import from the attached submodule failed",
    )

    # 6) attach_stub() parses a .pyi stub for the same wiring (AST visitor
    #    over within-module imports), the path scikit-image uses.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        stub = os.path.join(tmp, "stub.pyi")
        with open(stub, "w", encoding="utf-8") as handle:
            handle.write(
                "from . import rank\n"
                "from ._gaussian import gaussian\n"
                "from .edges import sobel, scharr, prewitt, roberts\n"
            )
        get_, dir_, all_ = lazy.attach_stub("my_module", stub)
        expect = {"gaussian", "sobel", "scharr", "prewitt", "roberts", "rank"}
        check(set(dir_()) == expect, f"stub dir() mismatch: {dir_()!r}")
        check(set(all_) == expect, f"stub __all__ mismatch: {all_!r}")

    print(f"LAZY_LOADER_CONSUMER=PASS assertions={assertions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
