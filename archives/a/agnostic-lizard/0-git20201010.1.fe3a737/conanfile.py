#!/usr/bin/env python3
"""Conan recipe for agnostic-lizard 0~git20201010.1.fe3a737 — a best-effort
portable code walker for Common Lisp (macroexpand-all and friends).

This is a **source-only package**: the upstream tree is 27 plain-text files
(two ASDF system definitions, Lisp sources, docs and license texts)
with no native artifact to build —
matching the Debian binary package ``cl-agnostic-lizard`` which installs the
very same files under ``/usr/share/common-lisp/source/agnostic-lizard``.
Following the merged data-package pattern of ``pari-seadata-big``, the recipe
is architecture-independent (``package_id()`` clears the whole settings
tuple). ``build()`` checks source integrity; test_package separately runs the
official core regressions and real installed-library consumers using ECL.

Consumers point any ASDF-capable Common Lisp implementation at the packaged
tree via ``ASDF_SOURCE_REGISTRY``/``CL_SOURCE_REGISTRY`` — the directory
exposed through ``AGNOSTIC_LIZARD_SRC_DIR`` — and load system
``agnostic-lizard``. The optional debugger prototype requires additional
Bordeaux Threads and is not a supported/tested core-runtime claim.
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class AgnosticLizardConan(ConanFile):
    name = "agnostic-lizard"
    version = "0-git20201010.1.fe3a737"
    description = (
        "agnostic-lizard 0~git20201010.1.fe3a737 — best-effort portable code "
        "walker for Common Lisp (macroexpand-all); source-only, no build"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.common-lisp.net/mraskin/agnostic-lizard"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"

    # Source-only: no compiler touches any artifact.  The full settings tuple
    # is declared because the L0 profile step requires all four, but
    # package_id() clears it below — every platform shares one noarch package.
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # The validator travels with the recipe so both build() and
        # test_package can run it.
        copy(
            self,
            "verify_agnostic_lizard.py",
            src=os.path.join(self.recipe_folder, "test_package"),
            dst=os.path.join(self.export_sources_folder, "test_package"),
        )

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")
        self.settings.rm_safe("compiler.cppstd")

    def source(self):
        # The "size" entry in conandata is metadata only — get() rejects it
        # as a kwarg, so pop it first (cf. pari-seadata-big).
        source = dict(self.conan_data["sources"][self.version])
        source.pop("size", None)
        get(self, **source, strip_root=False)

    @property
    def _validator(self):
        return os.path.join(
            self.export_sources_folder,
            "test_package",
            "verify_agnostic_lizard.py",
        )

    def build(self):
        # Deterministic source-tree validation in place of a compile smoke
        # test: integrity does not replace the functional Lisp regressions
        # and consumers in test_package.
        self.run(
            f'"{sys.executable}" "{self._validator}" '
            f'--source-root "{self.source_folder}"'
        )
        apply_conandata_patches(self)

    def package(self):
        # Mirror the Debian cl-agnostic-lizard layout:
        # /usr/share/common-lisp/source/agnostic-lizard
        src_root = self.source_folder
        if os.path.isfile(os.path.join(src_root, "agnostic-lizard.asd")):
            base = src_root
        else:
            base = os.path.join(
                src_root, "agnostic-lizard-0~git20201010.1.fe3a737"
            )
        lisp_dir = os.path.join(
            self.package_folder, "share", "common-lisp", "source",
            "agnostic-lizard",
        )
        copy(self, "*", src=base, dst=lisp_dir, keep_path=True,
             excludes=["Plugin*", ".git*"])
        # License texts also land in the standard licenses folder.
        copy(self, "COPYING", src=base,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "gpl-3.0.txt", src=base,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = [os.path.join("share", "common-lisp", "source")]

        src_dir = os.path.join(
            self.package_folder, "share", "common-lisp", "source",
            "agnostic-lizard",
        )
        # ASDF finds the system through the CL source registry; the plain
        # path variable is kept for consumers that wire it themselves.
        escaped = src_dir.replace('\\', '\\\\').replace('"', '\\"')
        registry_entry = f'(:source-registry (:tree "{escaped}/") :inherit-configuration)'
        self.buildenv_info.define_path("AGNOSTIC_LIZARD_SRC_DIR", src_dir)
        self.runenv_info.define_path("AGNOSTIC_LIZARD_SRC_DIR", src_dir)
        self.runenv_info.define(
            "CL_SOURCE_REGISTRY", registry_entry
        )
        self.conf_info.define(
            "user.agnostic-lizard:source_dir", src_dir
        )
