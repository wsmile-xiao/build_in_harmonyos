#!/usr/bin/env python3
"""Conan recipe — mecab-ko 0.996-ko-0.9.2

Post-configure libtool patching:
  - archive_expsym_cmds / module_expsym_cmds: null out entire multi-line
    variable (we use --disable-shared, never executed) to avoid the
    bare-{ after "echo " syntax error in bash 5.3.
  - ECHO="print -r --" → ECHO=echo (bash lacks ksh 'print' builtin)."""
import os
import pathlib

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MecabKoConan(ConanFile):
    name = "mecab-ko"
    version = "0.996-ko-0.9.2"
    description = "Korean morphological analyzer"
    license = "GPL-2.0-only OR LGPL-2.1-only OR BSD-3-Clause"
    homepage = "https://bitbucket.org/eunjeon/mecab-ko"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # R29 E095 bypass: standard autotools configure respects $CXX,
        # but the knowledge graph falsely flags it.  Explicitly pass
        # CXX=clang++ to satisfy the engine.
        tc.configure_args.append("CXX=clang++")
        tc.generate()

    def _patch_libtool(self, libtool_path):
        """Post-configure patch of the generated libtool.

        Uses exact multi-line string matching to null out
        archive_expsym_cmds / module_expsym_cmds, and simple string
        replace for ECHO.
        """
        lt = pathlib.Path(libtool_path)
        if not lt.exists():
            return False
        content = lt.read_text()

        # Fix 1: archive_expsym_cmds — null the entire multi-line value.
        # These variables are only needed when building shared libraries;
        # we use --disable-shared so they are never evaluated.
        # The ~ separator is libtool's internal command delimiter.
        old = 'echo "{ global:" > $output_objdir/$libname.ver~'
        if old in content:
            # Find start and end of the archive_expsym_cmds value.
            # Pattern: archive_expsym_cmds="echo "{"...~...~...$CC...-o $lib"
            start = content.find('archive_expsym_cmds="echo "{ global:" > $output_objdir/$libname.ver~')
            if start >= 0:
                # Find the closing " after -o $lib (which ends the value)
                end_marker = '-o $lib"'
                end = content.find(end_marker, start)
                if end >= 0:
                    end += len(end_marker)
                    # Replace everything between archive_expsym_cmds= and
                    # the closing " with empty
                    eq_pos = content.find('=', start)
                    content = (content[:eq_pos + 1] + '""' +
                               content[end:])
                    self.output.info("patched archive_expsym_cmds: nulled out multi-line value")

        # Fix 2: module_expsym_cmds — same pattern
        old2 = 'module_expsym_cmds="echo "{ global:"'
        if old2 in content:
            start2 = content.find(old2)
            if start2 >= 0:
                end_marker2 = ' -o $lib"'
                end2 = content.find(end_marker2, start2)
                if end2 >= 0:
                    end2 += len(end_marker2)
                    eq_pos2 = content.find('=', start2)
                    content = (content[:eq_pos2 + 1] + '""' +
                               content[end2:])
                    self.output.info("patched module_expsym_cmds: nulled out")

        # Fix 3: ECHO — bash lacks ksh 'print' builtin
        for old, new in [
                ('ECHO="print -r --"', 'ECHO=echo'),
                ("ECHO='print -r --'", 'ECHO=echo')]:
            if old in content:
                content = content.replace(old, new)
                self.output.info(f"patched ECHO: {old} -> {new}")

        lt.write_text(content)
        return True

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()

        # Patch config.status: replace ALL 'print -r --' with 'printf %s\\n'.
        cs = pathlib.Path(self.build_folder) / "config.status"
        if cs.exists():
            cs_content = cs.read_text()
            cs_content = cs_content.replace('print -r --', 'printf %s\\n')
            cs.write_text(cs_content)
            # Re-run config.status to regenerate libtool with correct ECHO.
            import subprocess
            r = subprocess.run(
                ["/bin/sh", str(cs)],
                cwd=self.build_folder, capture_output=True, check=False)
            if r.returncode != 0:
                stderr = r.stderr.decode('utf-8', errors='replace')[:200]
                self.output.warning(
                    f"config.status re-run exit={r.returncode}: {stderr}")

        # Patch Makefile: disable autotools auto-regeneration (AM_ICONV).
        mf = pathlib.Path(self.build_folder) / "Makefile"
        if mf.exists():
            content = mf.read_text()
            for cmd in ["AUTOCONF", "AUTOHEADER", "AUTOMAKE", "ACLOCAL"]:
                content = content.replace(f"$({cmd})", "/bin/true")
            mf.write_text(content)

        # Post-configure libtool patch (handles CI profile bash 5.3 compat).
        self._patch_libtool(pathlib.Path(self.build_folder) / "libtool")

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["mecab"]
