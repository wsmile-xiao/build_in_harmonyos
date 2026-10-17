#!/usr/bin/env python3
"""Conan recipe for vsearch 2.30.5 on OpenHarmony.

The GitHub archive omits configure. The recipe ships a pre-generated configure
script so the CI worker does not need autoconf or automake.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.scm import Git


class VsearchConan(ConanFile):
    name = "vsearch"
    version = "2.30.5"
    description = "Versatile open-source tool for microbiome analysis."
    license = "BSD-2-Clause OR GPL-3.0-or-later"
    homepage = "https://github.com/torognes/vsearch"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    # Export the directory so source() can access patches/configure from the
    # exported recipe cache, preserving the path used below.
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source = self.conan_data["sources"]
        clone_folder = os.path.join(self.source_folder, "_upstream")
        git = Git(self, clone_folder)
        git.clone(url=source["url"], target=".")
        # On OHOS the Conan worker UID can differ from the cache directory
        # owner. Trust only this just-cloned directory for this checkout;
        # do not persist a global safe.directory exception.
        git.run(f'-c safe.directory="{clone_folder}" checkout {source["commit"]}')

        # exports_sources has already placed patches/ in source_folder, so
        # clone in a child directory and then merge the upstream source tree.
        for entry in os.listdir(clone_folder):
            if entry != ".git":
                shutil.move(os.path.join(clone_folder, entry), self.source_folder)
        shutil.rmtree(clone_folder)

        # The upstream repository omits generated Autotools output. Ship the
        # matching scripts and templates so offline CI can run configure.
        executable_files = (
            "configure", "compile", "missing", "install-sh", "depcomp",
            "config.guess", "config.sub",
        )
        template_files = (
            "aclocal.m4", "config.h.in", "Makefile.in",
            os.path.join("src", "Makefile.in"),
            os.path.join("man", "Makefile.in"),
        )
        for filename in executable_files + template_files:
            source = os.path.join(self.source_folder, "patches", filename)
            destination = os.path.join(self.source_folder, filename)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(source, destination)
        for filename in executable_files:
            destination = os.path.join(self.source_folder, filename)
            os.chmod(destination, 0o755)
        self.output.info("Pre-generated Autotools files installed.")

    def generate(self):
        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/vsearch")
            os.makedirs(tmpdir, exist_ok=True)

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        if str(self.settings.os) == "OHOS":
            # The upstream configure script rejects config.guess' HarmonyOS
            # output. Use the OHOS triplet accepted by the bundled config.sub.
            triplet = "aarch64-unknown-linux-ohos"
            tc.configure_args.extend([f"--build={triplet}", f"--host={triplet}"])
        tc.generate()

    @staticmethod
    def _patch_configure_tempdir(configure):
        """Make generated config.status use a writable OHOS temporary directory."""
        with open(configure, encoding="utf-8") as file:
            contents = file.read()
        patched = contents.replace(
            '(umask 077 && mktemp -d "./confXXXXXX")',
            '(umask 002 && mktemp -d "${TMPDIR:-.}/confXXXXXX")',
        ).replace(
            'tmp=./conf$$-$RANDOM',
            'tmp=${TMPDIR:-.}/conf$$-$RANDOM',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            '(umask 002 && mkdir "$tmp")',
        )
        expected_tmpdir = '(umask 002 && mktemp -d "${TMPDIR:-.}/confXXXXXX")'
        expected_fallback = '(umask 002 && mkdir "$tmp")'
        if patched == contents and (
            expected_tmpdir not in contents or expected_fallback not in contents
        ):
            raise ConanException(
                f"Could not patch {configure} temporary directory handling"
            )
        if patched != contents:
            with open(configure, "w", encoding="utf-8", newline="") as file:
                file.write(patched)
            os.utime(configure, None)

    @staticmethod
    def _verify_config_status_tempdir(config_status):
        with open(config_status, encoding="utf-8") as file:
            contents = file.read()
        stale_patterns = (
            '(umask 077 && mktemp -d "./confXXXXXX")',
            'tmp=./conf$$-$RANDOM',
            '(umask 077 && mkdir "$tmp")',
        )
        remaining = [pattern for pattern in stale_patterns if pattern in contents]
        if remaining:
            raise ConanException(
                f"config.status still uses HMDFS-incompatible temp dirs: {remaining}"
            )

    @staticmethod
    def _disable_autotools_remake_rules(makefile):
        """Keep make from regenerating Autotools files shipped by the recipe."""
        with open(makefile, encoding="utf-8") as file:
            contents = file.read()

        replacements = (
            (
                "Makefile: $(srcdir)/Makefile.in $(top_builddir)/config.status",
                "Makefile: $(srcdir)/Makefile.in",
            ),
            (
                "$(top_builddir)/config.status: $(top_srcdir)/configure $(CONFIG_STATUS_DEPENDENCIES)",
                "$(top_builddir)/config.status:",
            ),
            (
                "$(top_srcdir)/configure: $(am__configure_deps)",
                "$(top_srcdir)/configure:",
            ),
            (
                "$(ACLOCAL_M4): $(am__aclocal_m4_deps)",
                "$(ACLOCAL_M4):",
            ),
            (
                "$(srcdir)/Makefile.in: $(srcdir)/Makefile.am $(am__configure_deps)",
                "$(srcdir)/Makefile.in:",
            ),
            (
                "stamp-h1: $(srcdir)/config.h.in $(top_builddir)/config.status",
                "stamp-h1:",
            ),
        )

        patched = contents
        changed = False
        for old, new in replacements:
            if old in patched:
                patched = patched.replace(old, new, 1)
                changed = True
        if not changed:
            raise ConanException(f"Could not find Autotools remake rules in {makefile}")
        with open(makefile, "w", encoding="utf-8", newline="") as file:
            file.write(patched)

    def build(self):
        apply_conandata_patches(self)

        # shutil.copy2() preserves the generated templates' original mtime.
        # Refresh them before configure so make does not try to run the
        # unavailable aclocal/automake tools on the OHOS build worker.
        generated_templates = (
            "aclocal.m4", "config.h.in", "Makefile.in",
            os.path.join("src", "Makefile.in"),
            os.path.join("man", "Makefile.in"),
        )
        for filename in generated_templates:
            template = os.path.join(self.build_folder, filename)
            if os.path.isfile(template):
                os.utime(template, None)

        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/vsearch")
            os.makedirs(tmpdir, exist_ok=True)
            # Conan 2.29 does not add recipe buildenv_info to conanbuildenv.
            # Set TMPDIR on this process so configure and config.status inherit it.
            os.environ["TMPDIR"] = tmpdir

        # Conan source copies can lose the executable bit on OHOS HMDFS.
        source_configure = os.path.join(self.source_folder, "configure")
        build_configure = os.path.join(self.build_folder, "configure")
        if str(self.settings.os) == "OHOS":
            # Conan may copy the source tree into build_folder before build().
            # Patch both templates because this Autotools helper executes the
            # build-folder copy, and make can regenerate config.status from it.
            for configure in (source_configure, build_configure):
                if not os.path.isfile(configure):
                    raise ConanException(f"Missing configure script: {configure}")
                os.chmod(configure, 0o755)
                self._patch_configure_tempdir(configure)
        elif os.path.isfile(build_configure):
            os.chmod(build_configure, 0o755)

        autotools = Autotools(self)
        autotools.configure()

        if str(self.settings.os) == "OHOS":
            # Autotools.configure() can refresh the build-folder script from
            # Conan's copied source tree. Patch it again with the generated
            # config.status before make can invoke either file.
            self._patch_configure_tempdir(build_configure)
            self._patch_configure_tempdir(
                os.path.join(self.build_folder, "config.status")
            )
            self._verify_config_status_tempdir(
                os.path.join(self.build_folder, "config.status")
            )
            # HMDFS can make configure/config.status appear newer than the
            # files they just generated. Configuration already completed, so
            # disable only the maintainer remake rules that would invoke them
            # again during make.
            for filename in (
                "Makefile",
                os.path.join("src", "Makefile"),
                os.path.join("man", "Makefile"),
            ):
                self._disable_autotools_remake_rules(
                    os.path.join(self.build_folder, filename)
                )

        # On OHOS HMDFS, make can incorrectly consider config.status newer
        # than the files it just generated. Keep the configured outputs newer
        # to prevent a second config.status invocation during make.
        generated_outputs = (
            "Makefile", "config.h", "stamp-h1",
            os.path.join("src", "Makefile"),
            os.path.join("man", "Makefile"),
        )
        for filename in generated_outputs:
            output = os.path.join(self.build_folder, filename)
            if os.path.isfile(output):
                os.utime(output, None)

        autotools.make()
        autotools.make(target="check")

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
