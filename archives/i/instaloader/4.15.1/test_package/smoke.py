#!/usr/bin/env python3
"""Consumer test: import the installed package and exercise real public APIs."""
import os
import sys

site_packages = sys.argv[1]
assert os.path.isdir(site_packages)
assert os.path.isfile(os.path.join(site_packages, "instaloader", "__init__.py"))
assert sys.version_info >= (3, 9)

import instaloader

assert instaloader.__version__ == "4.15.1"
assert callable(instaloader.Instaloader)
loader = instaloader.Instaloader(
    dirname_pattern="{target}",
    filename_pattern="{date_utc:%Y-%m-%d}",
)
assert loader.dirname_pattern == "{target}"
assert callable(instaloader.load_structure)
assert callable(instaloader.save_structure_to_file)
print("instaloader consumer API smoke: OK")
