#!/usr/bin/env python3
"""Conan recipe for xfpt 1.00 – autotools-style configure + make project.

xfpt is a command-line tool by Philip Hazel (University of Cambridge) that
converts marked-up UTF-8 plain text into XML (typically DocBook).

Upstream facts (audited from the xfpt-1.00 tag archive):
- Pure C, 8 source files in src/, no external library dependencies
  (the historical PCRE dependency was dropped before 1.00; grep for
  "pcre" in src/ returns nothing).
- Build system: hand-written autoconf configure (no AC_CANONICAL_HOST,
  so no config.guess/config.sub) + top-level Makefile.in that descends
  into src/Makefile.
- The upstream configure does NOT understand --host; the recipe therefore
  passes CC/CFLAGS explicitly instead of using AutotoolsToolchain --host.
- make install has no DESTDIR support (BINDIR=@prefix@/bin hardcoded),
  so we configure with --prefix=<package_folder> and install directly.
- Upstream tests (testing/runtest) are Perl scripts; they are run in
  build() only when perl is available, otherwise skipped with a note
  (see notes.md for the W5 device-side command).

Output: xfpt binary (command-line tool, not a library) + share data files.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class XfptConan(ConanFile):
    name = "xfpt"
    version = "1.00"
    description = "Plain text to XML (DocBook) processor by Philip Hazel"
    license = "GPL-2.0-only"
    homepage = "https://github.com/PhilipHazel/xfpt"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # xfpt 1.00 is pure C with no external dependencies (libc only).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler from Conan conf, never from raw shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        cflags = "-O2 -fPIC"

        # Build in-source: the top-level Makefile descends into src/.
        prefix = os.path.join(self.build_folder, "prefix")
        # 'sh ./configure' avoids execute-permission issues on HMDFS (E087);
        # this configure has no --host support (no config.guess), so we pass
        # CC/CFLAGS as variable assignments instead of cross args.
        # E011/E060: autoconf's temp-dir machinery (shared by configure and
        # the config.status it generates) uses mktemp -d "./confXXXXXX" — a
        # RELATIVE path, so it lands in the build dir. On HMFS-backed paths
        # (everything under /storage on the CI workers) writing
        # confXXXXXX/subs1.awk fails with "Permission denied / could not
        # setup config files machinery" — config.status dies INSIDE configure.
        # Empirically (builds #64478/#64484/#65170) even a Python-level
        # write probe on /storage PASSES while the shell redirection in
        # config.status still fails, so HMDFS paths must be excluded outright
        # rather than probed. Prefer the worker's native non-HMFS cache
        # (/data/storage/el2/base/cache); if none is usable, leave configure
        # untouched (the unmodified relative-path behaviour works on devices
        # where the conan cache is writable).
        def _non_hmfs_tmpdir():
            import tempfile
            candidates = ["/data/storage/el2/base/cache",
                          os.environ.get("TMPDIR", ""), "/tmp"]
            for cand in candidates:
                if (not cand or cand.startswith("/storage")
                        or not os.path.isdir(cand)):
                    continue
                try:
                    d = tempfile.mkdtemp(prefix="xfpt-probe-", dir=cand)
                    p = os.path.join(d, "probe")
                    with open(p, "w") as f:
                        f.write("x")
                    os.remove(p)
                    os.rmdir(d)
                    return cand
                except OSError:
                    continue
            return None

        configure = os.path.join(self.source_folder, "configure")
        tmpdir = _non_hmfs_tmpdir()
        if os.path.isfile(configure) and tmpdir:
            # Patch BEFORE running configure: both configure itself and the
            # generated config.status then use the absolute non-HMFS path.
            replace_in_file(
                self, configure,
                'mktemp -d "./confXXXXXX"',
                f'mktemp -d "{tmpdir}/confXXXXXX"',
            )

        self.run(
            f'sh ./configure --prefix="{prefix}" CC="{cc}" CFLAGS="{cflags}" LDFLAGS="-fPIC"',
            cwd=self.source_folder,
        )

        self.run("make -j1 build", cwd=self.source_folder)

        # Upstream tests: Perl-based runtest harness over testing/infiles.
        # Only runnable when perl exists; otherwise degrade gracefully
        # (W5 device-side verification recorded in notes.md).
        perl = None
        try:
            import shutil
            perl = shutil.which("perl")
        except Exception:
            perl = None
        if perl:
            self.output.info("perl found: running upstream test suite (testing/runtest)")
            self.run(
                f'cd testing && "{perl}" runtest',
                cwd=self.source_folder,
            )
        else:
            self.output.warning(
                "perl not available: skipping upstream test suite "
                "(testing/runtest is Perl-based); see notes.md for the "
                "device-side verification command"
            )

    def package(self):
        # make install honors the --prefix given to configure
        # (the Makefile has no DESTDIR support)
        prefix = os.path.join(self.build_folder, "prefix")
        self.run("make install", cwd=self.source_folder)

        # bin/ + share/xfpt/ + man land under package_folder via prefix
        copy(self, "xfpt", src=os.path.join(prefix, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(prefix, "share", "xfpt"),
             dst=os.path.join(self.package_folder, "share", "xfpt"))

        # License files
        copy(self, "LICENCE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # R7: Self-sign ELF binary on OHOS for local execution
        if self.settings.os in ("Linux", "OHOS"):
            xfpt_path = os.path.join(self.package_folder, "bin", "xfpt")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(xfpt_path):
                signed_path = f"{xfpt_path}.signed"
                self.run(
                    f'{sign_tool} sign -inFile "{xfpt_path}"'
                    f' -outFile "{signed_path}"'
                    f' -selfSign 1 -signAlg SHA256withECDSA',
                    quiet=True
                )
                if os.path.isfile(signed_path):
                    os.replace(signed_path, xfpt_path)
                    os.chmod(xfpt_path, 0o755)

    def package_info(self):
        # xfpt is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
