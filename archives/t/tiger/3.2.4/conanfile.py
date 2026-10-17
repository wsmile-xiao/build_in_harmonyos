#!/usr/bin/env python3
"""Conan recipe for tiger — the UNIX security checking system (3.2.4).

Upstream : https://savannah.nongnu.org/projects/tiger/
Source   : official Savannah release tarball ``tiger_3.2.4rc1.tar.gz``.
           The 3.2.4 series has no final tarball upstream (the git tags stop at
           ``version_3_2_3``), so 3.2.4rc1 is the released 3.2.4 artifact; the
           file is byte identical to Debian's ``tiger_3.2.4~rc1.orig.tar.gz``.
License  : GPL-2.0-or-later

Build system
------------
A hand written ``Makefile.in`` driven by a pre-generated Autoconf 2.69
``configure`` (no automake, no CMake, no upstream test suite).  The Makefiles
have no VPATH support, therefore the package is built in-source: the build and
source folders are the same directory.

HarmonyOS (OHOS) adaptation
---------------------------
* ``configure``, ``Makefile`` and every installed script point at ``/bin/sh``,
  which does not exist on OHOS (knowledge entry E165).  The interpreter paths
  are resolved on the build machine (``/system/bin/sh`` first) and written into
  ``configure``, into ``SHELL=`` for make, and into every installed script.
* ``SHELL``/``CONFIG_SHELL`` are left to the OHOS profile
  (``/data/service/hnp/bin/bash``); the shells that actually execute the build
  are forced explicitly rather than through the environment -- the configure
  shebang is rewritten and ``SHELL=`` is passed on the make command line,
  because make(1) ignores the environment variable and ``Makefile.in`` pins
  ``SHELL = /bin/sh``.
* ``umask 077`` in ``configure`` / ``config.status`` is relaxed to ``umask 022``
  (knowledge entry E129: HMDFS always sets the setgid bit on new directories and
  ``umask 077`` produces directories the owner cannot write to).
* Two upstream patches are applied, see ``conandata.yml``.

This recipe targets the project's native build model (build == host ==
OHOS/aarch64), see ``docs/ADAPTATION_GUIDE.md`` section 2.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Installation layout.  tiger bakes these absolute paths into the installed
# scripts during `make install`; DESTDIR puts them inside the package folder.
TIGER_HOME = "/share/tiger"      # scripts, systems/, util/, doc/, helper bins
TIGER_BIN = "/bin"               # tiger, tigexp, tigercron
TIGER_CONFIG = "/etc/tiger"      # tigerrc, cronrc
TIGER_WORK = "/var/tiger/run"    # scratch space used while checks run
TIGER_LOG = "/var/tiger/log"     # default report directory
TIGER_MAN = "/share/man"         # man8 pages


class TigerConan(ConanFile):
    name = "tiger"
    version = "3.2.4"
    description = ("Tiger - security auditing and intrusion detection toolset "
                   "for Unix-like systems")
    license = "GPL-2.0-or-later"
    homepage = "https://savannah.nongnu.org/projects/tiger/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # tiger's Makefiles are not VPATH aware: configure generates c/Makefile
        # and doc/Makefile next to the sources and the C programs are compiled
        # from the directory they live in, so build in-source.
        basic_layout(self, src_folder=".", build_folder=".")

    def requirements(self):
        # W0: tiger links against libc only.  It shells out to the platform's
        # utilities (sh, awk, sed, grep, ...) and has no Conan level dependency,
        # so nothing has to be published before this recipe.
        pass

    def validate(self):
        # R32: platform checks must accept both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tiger/3.2.4 supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _first_existing(*candidates):
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _interpreter_map(self):
        """Resolve the upstream FHS interpreter paths to interpreters that exist.

        HarmonyOS has no /bin (E165): the toybox shell lives in /system/bin and
        bash/perl come from the hnp toolchain.  Paths are detected, never
        hardcoded blindly, so a Linux build maps to itself and rewrites nothing.
        """
        mapping = {}
        shell = self._first_existing("/system/bin/sh", "/bin/sh")
        if shell:
            mapping["/bin/sh"] = shell
        bash = self._first_existing("/data/service/hnp/bin/bash", "/bin/bash",
                                    shutil.which("bash"))
        if bash:
            mapping["/bin/bash"] = bash
        perl = self._first_existing("/data/service/hnp/bin/perl", "/usr/bin/perl",
                                    shutil.which("perl"))
        if perl:
            mapping["/usr/bin/perl"] = perl
            mapping["/usr/local/bin/perl"] = perl
        return mapping

    def _rewrite_shebangs(self, mapping):
        """Point the installed scripts at interpreters that exist (E165)."""
        byte_map = {key.encode(): value.encode() for key, value in mapping.items()}
        rewritten = 0
        for root, _dirs, names in os.walk(self.package_folder):
            for name in names:
                path = os.path.join(root, name)
                try:
                    with open(path, "rb") as handle:
                        head = handle.readline(256)
                except OSError:
                    continue
                if not head.startswith(b"#!"):
                    continue
                parts = head[2:].split()
                if not parts or parts[0] not in byte_map:
                    continue
                with open(path, "rb") as handle:
                    content = handle.read()
                first, newline, rest = content.partition(b"\n")
                parts = first[2:].split()
                new_first = b"#!" + b" ".join(
                    [byte_map.get(parts[0], parts[0])] + parts[1:])
                if new_first == first:
                    continue
                with open(path, "wb") as handle:
                    handle.write(new_first + newline + rest)
                rewritten += 1
        self.output.info(f"tiger: rewrote {rewritten} script shebangs using "
                         f"{mapping}")

    # ------------------------------------------------------------------- recipe

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        # AutotoolsToolchain already passes `--prefix=/`, which keeps every
        # default path relative to the package folder.
        toolchain.configure_args.extend([
            f"--with-tigerhome={TIGER_HOME}",
            f"--with-tigerbin={TIGER_BIN}",
            f"--with-tigerconfig={TIGER_CONFIG}",
            f"--with-tigerwork={TIGER_WORK}",
            f"--with-tigerlog={TIGER_LOG}",
            f"--mandir={TIGER_MAN}",
        ])

        # SHELL/CONFIG_SHELL are deliberately left to the OHOS profile
        # (/data/service/hnp/bin/bash).  They are exported by
        # conanbuildenv-*.sh, which is sourced after this toolchain script, so a
        # define here would not take effect anyway; the shell that matters for
        # `./configure` itself is handled by the shebang rewrite in build().
        toolchain.generate()

    def _build_shell(self):
        """POSIX shell to drive configure/make with, or None when /bin/sh is fine."""
        if self.settings.os != "OHOS":
            return None
        shell = self._interpreter_map().get("/bin/sh")
        return shell if shell and shell != "/bin/sh" else None

    def _make_args(self):
        """Command line arguments for every make invocation.

        R9: single threaded.  tiger's hand written install target relies on the
        prerequisite order (installdirs before installbinaries / installconfig /
        installmanpages) and the Makefile has no .NOTPARALLEL, so a parallel
        `make install` races: the device run failed with
        "can't create .../bin/./tigexp: No such file or directory" because
        installdirs had not finished yet.  SHELL is passed on the command line
        because make(1) ignores the environment variable and Makefile.in pins
        `SHELL = /bin/sh`.
        """
        args = ["-j1"]
        shell = self._build_shell()
        if shell:
            args.append(f"SHELL={shell}")
        return args

    def build(self):
        apply_conandata_patches(self)

        shell = self._build_shell()
        if shell:
            # `./configure` is exec'd directly by Conan, so its own shebang has
            # to resolve (E165).  autoconf 2.69 writes exactly one such line.
            replace_in_file(self, os.path.join(self.source_folder, "configure"),
                            "#! /bin/sh", f"#!{shell}")

            # E129: HMDFS sets the setgid bit on new directories, so a
            # `umask 077` temporary directory ends up drwx--S--- and even its
            # owner cannot write into it ("could not setup config files
            # machinery").
            replace_in_file(self, os.path.join(self.source_folder, "configure"),
                            "umask 077", "umask 022")

        autotools = Autotools(self)
        autotools.configure()

        if shell:
            # configure regenerates config.status from its own templates, so the
            # umask has to be relaxed there as well.
            config_status = os.path.join(self.source_folder, "config.status")
            if os.path.exists(config_status):
                replace_in_file(self, config_status, "umask 077", "umask 022",
                                strict=False)

        autotools.make(args=self._make_args())

    def package(self):
        autotools = Autotools(self)
        # `make install` needs the same -j1 / SHELL treatment as `make all`
        # (see _make_args); Autotools.install() prepends DESTDIR itself.
        autotools.install(args=self._make_args())

        if self.settings.os == "OHOS":
            mapping = self._interpreter_map()
            if mapping:
                self._rewrite_shebangs(mapping)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Command line tools, not a library (P01 package shape).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
