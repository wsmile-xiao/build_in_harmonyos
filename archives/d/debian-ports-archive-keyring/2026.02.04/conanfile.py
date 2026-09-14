#!/usr/bin/env python3
"""Conan recipe — debian-ports-archive-keyring 2026.02.04 (Debian data/keyring package).

The debian-ports archive signs its Release files with the OpenPGP keys shipped
in this package. Pure data-only keyring package: nothing compiles, and build
needs no gpg, no network (only python3 stdlib).

The Debian-native source ships ASCII-armored keys under active-keys/ (2 keys)
and removed-keys/ (19 historical keys, 2007-2025). debian/rules rebuilds the
binary keyrings shipped as /usr/share/keyrings/*.pgp with `gpg --import`.
We reproduce that step deterministically in pure Python (armor-decode then
year-sorted concatenation of the full public-key packets) and assert the
result is byte-identical to the official binary .deb (sha256 hard-gated), so
content drift from upstream fails the build instead of shipping silently.

Installed layout mirrors the Debian package, relocated for Conan:
  share/keyrings/debian-ports-archive-2026.asc              (== official trusted.gpg.d)
  share/keyrings/debian-ports-archive-2027.asc
  share/keyrings/debian-ports-archive-keyring.pgp           (active, binary)
  share/keyrings/debian-ports-archive-keyring-removed.pgp   (historical, binary)
"""
import base64
import hashlib
import os
import re

from conan import ConanFile
from conan.tools.files import copy, get


# sha256 of the four payload files inside the official Debian binary package
# debian-ports-archive-keyring_2026.02.04_all.deb (verified 2026-09-09).
OFFICIAL_SHA = {
    "debian-ports-archive-2026.asc":
        "e7c5cd21987bac198e1536d12a2d7cfadbf0979e063d07838165df25dc4de7d0",
    "debian-ports-archive-2027.asc":
        "d91ed90ad85d43447da9af784e3fbd0fd4c447aa3596d0667a1ad6354ba13a82",
    "debian-ports-archive-keyring.pgp":
        "7d5da83561d53da68cc44141fc34fba1c174ce073f379576091a8d9ea21bf793",
    "debian-ports-archive-keyring-removed.pgp":
        "383db113d9f362efc25bfdd11b630c7b39695f329f3be11dd874c264fc4206be",
}


def _year_of(path):
    return int(re.search(r"(\d{4})", os.path.basename(path)).group(1))


def _armor_body_bytes(path):
    """Extract the binary payload of one ASCII-armored OpenPGP block."""
    text = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"-----BEGIN [^-]+-----\n(.*?)-----END [^-]+-----", text, re.S)
    if not m:
        raise ValueError(f"not an OpenPGP armor block: {path}")
    lines = m.group(1).split("\n")
    i = 0
    # Skip armor header lines (Version:/Comment:/... up to the blank line).
    while i < len(lines) and lines[i].strip() != "":
        i += 1
    body = []
    for line in lines[i:]:
        line = line.strip()
        if not line or line.startswith("="):
            continue
        body.append(line)
    return base64.b64decode("".join(body), validate=True)


def _concat_keyring(paths):
    return b"".join(_armor_body_bytes(p) for p in sorted(paths, key=_year_of))


class DebianPortsArchiveKeyringConan(ConanFile):
    name = "debian-ports-archive-keyring"
    version = "2026.02.04"
    package_type = "unknown"

    # 纯数据/资源包：无平台/编译器依赖；显式声明 settings 以通过 CI L0 门禁
    settings = "os", "compiler", "build_type", "arch"
    options = None
    default_options = None

    def requirements(self):
        pass  # 无 Conan 第三方依赖

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 python 复现 debian/rules 的 `gpg --no-keyring --import ...`：
        #   active-keys/*.key  -> debian-ports-archive-keyring.pgp
        #   removed-keys/*.key -> debian-ports-archive-keyring-removed.pgp
        # .asc 与官方 /etc/apt/trusted.gpg.d/*.asc 逐字节相同（= 源 .key 原文）。
        src = self.source_folder
        active = [os.path.join(src, "active-keys", f)
                  for f in os.listdir(os.path.join(src, "active-keys"))]
        removed = [os.path.join(src, "removed-keys", f)
                   for f in os.listdir(os.path.join(src, "removed-keys"))]
        active_pgp = _concat_keyring(active)
        removed_pgp = _concat_keyring(removed)

        artifacts = {
            "debian-ports-archive-keyring.pgp": active_pgp,
            "debian-ports-archive-keyring-removed.pgp": removed_pgp,
        }
        for f in active:
            artifacts[os.path.basename(f).replace(".key", ".asc")] = open(f, "rb").read()

        out = os.path.join(self.build_folder, "keyrings")
        os.makedirs(out, exist_ok=True)
        for name, data in artifacts.items():
            if hashlib.sha256(data).hexdigest() != OFFICIAL_SHA[name]:
                raise RuntimeError(
                    f"keyring artifact {name} does not match official "
                    f"debian-ports-archive-keyring_2026.02.04_all.deb "
                    f"(sha256 {hashlib.sha256(data).hexdigest()} != {OFFICIAL_SHA[name]}); "
                    "upstream content drifted — do not ship")
            with open(os.path.join(out, name), "wb") as fh:
                fh.write(data)

    def package(self):
        src = os.path.join(self.build_folder, "keyrings")
        copy(self, "*", src=src, dst=os.path.join(self.package_folder, "share", "keyrings"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
