#!/usr/bin/env python3
"""Conan recipe for sedutil 1.20.0 — autotools CLI tool.

sedutil is a command-line tool to manage self encrypting drives that
conform to the Trusted Computing Group OPAL 2.0 SSC specification.
Builds two binaries: sedutil-cli (main tool) and sedutil-pba.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SedutilConan(ConanFile):
    name = "sedutil"
    version = "1.20.0"
    description = "CLI tool to manage self encrypting drives conforming to TCG OPAL 2.0"
    license = "GPL-3.0"
    homepage = "https://github.com/Drive-Trust-Alliance/sedutil"
    url = "https://github.com/Drive-Trust-Alliance/sedutil"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # GitHub archive tarball ships configure.ac/Makefile.am only; the
        # autoreconf-generated configure script must be produced in build().
        # The OHOS CI image has the autoconf family in /data/service/hnp/bin
        # but no automake, so automake is pulled as tool_requires (published on
        # the ohpcd artifact repo, same pattern as merged abiword-plugin-*
        # recipes). autoconf must NOT be added here: its conan dependency chain
        # pulls conan perl/5.42.2 whose PERL5LIB pollutes the system perl
        # (5.42.0) and breaks autoconf's own perl module loading (Cwd.pm).
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)
        # sedutil's Makefile.am assumes in-source builds (linux/GitVersion.sh
        # writes linux/Version.h, -I./linux relative include paths), so force
        # the build folder to the source folder (same pattern as the merged
        # abc/abduco in-source recipes).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # sedutil is a standalone CLI tool, no shared libs needed
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def _run_autogen(self):
        """Regenerate configure/Makefile.in/config.h.in from autotools sources.

        GitHub archive tarballs do not contain the autoreconf-generated
        configure script. On OHOS HMDFS the full autoreconf chain can hit
        autoconf.m4f loading conflicts, so use the aclocal -> autoconf ->
        autoheader -> automake direct chain (same approach as the merged
        abiword-plugin-* recipes).
        """
        src = self.source_folder
        # aclocal generates aclocal.m4 (provides AM_* macros)
        self.run('"${ACLOCAL:-aclocal}" --force',
                 cwd=src, env="conanbuild", ignore_errors=True)
        # autoconf compiles configure.ac -> configure (bypasses autoreconf chain)
        self.run('autoconf -o configure configure.ac',
                 cwd=src, env="conanbuild", ignore_errors=True)
        if not os.path.exists(os.path.join(src, "configure")):
            raise ConanException("autoconf failed to generate configure")
        # autoheader generates config.h.in
        self.run('autoheader', cwd=src, env="conanbuild", ignore_errors=True)
        if not os.path.exists(os.path.join(src, "config.h.in")):
            # touch fallback if autoheader produced no output
            open(os.path.join(src, "config.h.in"), "w").close()
        # automake generates Makefile.in + install-sh/missing/depcomp
        self.run('"${AUTOMAKE:-automake}" --add-missing --copy --no-force',
                 cwd=src, env="conanbuild", ignore_errors=True)

    def build(self):
        apply_conandata_patches(self)
        self._run_autogen()
        # Fix CONFIG_SHELL from profile that may point to non-existent path
        bash_path = shutil.which("bash") or "/bin/sh"
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            # Insert CONFIG_SHELL fallback after shebang line
            if content.startswith("#!"):
                shebang = content.split("\n", 1)[0]
                rest = content.split("\n", 1)[1] if "\n" in content else ""
                fallback = (
                    f'{shebang}\n'
                    f'# Override invalid paths from Conan profile\n'
                    f'if [ ! -x "$CONFIG_SHELL" ] 2>/dev/null; then\n'
                    f'  CONFIG_SHELL={bash_path}\n'
                    f'  export CONFIG_SHELL\n'
                    f'fi\n'
                    f'if [ ! -x "$SHELL" ] 2>/dev/null; then\n'
                    f'  SHELL={bash_path}\n'
                    f'  export SHELL\n'
                    f'fi\n'
                    f'if [ -n "$CC" ] && [ ! -x "$CC" ] 2>/dev/null; then\n'
                    f'  CC=clang\n'
                    f'  export CC\n'
                    f'fi\n'
                    f'if [ -n "$CXX" ] && [ ! -x "$CXX" ] 2>/dev/null; then\n'
                    f'  CXX=clang++\n'
                    f'  export CXX\n'
                    f'fi\n'
                )
                content = fallback + rest
                with open(configure_path, "w") as f:
                    f.write(content)
        os.environ["CONFIG_SHELL"] = bash_path
        os.environ["SHELL"] = bash_path
        # Fix umask 077 issue on HMDFS (E002-related): directories created
        # with umask 077 get setgid bit which prevents file creation
        for fn in ["configure", "config.status"]:
            p = os.path.join(self.source_folder, fn)
            if os.path.exists(p):
                with open(p, "r") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(p, "w") as f:
                    f.write(content)
        # Restore execute bits on autotools helper scripts (E490)
        for fn in ["configure", "install-sh", "missing", "depcomp", "compile"]:
            p = os.path.join(self.source_folder, fn)
            if os.path.exists(p):
                os.chmod(p, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # sedutil is a standalone CLI tool, no libraries to export
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["sbin"]
