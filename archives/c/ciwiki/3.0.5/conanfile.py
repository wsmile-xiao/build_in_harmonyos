#!/usr/bin/env python3
"""Conan recipe for ciwiki — a personal lightweight wiki written in C.

Builds the upstream autotools project into the `ciwiki` CLI server binary.
Workarounds:
  - E114 (platform/hmdfs): HMDFS `mktemp -d` creates unwritable drwx--S---
    temp dirs which break config.status. Point ac_tmp at a fixed dir in the
    build folder before running configure.
  - E490 + strip_root hardening: `get(keep_permissions=False)` drops the
    executable bit on configure scripts; and on this OHOS conan variant the
    tarball top-level dir may not be stripped. Normalize the source layout
    (move top-level dir contents up, chmod +x autotools scripts) so
    AutotoolsToolchain can always find/run `configure`.
  - 0001-src-ci.c.patch: musl/OHOS `stdin` is FILE *const, cannot reassign.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    chmod,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CiwikiConan(ConanFile):
    name = "ciwiki"
    version = "3.0.5"
    description = "Personal lightweight wiki written in C"
    license = "GPL-2.0-or-later"
    homepage = "https://ciwiki.sourceforge.net/"
    url = "https://downloads.sourceforge.net/project/ciwiki/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ciwiki only uses the C standard library (asprintf/socket/strdup).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="ciwiki-3.0.5.tar.gz")
        # Harden against strip_root not taking effect: if the tarball's single
        # top-level dir is still present and configure is not at the root,
        # move its contents up into source_folder.
        top = os.path.join(self.source_folder, "ciwiki-3.0.5")
        if os.path.isdir(top) and not os.path.exists(
                os.path.join(self.source_folder, "configure")):
            for item in os.listdir(top):
                os.replace(os.path.join(top, item),
                           os.path.join(self.source_folder, item))
            os.rmdir(top)
        # Upstream tarball was shipped after a local `./configure` run, so it
        # contains config.status/config.log/config.h/stamp-h1/Makefile. These
        # stale artifacts make autoconf fail with "source directory already
        # configured". Remove them so configure regenerates everything.
        for root, _dirs, files in os.walk(self.source_folder):
            for f in files:
                if f in ("config.status", "config.log", "config.h",
                         "stamp-h1", "Makefile"):
                    p = os.path.join(root, f)
                    if os.path.isfile(p):
                        os.remove(p)
        # E490: keep_permissions=False drops the executable bit on the
        # autotools helper scripts, restore them so configure can run.
        for script in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "depcomp"):
            p = os.path.join(self.source_folder, script)
            if os.path.exists(p):
                chmod(self, p, 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS: clang 15 toolchain is used, keep upstream defaults otherwise.
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--host=aarch64-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E114 (platform/hmdfs): config.status uses `mktemp -d ./confXXXXXX`
        # which produces drwx--S--- (2700+setgid) dirs on HMDFS, unwritable by
        # the owner. Point ac_tmp at a fixed dir in the build folder instead.
        tmpdir = os.path.join(self.build_folder, ".ciwiki-conf-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        for script in ("configure", "config.status"):
            p = os.path.join(self.source_folder, script)
            if os.path.isfile(p):
                with open(p, encoding="utf-8", errors="replace") as fh:
                    data = fh.read()
                data = data.replace("ac_tmp=$tmp", "ac_tmp=" + tmpdir)
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(data)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI tool: bin/ciwiki; no libraries to link against.
        self.cpp_info.bindirs = ["bin"]
