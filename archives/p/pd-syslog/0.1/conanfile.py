#!/usr/bin/env python3
"""Conan recipe — pd-syslog 0.1 (Pd Makefile template 1.0.14).

pd-syslog is the Pure Data external `[syslog]`: it forwards anything typed into
its inlet to libc `syslog()` at a settable severity.  Upstream ships only the
Pd library template Makefile plus one C file, so the whole build is driven from
the make command line (see `_make_args()`); no file is patched.

Pd integration (see notes.md):
- The artifact is a Pd plugin: an ELF shared object that Pd `dlopen()`s as
  `<lib>/<lib>/syslog.pd_linux`, resolved against Pd's own `-rdynamic` image.
  Nothing is linked against Pd, so `package_info()` exports no libs.
- The only build input from Pd is the API header `m_pd.h`, which ships inside
  the `puredata/0.54.1` application package.  That package publishes no
  `cpp_info.includedirs`, so the header directory is resolved from the
  dependency's package folder and re-exported, exactly like pd-libdir/1.11.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get


class PdSyslogConan(ConanFile):
    name = "pd-syslog"
    version = "0.1"
    description = "Pure Data external that forwards Pd messages to libc syslog() at a settable severity"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/umlaeute/pd-syslog"
    url = "https://sourcelink.debian.org/src/pd-syslog/"

    # A Pd plugin: a dlopen()ed shared object with a `syslog_setup` entry point,
    # not a CLI tool (no main(), no bin/ install) — hence "library" and no
    # commands.json.
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"

    # Pd dlopen()s the plugin, so it is always shared; the upstream template has
    # no static mode. The option exists only to satisfy conan's 'library'
    # package_type contract and is rejected when False.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        # Pd itself supplies m_pd.h.  The header is the only thing syslog.c
        # needs from Pd; every Pd symbol is resolved from Pd's own -rdynamic
        # image at load time.
        self.requires("puredata/0.54.1")

    # R32: only Linux/OHOS are supported build hosts for this recipe.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                f"{self.ref} is a Pd plugin and must be shared: Pd dlopen()s "
                "syslog.pd_linux, and the upstream Makefile template has no "
                "static mode"
            )

    def _pd_include_dir(self):
        """Directory holding m_pd.h inside the puredata package.

        puredata/0.54.1 is declared as an application package, so it publishes
        no cpp_info.includedirs; the headers are there all the same
        (<pkg>/include/pd/m_pd.h and <pkg>/include/m_pd.h).
        """
        dep = self.dependencies["puredata"]
        for candidate in (os.path.join(dep.package_folder, "include", "pd"),
                          os.path.join(dep.package_folder, "include")):
            if os.path.isfile(os.path.join(candidate, "m_pd.h")):
                return candidate
        raise ConanInvalidConfiguration(
            "puredata/0.54.1 package does not provide m_pd.h "
            f"(looked in {dep.package_folder}/include[/pd])"
        )

    def _compiler(self):
        # R33: never rely on undefined shell env — read the compiler from the
        # Conan profile conf that CI and W3 both set.
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        return executables.get("c") or "clang"

    def _make_args(self, destination=None):
        """make(1) overrides, shared by the build and install invocations.

        The upstream Pd library template honours all of these on the command
        line (its own comment says CFLAGS/LDFLAGS/LIBS "can be set from
        outside without (usually) breaking the build"):
          UNAME      force the Linux branch (see below)
          CC         the cross compiler (its default is plain `gcc`)
          PD_INCLUDE where m_pd.h lives (upstream derives it from
                     PD_PATH=/usr, which does not exist on this platform)
          prefix     install root, so nothing lands in /usr/local
          LDFLAGS    DT_SONAME + strip, so the plugin is identifiable
          STRIP      no-op; see below

        `UNAME=Linux` is required, not cosmetic.  The template picks its
        platform by exact string match on `uname -s` (Linux / Darwin / Android
        / CYGWIN / MINGW / GNU / GNU/kFreeBSD) and has no branch for OHOS: the
        OHOS worker reports `uname` = "HarmonyOS", so the Linux block is
        skipped entirely, `EXTENSION` stays empty, `PD_PATH` is never set and
        the link degenerates to `-o syslog.` with no `-shared`, failing with
        "ld.lld: error: undefined symbol: main" plus every Pd symbol.  That is
        invisible on a Linux dev box — WSL2 reports uname=Linux — so the bug
        only reproduces on the real worker.  Taking the Linux branch gives the
        artifact the name Pd actually looks for on non-Apple platforms
        (`pd_linux`), plus -fPIC/-shared/-rdynamic and -lc.

        `PD_INCLUDE` is overridden directly rather than `PD_PATH`, so the
        recipe does not have to re-derive the layout the puredata package
        happens to use: the template builds `ALL_CFLAGS = -I"$(PD_INCLUDE)"`
        from it, and a make command-line assignment outranks any in-Makefile
        `=` assignment, so this works wherever `_pd_include_dir()` found the
        header.  Upstream's own default (`PD_PATH = /usr`, hence
        `/usr/include/pd`) is only correct for a system-wide Pd install.

        `STRIP=:` disables the install-time strip step.  The template hardcodes
        `STRIP = strip --strip-unneeded -R .note -R .comment`, i.e. the *host*
        binutils strip; on this cross build that binary cannot read the aarch64
        ELF it just produced ("strip: Unable to recognise the format of the
        input file") and `make install` dies.  Stripping is instead requested
        at link time through LDFLAGS below, which uses the same OHOS clang that
        produced the file and therefore works identically on WSL and on the
        worker.
        """
        args = [
            "UNAME=Linux",
            f'CC="{self._compiler()}"',
            f'PD_INCLUDE="{self._pd_include_dir()}"',
            f'prefix="{self.package_folder}"',
            'LDFLAGS="-Wl,-soname,syslog.pd_linux -Wl,-s"',
            "STRIP=:",
        ]
        if destination is not None:
            args.append(f'DESTDIR="{destination}"')
        return " ".join(args)

    def source(self):
        data = self.conan_data["sources"][self.version]
        # The tarball's root directory is `syslog-0.1`, not `pd-syslog-0.1`.
        get(self, url=data["url"], sha256=data["sha256"], strip_root=True)

    def build(self):
        # R9: the template builds a single object file; keep -j1 so the build
        # log stays deterministic.
        self.run(f"make all {self._make_args()} -j1",
                 env="conanbuild", cwd=self.source_folder)

    def package(self):
        # `make install` honours DESTDIR, but prefix already points at the
        # package folder, so no DESTDIR indirection is needed.  The template
        # installs to $(DESTDIR)$(objectsdir)/syslog with
        # objectsdir = $(libdir)/pd-externals and libdir = $(prefix)/lib, i.e.
        # <package>/lib/pd-externals/syslog/ — the upstream default layout
        # (/usr/local/lib/pd-externals/syslog), which is also where Pd looks
        # for an extra library.
        self.run(f"make install {self._make_args()}",
                 env="conanbuild", cwd=self.source_folder)
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # The plugin lives two levels below lib/
        # (lib/pd-externals/syslog/syslog.pd_linux) and is dlopen()'d by Pd by
        # path; it links against nothing, so there are no libs to export.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = ["lib/pd-externals/syslog"]
        self.cpp_info.libs = []
        self.cpp_info.defines = ["PD"]
        # Re-export the Pd API headers resolved above, so consumers can compile
        # Pd code against this package alone (puredata/0.54.1 publishes no
        # include dirs of its own).
        self.cpp_info.includedirs = [self._pd_include_dir()]
