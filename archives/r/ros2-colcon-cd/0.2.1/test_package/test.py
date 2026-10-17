import pathlib
import sys

if len(sys.argv) < 2:
    raise SystemExit("Usage: python test.py <site-packages-dir>")

site_packages = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(site_packages))

import colcon_cd


module_path = pathlib.Path(colcon_cd.__file__).resolve()
if colcon_cd.__version__ != "0.2.1":
    raise RuntimeError(f"Unexpected version: {colcon_cd.__version__}")
if site_packages not in module_path.parents:
    raise RuntimeError(f"Module was not loaded from the package: {module_path}")
