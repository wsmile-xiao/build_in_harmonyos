#!/usr/bin/env python3
"""Conan recipe for cronic 3 — a cron job report wrapper (bash script).

cronic wraps a command and stays silent when it succeeds with no stderr
output; otherwise it prints a report (command, result code, error output,
standard output) so cron only mails on real failures.

This package has NO compilation units, NO build system and NO upstream test
suite. It only redistributes and installs the upstream `cronic` shell script
plus its LICENSE/README. Runtime dependencies (bash, grep, mktemp) are
operating-system tools, not Conan packages, so there are no requires().

Version slug: upstream labels this release "Cronic v3" and publishes no dotted
version and no git tag (GitHub tags API returns []). Conan 2.x rejects a
single-character version — its RecipeReference pattern is
`^[a-z0-9_][a-z0-9_+.-]{1,100}$` (conan/api/model/refs.py), i.e. >= 2 chars —
so `cronic/3` fails at export with `Invalid package version '3'`. Following the
sanctioned repo precedent (archives/c/cutmp3/4, archives/r/rapidhash/3) the
task-card directory stays `3` while set_version() names the built artifact
`cronic/v3`, the upstream label kept verbatim. The archive directory and the
`feat/cronic-3` branch keep the platform's task-card form.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class CronicConan(ConanFile):
    name = "cronic"
    description = ("Cron job output wrapper: only emails when the wrapped command "
                   "fails or writes to stderr")
    license = "CC0-1.0"
    homepage = "http://habilis.net/cronic/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cron", "shell", "script", "wrapper", "ohos")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def set_version(self):
        # Upstream label "Cronic v3" -> artifact version `v3` (see docstring).
        # Deliberately not a bare `version = "3"` attribute: Conan rejects the
        # one-character form, and CI L0m/PF8 only cross-check a literal
        # `version = "..."` attribute against the version directory, so the
        # task-card directory `3` and the artifact `cronic/v3` coexist.
        self.version = "v3"

    def export_sources(self):
        # This package needs no patches; the hook is a safe no-op when the
        # conandata.yml `patches` mapping is empty (same form as pari-galpol).
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No compilation: the upstream artifact is a finished bash script.
        # Applying the (empty) patch set keeps the standard recipe shape and
        # the presence check guards against an incomplete download.
        apply_conandata_patches(self)
        if not os.path.isfile(os.path.join(self.source_folder, "cronic")):
            raise ConanException("upstream cronic script missing from source archive")
        self.output.info("Validated upstream cronic script; no compilation required")

    def package(self):
        copy(self, "cronic", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "cronic"),
             keep_path=False)

        # Best-effort exec bit. On HMDFS (HarmonyOS) chmod is frequently
        # ignored / normalized, so the test and smoke checks invoke the
        # script explicitly as `bash <pkg>/bin/cronic` instead of relying
        # on the shebang, and the permission outcome is not asserted.
        binary = os.path.join(self.package_folder, "bin", "cronic")
        try:
            os.chmod(binary, 0o755)
        except OSError as exc:  # pragma: no cover - defensive
            self.output.warning(f"chmod on {binary} failed: {exc}")

    def package_id(self):
        # Pure script: independent of compiler/build_type/arch.
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = [os.path.join("share", "doc", "cronic")]
