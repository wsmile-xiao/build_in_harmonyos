#!/usr/bin/env python3
"""Conan recipe for trf 4.09.1 — Tandem Repeats Finder CLI.

TRF (Benson-Genomics-Lab) detects tandem repeats in DNA sequences.
Single C source (src/trf.c, plus the generated tr30dat.c data table),
classic Autotools build, no external dependencies, no upstream automated
test suite (test_seqs.fasta/.txt are manual sample data).

OHOS adaptation notes:
  - the v4.09.1 tag ships a 2020-era pre-generated configure whose
    config.sub predates the ohos triplet: pass both triplets explicitly
    (aarch64-unknown-linux-gnu) so the config.guess probe never runs;
    AC_CANONICAL_HOST only feeds TARGET_NAME (linux32/64 symlink suffix).
  - the shipped configure carries two `(umask 077 && ...)` temp-dir
    wrappers (E114: HMDFS setgid makes them unwritable) — stripped at
    build() start.
  - the ohos-aarch64 profile [buildenv] pins SHELL/CONFIG_SHELL to the
    hnp bash which getcwd-hangs inside HMDFS build dirs (E386, §12.70①)
    — aggregated env scripts are rewritten in place at build() start.
  - upstream tags are inconsistent: the v4.09.1 tag's configure.ac self-
    reports 4.10.0-rc.2; the recipe/conandata/task version stays 4.09.1
    (the install hook symlink name therefore embeds the upstream string).
"""
import glob
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

_HNP_BASH = "/data/service/hnp/bin/bash"


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir whose files even the owner cannot write
    (config.status dies with `can't create ./confstat*/out: Permission
    denied`).  Strip every `(umask 077 && ...)` wrapper from the shipped
    configure — autoconf generations differ, so match generically and drop
    the now-orphaned parentheses."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = re.sub(r"\(umask 077 && ([^()]+)\)", r"\1", data)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _route_hnp_bash_to_sh(generators_folder):
    """E386 (§12.70①): profile [buildenv] pins SHELL/CONFIG_SHELL to the hnp
    bash, which fails getcwd() inside HMDFS build dirs.  Rewrite the
    aggregated env scripts in place; never re-save_script("conanbuild") — a
    same-named second script is sourced into itself and recurses forever."""
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


class TrfConan(ConanFile):
    name = "trf"
    version = "4.09.1"
    description = ("Tandem Repeats Finder: detects tandem repeats in DNA "
                   "sequences (Benson, TraskLab)")
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/Benson-Genomics-Lab/TRF"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"trf is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 2020-era config.guess/config.sub: keep configure away from the
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

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone binary (bin/trf plus the upstream install-hook symlink
        # trf<version>.linux64.exe pointing at it).
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
