#!/usr/bin/env python3
"""Conan recipe for tpm — tiny password manager (nmeum/tpm).

tpm is a pure POSIX shell script (no C/C++ code) compatible with pass(1).
The build consists of a tiny Makefile that installs the `tpm` script into
$(BINDIR) and an optional man page generated from README.pod via pod2man.

OHOS adaptation notes:
  - No compilation step exists (shell script only), so there is no C/C++
    toolchain involvement, no musl/ABI risk, and R26 (static build for
    system-name libs) does not apply.
  - The Makefile natively supports PREFIX/BINDIR/MANDIR/DESTDIR, so the
    package phase is `make install DESTDIR=<package_folder>` — no source
    patch required (patch count = 0).
  - pod2man (a perl tool) may be absent on the OHOS CI worker. To keep the
    build hermetic and not depend on perl, this recipe installs the `tpm`
    script and the pre-authored README.pod directly, and skips man-page
    generation. The `tpm` command (cmd:tpm) is fully functional without
    the man page; man pages are an optional附属 deliverable.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TpmConan(ConanFile):
    name = "tpm"
    version = "1.3.3"
    description = "tiny password manager — POSIX shell script compatible with pass(1), stores passwords encrypted with gpg2"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/nmeum/tpm"
    url = "https://github.com/nmeum/tpm"

    # Tool (application), not a library: the build output is bin/tpm.
    package_type = "application"

    # Shell-script tool: no compiler/build_type relevance. Keep settings
    # minimal but include os/arch so Conan cross-build machinery is happy.
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply any declared patches (none for this version; kept for spec
        # compliance so future patches just need a conandata entry).
        apply_conandata_patches(self)
        # Nothing to compile: tpm is a #!/bin/sh script. The only Makefile
        # target that does real work is `tpm.1` (man page), which needs
        # pod2man (perl). We deliberately do NOT run `make all` here to avoid
        # a hard build-time dependency on perl/pod2man in the OHOS worker.
        # The script is installed verbatim in package().

    def package(self):
        src = self.source_folder
        dst = self.package_folder

        # Install the tpm executable script into bin/.
        # The Makefile rule is:
        #   install -Dm755 tpm "$(DESTDIR)$(BINDIR)/tpm"
        # We reproduce it with Conan's copy() so the recipe is self-contained
        # and does not invoke the Makefile install target (which would also
        # try to install the man page produced by pod2man).
        copy(self, "tpm", src=src, dst=os.path.join(dst, "bin"), keep_path=False)
        # Preserve executable bit: copy() preserves source file mode, and the
        # upstream tpm script is committed with 0755.

        # Ship the license and the pod source (docs) for completeness.
        copy(self, "LICENSE.txt", src=src,
             dst=os.path.join(dst, "share", "doc", "tpm"), keep_path=False)
        copy(self, "README.pod", src=src,
             dst=os.path.join(dst, "share", "doc", "tpm"), keep_path=False)

        # Optional shell completions from contrib/ (best-effort; do not fail
        # if upstream renames them).
        contrib = os.path.join(src, "contrib")
        if os.path.isdir(contrib):
            copy(self, "*completion*", src=contrib,
                 dst=os.path.join(dst, "share", "tpm", "contrib"),
                 keep_path=False)

    def package_info(self):
        # Application: expose bin/ as the runtime bindir so consumers (and the
        # test_package) find the `tpm` command on PATH via conanrun.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
