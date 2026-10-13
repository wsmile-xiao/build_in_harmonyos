#!/usr/bin/env python3
"""Verify the v0.7.6 LNGS_LITE/core-target separation in the official archive."""
from hashlib import sha256
from io import BytesIO
import re
import tarfile
from urllib.error import URLError
from urllib.request import urlopen

URL = "https://codeload.github.com/mbits-os/lngs/tar.gz/refs/tags/v0.7.6"
EXPECTED = "85c9fd3afd5b6d5446a294f4de11221ae7fa160a62d1115a7ea0c1af17633a0b"
paths = (
    "CMakeLists.txt",
    "libs/CMakeLists.txt",
    "libs/liblngs/CMakeLists.txt",
    "libs/liblngs_lite/CMakeLists.txt",
    "app/CMakeLists.txt",
)
try:
    archive = urlopen(URL, timeout=120).read()
except (URLError, OSError) as exc:
    raise SystemExit(f"failed to download official v0.7.6 archive from {URL}: {exc}") from exc
actual = sha256(archive).hexdigest()
if actual != EXPECTED:
    raise SystemExit(f"archive SHA-256 mismatch: {actual}")
with tarfile.open(fileobj=BytesIO(archive), mode="r:gz") as tf:
    members = tf.getmembers()
    roots = {member.name.split("/", 1)[0] for member in members if "/" in member.name}
    if len(roots) != 1:
        raise SystemExit(f"expected one codeload root directory, found: {sorted(roots)}")
    root = roots.pop()
    files = {}
    for suffix in paths:
        expected = f"{root}/{suffix}"
        for member in members:
            if member.name == expected:
                stream = tf.extractfile(member)
                if stream:
                    try:
                        files[suffix] = stream.read().decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise SystemExit(f"non-UTF-8 CMake source {member.name}: {exc}") from exc
                break
missing = set(paths) - set(files)
if missing:
    raise SystemExit(f"missing CMake files: {sorted(missing)}")
def require(condition, message):
    if not condition:
        raise SystemExit(message)

require("LNGS_LITE" in files["CMakeLists.txt"], "root CMakeLists.txt has no LNGS_LITE option")
require(re.search(r"add_subdirectory\(liblngs\)", files["libs/CMakeLists.txt"]), "libs/CMakeLists.txt does not add the core library")
require(re.search(r"if\s*\(LNGS_LITE\)\s*add_subdirectory\(liblngs_lite\)", files["libs/CMakeLists.txt"]), "LNGS_LITE does not gate the lite target")
require(re.search(r"add_library\(liblngs\s+STATIC\b", files["libs/liblngs/CMakeLists.txt"]), "core library is not declared STATIC")
require("LNGS_LITE" not in files["libs/liblngs/CMakeLists.txt"], "core library CMakeLists references LNGS_LITE")
require(re.search(r"add_library\(lngs_lite\s+SHARED\b", files["libs/liblngs_lite/CMakeLists.txt"]), "lite target is not declared SHARED")
require(re.search(r"target_link_libraries\(lngs_lite\s+PUBLIC\s+liblngs\)", files["libs/liblngs_lite/CMakeLists.txt"]), "lite target does not link to core library")

for path in paths:
    print(f"{path} sha256={sha256(files[path].encode()).hexdigest()}")
print(f"archive sha256={actual}")
print("PASS: LNGS_LITE gates only the added shared target; the core target remains STATIC and has no LNGS_LITE reference.")
