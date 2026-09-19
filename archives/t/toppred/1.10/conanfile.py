#!/usr/bin/env python3
"""Conan recipe for toppred 1.10 — transmembrane helix topology prediction CLI.

toppred (Bioinformatics dept., Institut Pasteur) predicts transmembrane
helices and their topology from protein sequences using the von Heijne
window/scale method.  Single C binary (src/), classic Autotools build,
runtime data files (hydrophobicity scales) installed to <prefix>/share/toppred.

Upstream vintage notes:
  - the GitHub tag archive ships a pre-generated 2014-era configure whose
    config.guess/config.sub predate the aarch64/ohos triplets.  configure is
    given both triplets explicitly (aarch64-unknown-linux-gnu) so the
    config.guess probe never runs and config.sub only parses gnu triplets;
    AC_CANONICAL_HOST result is only consulted for an OSF/1 special case
    (a52dec/0.7.4 same-vintage precedent).
  - libgd (PNG topologies) and gnuplot (interactive plots) are optional:
    configure degrades to a warning and the tests all pass `-g none -t none`.
  - the shipped configure carries the autoconf `umask 077` temp-dir pattern
    (E114: HMDFS turns the 0700 dir into an unwritable drwx--S--- dir) —
    dropped at build() start.
  - the ohos-aarch64 profile [buildenv] pins SHELL/CONFIG_SHELL to the hnp
    bash, which getcwd-hangs inside HMDFS build dirs (E386, §12.70①) — the
    aggregated env scripts are rewritten in place at build() start.
"""
import glob
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, get, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

_HNP_BASH = "/data/service/hnp/bin/bash"


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir whose files even the owner cannot write
    (config.status dies with `can't create ./confstat*/out: Permission
    denied`).  Strip every `(umask 077 && ...)` wrapper from the shipped
    configure — autoconf generations differ (`mktemp -d "./confXXXXXX"` vs
    `mktemp -d -q "./confstatXXXXXX"` vs `mkdir $tmp`), so match generically
    and drop the now-orphaned parentheses."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = re.sub(r"\(umask 077 && ([^()]+)\)", r"\1", data)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _route_hnp_bash_to_sh(generators_folder):
    """E386 (§12.70①): profile [buildenv] pins SHELL/CONFIG_SHELL to the hnp
    bash, which fails getcwd() inside HMDFS build dirs (autoconf re-exec and
    automake test drivers inherit it).  Rewrite the aggregated env scripts in
    place; never re-save_script("conanbuild") — a same-named second script is
    sourced into itself and recurses forever."""
    if not generators_folder or not os.path.isdir(generators_folder):
        return
    for sh in glob.glob(os.path.join(generators_folder, "**", "*.sh"),
                        recursive=True):
        with open(sh, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        if _HNP_BASH in data:
            with open(sh, "w", encoding="utf-8") as f:
                f.write(data.replace(_HNP_BASH, "/bin/sh"))
    for var in ("SHELL", "CONFIG_SHELL"):
        if os.environ.get(var, "").startswith(_HNP_BASH):
            os.environ[var] = "/bin/sh"


class ToppredConan(ConanFile):
    name = "toppred"
    version = "1.10"
    description = ("toppred: prediction of protein transmembrane helices and "
                   "topology (von Heijne method, Institut Pasteur)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/bioinfo-center-pasteur-fr/toppred"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libm (pow/sqrt) only; libgd/gnuplot intentionally not provided —
        # configure degrades to "graphic topologies unavailable" (upstream
        # default) and every upstream test passes `-g none -t none`.
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"toppred is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 2014-era config.guess/config.sub: keep configure away from the
        # guess probe and from parsing the ohos triplet (see module docstring).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        _route_hnp_bash_to_sh(self.generators_folder)
        autotools = Autotools(self)
        autotools.configure()
        # R9/E074: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # Upstream test suite (test/Makefile.am TESTS: 7 shell scripts) is part
        # of the build contract (R51: 0 执行 = 不可交付).
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone binary; hydrophobicity scales land in share/toppred and
        # are resolved at runtime via the compiled-in pkgdatadir (or the
        # TOPPREDDATA override, as upstream tests do).
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
