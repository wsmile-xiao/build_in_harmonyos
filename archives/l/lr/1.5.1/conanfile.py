#!/usr/bin/env python3
"""Conan recipe for lr 1.5.1 — list files, recursively.

`lr` is a single-file C program that merges the useful parts of ls(1),
find(1), stat(1) and du(1): recursive listing with C-style filter
expressions, sorting, computed directory sizes and shell quoting.

Upstream ships a plain POSIX Makefile with no configure step and no test
target (its only targets are `all`, `clean`, `install` and the `FRC`
placeholder), so the recipe drives `make` directly:

    * make            — builds the `lr` binary from lr.c
    * make install    — installs bin/lr, share/man/man1/lr.1 and the zsh
                        completion _lr under PREFIX (a hard-coded system
                        prefix by default, overridable via make variables)

Adaptation notes (HarmonyOS PC, aarch64):
    * W0: no third-party dependencies — ANSI C + POSIX only, links against
      the system libc (requirements is intentionally absent).
    * Zero upstream patches: the unmodified Makefile builds with the OHOS SDK
      clang (R8: no platform macros anywhere; R33: the compiler path comes
      from the Conan conf `tools.build:compiler_executables`, never a bare
      shell variable).
    * `package()` copies the artifacts instead of running `make install`,
      because the upstream target needs install(1), which is not guaranteed on
      the CI worker PATH, and because it would install into a hard-coded system
      prefix rather than the Conan package folder (R49: no shared system
      prefix is ever touched).
    * Upstream ships no test suite (see test_package/MANIFEST.yml for the
      inventory evidence), so the behavioural regression suite lives in
      test_package/test_lr.sh and really executes the installed binary
      (R34; CI L1e sabotages bin/ to prove the dependency).
Artifacts: bin/lr, share/man/man1/lr.1, share/zsh/site-functions/_lr
(software-level commands.json declares the CLI, R38).
License: MIT.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LrConan(ConanFile):
    name = "lr"
    version = "1.5.1"
    description = "List files recursively, combining the best of ls(1), find(1), stat(1) and du(1)"
    license = "MIT"
    homepage = "https://github.com/leahneukirchen/lr"
    url = "https://github.com/leahneukirchen/lr"
    topics = ("cli", "file-listing", "find", "ls", "posix")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Plain POSIX Makefile project: build in the source folder.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException("lr requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or str(self.settings.compiler)
        # R9: -j1. Upstream CFLAGS (-g -O2 -Wall -Wno-switch -Wextra
        # -Wwrite-strings) are kept as published; only the compiler is
        # substituted (R33), quoted so a path with separators cannot break out.
        self.run("make -j1 CC={0}".format(shlex.quote(cc)))

        # Run the produced ELF once on the build host.  OHOS only rejects an
        # incompatible binary at exec time, so compiling is not proof enough;
        # lr must be able to list its own source directory.  The raw string keeps
        # the backslash-n for lr's own format parser (it honours C escapes);
        # lr-build-smoke.txt is a build-folder temporary and is not packaged.
        self.run(r"./lr -1 -f '%f\n' > lr-build-smoke.txt")
        with open(os.path.join(self.build_folder, "lr-build-smoke.txt")) as handle:
            listing = handle.read()
        if "lr.c" not in listing:
            raise ConanException(
                "lr smoke: built binary did not list its own source (got: {0!r})".format(
                    listing.strip()
                )
            )

        # The smoke test above only proves "runs on this host"; also pin the
        # architecture to what the profile declares, so a future worker that is
        # not aarch64 fails loudly instead of shipping a host-arch binary.
        binary = os.path.join(self.build_folder, "lr")
        with open(binary, "rb") as handle:
            ident = handle.read(20)
        if str(self.settings.arch) == "armv8":
            e_machine = int.from_bytes(ident[18:20], "little")
            if ident[:4] != b"\x7fELF" or e_machine != 0xB7:
                raise ConanException(
                    "lr: built file is not an AArch64 ELF (magic {0!r}, "
                    "e_machine 0x{1:04X})".format(ident[:4], e_machine)
                )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        compdir = os.path.join(self.package_folder, "share", "zsh", "site-functions")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        os.makedirs(compdir, exist_ok=True)
        # Direct copy: the upstream `install` target needs install(1) and would
        # write below a system prefix.
        copy(self, "lr", src=self.build_folder, dst=bindir, keep_path=False)
        copy(self, "lr.1", src=self.build_folder, dst=mandir, keep_path=False)
        copy(self, "_lr", src=self.build_folder, dst=compdir, keep_path=False)
        os.chmod(os.path.join(bindir, "lr"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
