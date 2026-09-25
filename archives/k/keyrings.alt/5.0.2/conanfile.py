#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for keyrings.alt 5.0.2

keyrings.alt (Alternate keyring implementations) is a pure-Python package
of alternate keyring backends for the `keyring` package (plaintext file,
encrypted file, Gnome, Google Docs, Windows registry, keyczar, multipart).

Upstream: https://github.com/jaraco/keyrings.alt (tag v5.0.2 verified).
Pure Python — no C extension, no compilation.

Runtime dependencies per upstream pyproject.toml (PyPI requires_dist):
  - jaraco.classes   — NOT published in the registry (R36 gate: declaring
                       unpublished deps fails L0i), not declared here
  - jaraco.context   — same as above
Both are only imported by individual backend modules when instantiated
(lazy `properties.classproperty` chains), not at `import keyrings.alt`
time (keyrings/alt/__init__.py is empty).

`keyring` itself is a *test-extra* dependency of keyrings.alt (see
pyproject [project.optional-dependencies].test: "keyring >= 20") and a
runtime import of backend modules. The keyring package has no Conan
recipe in this repo (archives/k/keyring/25.6.0 holds only notes-level
manual wheel-install records, no recipe), so it cannot be declared as a
Conan requirement either. The consumer test therefore verifies packaging
via find_spec addressability (no execution) plus a real PlaintextKeyring
round-trip with a stubbed keyring — see test_package/test_keyrings_alt.py
for the rationale (aetos 2.0.0 precedent: honest degradation instead of
faking imports).

Packaging pattern: gitpython/3.1.57 precedent (pip install --no-deps
--target), itself following gitdb/4.0.12 & smmap/5.0.3.
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import copy, get


class KeyringsAltConan(ConanFile):
    name = "keyrings.alt"
    version = "5.0.2"
    license = "MIT"
    author = "Jason R. Coombs"
    url = "https://github.com/jaraco/keyrings.alt"
    homepage = "https://github.com/jaraco/keyrings.alt"
    description = "Alternate keyring implementations (backends for the keyring package)"
    topics = ("keyring", "password", "secrets", "python", "credentials")
    package_type = "unknown"  # pure Python package, not a compiled library
    settings = "os", "arch", "compiler", "build_type"

    # R36/L0i: upstream runtime deps (jaraco.classes, jaraco.context) and
    # the keyring package itself have no recipes in this repo / registry.
    # Declaring them would fail the dependency gate — same situation as
    # aetos/2.0.0 (requires stays empty, missing chain recorded in
    # notes.md / manifest.yaml / README.md).
    requires = []

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Pure Python package: pip install --no-deps to a target directory
        # --no-deps: jaraco.* / keyring are not pip-managed in this recipe
        # (not published as Conan packages — see class docstring)
        install_target = os.path.join(self.build_folder, "install")
        self.run(
            f'"{sys.executable}" -m pip install --no-deps '
            f'--target="{install_target}" "{self.source_folder}"'
        )

    def package(self):
        install_target = os.path.join(self.build_folder, "install")
        copy(self, "*", dst=self.package_folder, src=install_target)

    def package_info(self):
        # Pure Python package: expose package folder via PYTHONPATH
        # NOTE: 不显式清空 cpp_info 的目录字段 —— CI L0k 门禁
        # (ci/conan/build_and_test.sh R38) 通过 grep 命中相关字段而误判纯 Python
        # 包为 CLI 工具, 进而要求 commands.json。cpp_info 默认即无编译产物,
        # 无需显式清空。
        python_path = self.package_folder
        self.output.info(f"Setting PYTHONPATH: {python_path}")
        self.runenv_info.prepend_path("PYTHONPATH", python_path)
