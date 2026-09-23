#!/usr/bin/env python3
"""Conan recipe for dehydrated-hook-ddns-tsig 0.1.4 — pure Python dehydrated
DNS-01 challenge hook (RFC2136 dynamic TXT updates with TSIG via dnspython).

Upstream ships a single Python script + sample conf (no build system).
Installed layout:
  bin/dehydrated-hook-ddns-tsig          patched entry script (0755)
  lib/python3.12/site-packages/dns/      vendored dnspython (pure Python)
  share/doc/dehydrated-hook-ddns-tsig/   sample configuration

Dependency closure: the OHOS device Python (3.12.9) has no dnspython module
and no dnspython recipe exists in the OHOS archives, so the pure-Python
dnspython sdist is vendored into this package at source() time (URL and
SHA256 pinned below). The script reaches it via a relative sys.path
bootstrap (patch 0001), so no absolute paths are baked in.
The optional upstream dependency `iscpy` is deliberately NOT packaged: it
is py2-only and only needed for DDNS_HOOK_KEY_FILE parsing; configure
key_name/key_secret directly in the conf file instead (see notes.md).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)

# Vendored runtime dependency (pure Python, MIT, no further deps).
# Source of truth: https://pypi.org/pypi/dnspython/2.8.0/json (sdist digest).
DNSPYTHON_VERSION = "2.8.0"
DNSPYTHON_URL = (
    "https://files.pythonhosted.org/packages/8c/8b/"
    "57666417c0f90f08bcafa776861060426765fdb422eb10212086fb811d26/"
    "dnspython-2.8.0.tar.gz"
)
DNSPYTHON_SHA256 = (
    "181d3c6996452cb1189c4046c61599b84a5a86e099562ffde77d26984ff26d0f"
)


class DehydratedHookDdnsTsigConan(ConanFile):
    name = "dehydrated-hook-ddns-tsig"
    version = "0.1.4"
    package_type = "application"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/eferdman/dehydrated-hook-ddns-tsig"
    description = (
        "dehydrated DNS-01 challenge hook: RFC2136 dynamic TXT-record "
        "updates with TSIG signing via dnspython (pure Python)"
    )
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Vendor dnspython (pure Python) — rationale in module docstring.
        get(
            self,
            DNSPYTHON_URL,
            sha256=DNSPYTHON_SHA256,
            strip_root=True,
            destination=os.path.join("vendor", "dnspython"),
        )

    def build(self):
        script = os.path.join(
            self.source_folder, "dehydrated-hook-ddns-tsig.py")
        if not os.path.isfile(script):
            raise ConanException(f"hook script missing: {script}")
        dns_init = os.path.join(
            self.source_folder, "vendor", "dnspython", "dns", "__init__.py")
        if not os.path.isfile(dns_init):
            raise ConanException(f"vendored dnspython missing: {dns_init}")
        # Pure Python: syntax-check the patched script + vendored package.
        # Keep __pycache__ out of the source tree (would otherwise be copied).
        pycache = os.path.join(self.build_folder, "pycache")
        self.run(
            f'PYTHONPYCACHEPREFIX="{pycache}" '
            f'python3 -m py_compile "{script}" "{dns_init}"'
        )

    def package(self):
        # Entry script (shebang/python3 + sys.path bootstrap via patch 0001).
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        script_dst = os.path.join(bindir, "dehydrated-hook-ddns-tsig")
        shutil.copy(
            os.path.join(self.source_folder, "dehydrated-hook-ddns-tsig.py"),
            script_dst,
        )
        os.chmod(script_dst, 0o755)

        # Vendored dnspython -> site-packages; layout matches the relative
        # sys.path bootstrap: <pkg>/bin/../lib/python3.12/site-packages.
        src_dns = os.path.join(
            self.source_folder, "vendor", "dnspython", "dns")
        dst_dns = os.path.join(
            self.package_folder, "lib", "python3.12", "site-packages", "dns")
        shutil.copytree(
            src_dns, dst_dns,
            ignore=shutil.ignore_patterns("__pycache__"))

        # Sample configuration (documentation copy; runtime conf is supplied
        # via -c FILE or the default search paths).
        docdir = os.path.join(
            self.package_folder, "share", "doc", "dehydrated-hook-ddns-tsig")
        os.makedirs(docdir, exist_ok=True)
        shutil.copy(
            os.path.join(
                self.source_folder, "dehydrated-hook-ddns-tsig.conf"),
            os.path.join(docdir, "dehydrated-hook-ddns-tsig.conf"),
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Consumers of this package get the vendored dnspython on PYTHONPATH;
        # the entry script also self-bootstraps it (patch 0001).
        self.runenv_info.append_path(
            "PYTHONPATH",
            os.path.join(
                self.package_folder, "lib", "python3.12", "site-packages"),
        )
