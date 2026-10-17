#!/usr/bin/env python3
"""Conan recipe — clamassassin 1.2.4 (pure shell script, autotools wrapper).

clamassassin is a wrapper for ClamAV's clamscan, designed to be called
from procmail/maildrop for email virus scanning. It is a pure shell
script — the autotools build system only performs variable substitution
(@CLAMSCAN@, @FORMAIL@, etc.) and installs a single file.

configure requires formail/sigtool/clamscan/mktemp in PATH, but those
are RUNTIME dependencies of the generated script, not build-time
libraries. They are not present in the CI toolchain, so the generated
configure (autoconf 2.x style) is patched to turn the hard errors into
warnings with sensible defaults.
"""

import os

from conan import ConanFile
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches, copy, chmod,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ClamassassinConan(ConanFile):
    name = "clamassassin"
    version = "1.2.4"
    description = "Simple email virus filter wrapper for ClamAV clamscan"
    license = "BSD-3-Clause"
    homepage = "https://jameslick.com/clamassassin/"
    url = "https://jameslick.com/clamassassin/"

    package_type = "application"
    # Pure shell script: compiler/build_type are not used by the build,
    # but they must be declared for CI profile compatibility and the L0p
    # quality gate (settings must list os/compiler/build_type/arch).
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-clamdscan",
            "--disable-version-check",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # formail/mktemp/sigtool/clamscan are runtime dependencies of the
        # generated script and are not present in the CI toolchain.
        # Patch the generated configure (autoconf 2.x error blocks) to
        # turn the hard errors into warnings + default command names.
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r") as f:
            content = f.read()

        for var, tool in (
            ("CONF_FORMAIL", "formail"),
            ("CONF_MKTEMP", "mktemp"),
            ("CONF_SIGTOOL", "sigtool"),
            ("CONF_CLAMSCAN", "clamscan"),
        ):
            old = (
                '  { { echo "$as_me:$LINENO: error: Required utility '
                f'{tool} not found." >&5\n'
                f'echo "$as_me: error: Required utility {tool} not found." >&2;}}\n'
                "   { (exit 1); exit 1; }; }"
            )
            new = (
                f'  {{ echo "$as_me:$LINENO: WARNING: {tool} not found '
                '(runtime dependency)." >&5\n'
                f'echo "$as_me: WARNING: {tool} not found (runtime dependency)." >&2;}}\n'
                f"  {var}={tool}"
            )
            if old not in content:
                raise ConanException(f"configure patch pattern for {tool} not found")
            content = content.replace(old, new)

        # clamscan cannot be executed on CI, so the signature-dir
        # detection must not hard-fail either.
        old_sig = (
            '  { { echo "$as_me:$LINENO: error: Cannot determine virus '
            'signature file directory" >&5\n'
            'echo "$as_me: error: Cannot determine virus signature file '
            'directory" >&2;}\n'
            "   { (exit 1); exit 1; }; }"
        )
        new_sig = (
            '  { echo "$as_me:$LINENO: WARNING: cannot determine virus '
            'signature dir, defaulting." >&5\n'
            'echo "$as_me: WARNING: cannot determine virus signature dir, '
            'defaulting." >&2;}\n'
            "  CONF_SIGLOC=/usr/share/clamav"
        )
        if old_sig not in content:
            raise ConanException("configure SIGLOC patch pattern not found")
        content = content.replace(old_sig, new_sig)

        with open(configure, "w") as f:
            f.write(content)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-clamdscan",
            "--disable-version-check",
        ])
        args = " ".join(tc.configure_args)
        src = self.source_folder

        # Step 1: configure --no-create (generates config.status only)
        self.run(
            f"bash ./configure --no-create {args}",
            cwd=src,
        )

        # Step 2: E011 fix — patch config.status umask 077 -> 022 (HMDFS)
        config_status = os.path.join(src, "config.status")
        if os.path.isfile(config_status):
            with open(config_status, "r") as f:
                cs = f.read()
            if "umask 077" in cs:
                cs = cs.replace("umask 077", "umask 022")
                with open(config_status, "w") as f:
                    f.write(cs)
                self.output.info("E011: Patched config.status umask 077 -> 022")

        # Step 3: generate Makefile + clamassassin
        self.run("bash ./config.status", cwd=src)

        # -j1: jobserver mkfifo fails on HMDFS (Operation not permitted).
        self.run("make -j1", cwd=src)

    def package(self):
        # The upstream Makefile install target uses an absolute bindir
        # without DESTDIR (cp -f clamassassin /bin), which would write
        # into the system root. Copy the config.status-generated script
        # into the package folder instead of running make install.
        copy(self, "clamassassin", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        chmod(self, os.path.join(self.package_folder, "bin", "clamassassin"), 0o555)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
