#!/usr/bin/env python3
"""Exercise public URL generation and package-path behavior."""

import os
from pathlib import Path

from libthumbor import CryptoURL, Url


root = Path(os.environ["LIBTHUMBOR_PACKAGE_ROOT"]).resolve()
module_path = Path(__import__("libthumbor").__file__).resolve()
assert root in module_path.parents

url = CryptoURL(key="my-security-key").generate(
    width=300,
    height=200,
    smart=True,
    image_url="images.example.com/photo.jpg",
)
assert url.startswith("/")
assert url.endswith("/300x200/smart/images.example.com/photo.jpg")

path = Url.generate_options(
    width=300,
    height=200,
    fit_in=True,
    halign="left",
    filters="brightness(10):contrast(5)",
)
assert path == "fit-in/300x200/left/filters:brightness(10):contrast(5)"
print("libthumbor 2.0.2 consumer API: PASS")
