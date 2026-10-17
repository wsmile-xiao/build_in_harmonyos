#!/usr/bin/env python3
"""Conan recipe for rungetty 1.2.

rungetty is a small console getty: it takes over a tty line and runs an
arbitrary program on it (upstream homepage
http://ibiblio.org/pub/Linux/system/serial/getty/).

Upstream ships a single C file plus a bare Makefile, so the recipe drives that
Makefile directly (R33: the compiler comes from the Conan conf, never from a
shell variable) and installs the artifacts itself: the upstream ``install``
target cannot be used on this platform because it hardcodes
``install -o root -g root`` (needs root, and the ``install(1)`` tool is not
present in the OpenHarmony device image at all) and installs the manual page
into the non-FHS path ``$(ROOT)/usr/man/man8``.
"""
import os
import shutil
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.layout import basic_layout


class RungettyConan(ConanFile):
    name = "rungetty"
    version = "1.2"
    description = (
        "A small console getty that takes over a tty line and runs an "
        "arbitrary program on it."
    )
    license = "GPL-2.0-or-later"
    homepage = "http://ibiblio.org/pub/Linux/system/serial/getty/"
    url = ""  # CI fills this

    # R38: command line tool, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # rungetty links against libc only: POSIX termios/ioctls, no external
        # dependency to declare (verified by ci/scripts/preflight_check.sh).
        pass

    def validate(self):
        # R32: never compare settings.os with "Linux" only.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rungetty needs Linux console TTY semantics (TIOCSCTTY, "
                f"vhangup), got os={self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        data = self.conan_data["sources"][0]
        try:
            get(self, **data, strip_root=True)
        except ConanException as error:
            # ibiblio.org answers `Content-Encoding: x-gzip` for .tar.gz (Apache
            # `AddEncoding x-gzip .gz`), so the Conan downloader (requests /
            # urllib3) transparently decompresses the body: the bytes on disk
            # are the uncompressed tar and the sha256 of the official archive
            # can never match.  urllib does not decode Content-Encoding, so the
            # archive lands byte-exactly and the checksum is the real check.
            # Mechanism: knowledge/drafts/DRAFT-conan-downloader-xgzip-content-encoding
            self.output.warning(
                f"conan download rejected the archive ({error}); "
                "retrying with urllib (server responds Content-Encoding: x-gzip)"
            )
            self._source_with_urllib(data["url"], data["sha256"])

    def _source_with_urllib(self, url, sha256):
        archive = os.path.join(self.source_folder, os.path.basename(url))
        os.makedirs(self.source_folder, exist_ok=True)
        with urllib.request.urlopen(url, timeout=120) as response, \
                open(archive, "wb") as handle:
            shutil.copyfileobj(response, handle)
        check_sha256(self, archive, sha256)
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.remove(archive)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from the Conan conf, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c", "clang") if executables else "clang"

        # The upstream default target `all` builds `rungetty` and then prints
        # `size rungetty`; building the `rungetty` target keeps the recipe from
        # depending on binutils being present.  Upstream CFLAGS are kept as they
        # are (`CFLAGS` is only overridable as a whole, so it is not touched).
        self.run(f'make CC="{cc}" -j1 rungetty', cwd=self.source_folder, env=None)

        # R51: upstream ships no test suite at all — the archive contains
        # CHANGELOG COPYING Makefile README THANKS mingetty.comment rungetty.8
        # rungetty.c, the Makefile has no `check` target and `make -n check`
        # fails with "No rule to make target 'check'" (evidence recorded in
        # notes.md / reports/test-report.md).  The behavioural coverage is
        # therefore asserted in test_package/ (R34), which is also what CI L1e
        # verifies destructively.

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "rungetty", self.source_folder, bindir)
        os.chmod(os.path.join(bindir, "rungetty"), 0o755)
        # FHS manual page location instead of upstream's $(ROOT)/usr/man/man8.
        copy(
            self,
            "rungetty.8",
            self.source_folder,
            os.path.join(self.package_folder, "share", "man", "man8"),
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Application package: no libraries to link, only the executable.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
