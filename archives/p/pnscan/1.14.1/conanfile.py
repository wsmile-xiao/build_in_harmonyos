#!/usr/bin/env python3
"""Conan recipe for pnscan 1.14.1 — parallel network scanner (application).

Autotools project with a pre-generated configure (autoconf 2.69, no
config.guess/config.sub in build-aux and no AC_CANONICAL_HOST, so the
OHOS toolchain reaches the build purely through the environment CC set
by AutotoolsToolchain; the --host/--build arguments passed by Conan are
harmlessly warned about as unrecognized).  Upstream ships a real
"make check" with five scan scenarios against its own t_listen test
daemon on 127.0.0.1 — executed inside build() as the upstream test run.
"""
import os
import re

import glob as _glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class PnscanConan(ConanFile):
    name = "pnscan"
    version = "1.14.1"
    description = ("Parallel network scanner: probes TCP services, banners and "
                   "responses across IP/port ranges")
    license = "BSD-3-Clause"
    homepage = "https://github.com/ptrrkssn/pnscan"
    url = "https://github.com/ptrrkssn/pnscan"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def configure(self):
        self.options.rm_safe("shared")
        self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)
        # In-tree build: configure/make/check run directly in the source
        # folder, so the build scripts never depend on conan's source-copy
        # timing and the upstream relative-path invocations keep working.
        self.folders.build = self.folders.source

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Legacy autoconf triplet; config.sub absent so the value is
            # cosmetic, but keep the known-good pattern from a52dec.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E386: the aggregated build env (written lazily by conan right
        # before the first self.run) carries the login shell (hnp bash) as
        # SHELL/CONFIG_SHELL, and autoconf re-executing through it fails
        # getcwd() under HMDFS build dirs.  Patching those files is a race
        # against conan's own aggregation, so instead source the toolchain
        # env scripts explicitly and route every shell-relevant command
        # through `env -u CONFIG_SHELL SHELL=/bin/sh`.
        bf = self.build_folder
        env_files = sorted(_glob.glob(
            os.path.join(self.generators_folder, "conanbuildenv-*.sh")))
        if not env_files:
            raise ConanException(
                "AutotoolsToolchain env scripts not found in generators folder")
        src = " && ".join(f'. "{p}"' for p in env_files)
        pre = "env -u CONFIG_SHELL SHELL=/bin/sh"
        triplet = ("--host=aarch64-unknown-linux-gnu "
                   "--build=aarch64-unknown-linux-gnu"
                   if str(self.settings.os) == "OHOS" else "")
        # E011/E114: autoconf 2.69 creates its config.status scratch dir as
        # `(umask 077 && mktemp -d ...)` / `(umask 077 && mkdir "$tmp")`; the
        # resulting 0700 dir breaks on HMDFS ("can't create .../subs1.awk:
        # Permission denied" inside the generated config.status).  Relax just
        # the umask value (creation logic untouched) before running it.
        self.run(
            f"{pre} sed -i 's/umask 077/umask 022/g' ./configure", cwd=bf)
        self.run(
            f'{src} && {pre} ./configure --prefix=/ {triplet} && '
            f'{pre} make -j1 && {pre} make -j1 check',
            cwd=bf)

    def package(self):
        # Manual packaging: upstream has no usable DESTDIR story beyond
        # install-bin (pnscan only), and going through make here would
        # re-enter the aggregated build env.  Copy the two binaries plus
        # the license; t_listen is the companion daemon used by
        # "make check" and by the consumer test.
        copy(self, "pnscan", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "t_listen", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
