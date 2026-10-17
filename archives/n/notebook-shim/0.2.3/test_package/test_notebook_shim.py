#!/usr/bin/env python3
"""Smoke-test the installed notebook-shim package layout."""

import importlib.util
import json
import pathlib
import sys


def require_file(path):
    if not path.is_file():
        raise RuntimeError(f"Missing expected file: {path}")
    return path.read_text(encoding="utf-8")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: test_notebook_shim.py <package-folder>")

    package_folder = pathlib.Path(sys.argv[1])
    module_dir = package_folder / "lib" / "python" / "notebook_shim"

    init_file = module_dir / "__init__.py"
    version_file = module_dir / "_version.py"
    require_file(module_dir / "nbserver.py")
    require_file(module_dir / "shim.py")
    require_file(module_dir / "traits.py")

    init_module = load_module("notebook_shim_init_for_test", init_file)
    paths = init_module._jupyter_server_extension_paths()
    if paths != [{"module": "notebook_shim.nbserver"}]:
        raise RuntimeError(f"Unexpected extension paths: {paths!r}")

    version_module = load_module("notebook_shim_version_for_test", version_file)
    if version_module.__version__ != "0.2.3":
        raise RuntimeError(f"Unexpected notebook_shim version: {version_module.__version__!r}")

    config_text = require_file(
        package_folder / "etc" / "jupyter" / "jupyter_server_config.d" / "notebook_shim.json"
    )
    config = json.loads(config_text)
    enabled = config.get("ServerApp", {}).get("jpserver_extensions", {}).get("notebook_shim")
    if enabled is not True:
        raise RuntimeError("notebook_shim extension config is not enabled")

    print("notebook-shim package checks passed: 7/7")


if __name__ == "__main__":
    main()
