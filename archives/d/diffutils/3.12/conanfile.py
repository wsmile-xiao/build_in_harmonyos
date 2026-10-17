#!/usr/bin/env python3
"""Conan recipe — diffutils 3.12 (GNU diffutils).

GNU diffutils provides the `diff`, `diff3`, `sdiff` and `cmp` command line
tools for comparing files.  Build system: autotools (configure + make).
No external dependencies (gnulib is bundled in the release tarball).
"""
import os
import shlex
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DiffutilsConan(ConanFile):
    name = "diffutils"
    version = "3.12"
    description = "GNU diffutils — file comparison utilities (diff, diff3, sdiff, cmp)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/diffutils/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"diffutils supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The automake dependency-tracking files (.deps/*.Tpo) are rewritten on
        # every compile; that machinery is fragile on HMDFS and the build does
        # not need the generated dependency files.
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._restore_exec_bits()
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # E232: Autotools.configure() launches the source ./configure as the
            # first process.  On HarmonyOS every child is created through
            # posix_spawn (E055) and such a child cannot execute a script living
            # on HMDFS (the mode has no o+x bits), so the direct launch dies with
            # "Permission denied" / Error 126.  Run configure through the native
            # shell with exactly the arguments Conan generated instead.
            configure_script = os.path.join(self.source_folder, "configure")
            command = (
                "CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
                + shlex.join(["/system/bin/sh", configure_script])
            )
            if autotools._configure_args:
                command = f"{command} {autotools._configure_args}"
            self.run(command, cwd=self.build_folder)
        else:
            autotools.configure()
        self._preserve_prebuilt_docs()
        # A single job avoids make jobserver/FIFO failures on HMDFS.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command line tool package: it exposes binaries, not consumer libraries.
        pass

    def _preserve_prebuilt_docs(self):
        """doc/diffutils.info ships pre-built and must not be regenerated.

        ``doc/stamp-vti`` depends on ``configure``; because the recipe patches
        ``configure`` its mtime becomes newer than the shipped stamp, so make
        would rebuild stamp-vti -> version.texi -> diffutils.info.  That requires
        ``makeinfo`` (texinfo), which is not available in the OHOS build
        environment, and the mdate-sh helper also misbehaves on HarmonyOS.
        Refresh the mtimes so the shipped info file is kept as-is.
        """
        doc_dir = os.path.join(self.source_folder, "doc")
        now = time.time()
        for name in ("stamp-vti", "version.texi", "diffutils.info"):
            path = os.path.join(doc_dir, name)
            if os.path.isfile(path):
                try:
                    os.utime(path, (now, now))
                except OSError as exc:
                    self.output.warning(f"cannot touch doc/{name}: {exc}")

    def _restore_exec_bits(self):
        """E490: HMDFS adaptation paths can lose the exec bit of the autotools
        helper scripts.  chmod() is ignored on HMDFS, so the file has to be
        recreated (fresh inode, umask=0, mode 0o755) to gain an executable bit.
        """
        for name in ("configure", "build-aux/config.guess",
                     "build-aux/config.sub", "build-aux/install-sh",
                     "build-aux/missing", "build-aux/compile",
                     "build-aux/depcomp", "build-aux/test-driver"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as fh:
                    data = fh.read()
                os.unlink(path)
                old_umask = os.umask(0)
                try:
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o755)
                    try:
                        os.write(fd, data)
                    finally:
                        os.close(fd)
                finally:
                    os.umask(old_umask)
            except OSError as exc:
                self.output.warning(f"cannot restore exec bit on {name}: {exc}")
