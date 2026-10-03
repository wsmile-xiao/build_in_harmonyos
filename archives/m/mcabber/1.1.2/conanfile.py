#!/usr/bin/env python3
"""Conan recipe - mcabber 1.1.2 (Autotools: configure + make).

mcabber is a small console XMPP (Jabber) client: a full-screen curses UI on
top of loudmouth/glib.  HarmonyOS (OHOS) aarch64 adaptation notes:

* Every dependency comes from the ohpcd registry (glib, loudmouth, ncurses);
  nothing is taken from the build host.
* loudmouth's conan package declares ``pkg_config_name = "loudmouth-1"`` while
  mcabber's configure.ac probes ``PKG_CHECK_MODULES(..., loudmouth-1.0 >= 1.4.2)``;
  generate() aliases the generated module so that probe resolves.  The
  loudmouth-1.0.pc shipped *inside* loudmouth's own package cannot be used (its
  prefix is the stale ``/`` from the upstream build).
* Optional features whose dependencies are not published for OHOS are pinned
  off (libidn, GPGME, OTR) so configure cannot half-enable them.
* R32: settings.os is checked in ("Linux", "OHOS").
* E129/E011: on OHOS the configure is phased -- run it with ``--no-create``,
  patch the generated config.status umask (HMDFS refuses the setgid directories
  that configure's ``umask 077`` creates), then run config.status with /bin/sh
  (the HNP bash cannot getcwd(2) on the HMDFS build directory).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    rm,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class McabberConan(ConanFile):
    name = "mcabber"
    version = "1.1.2"
    description = "Console Jabber (XMPP) client with a text-mode interface"
    license = "GPL-2.0-or-later"
    homepage = "https://mcabber.com"
    url = "https://mcabber.com"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # loudmouth pulls glib in as well, but configure.ac probes glib directly
        # (AM_PATH_GLIB_2_0) -> declare it explicitly so the module is always
        # generated for the pkg-config probe.
        self.requires("glib/2.84.0.1")
        self.requires("loudmouth/1.5.4")
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: OS check must accept both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mcabber is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-libidn=no",   # libidn is not published for OHOS
            "--disable-gpgme",    # gpgme is not published for OHOS
            "--disable-otr",      # libotr is not published for OHOS
            "--disable-hgcset",   # no mercurial available; keep the plain version
        ])
        # configure.ac only defines HAVE_UNICODE from inside its curses probe
        # (AC_CHECK_LIB(ncursesw, waddnwstr)), and that whole block is skipped
        # once `AC_CHECK_FUNC(initscr)` succeeds -- which is what happens here,
        # because AutotoolsDeps exports the dependencies' libs (-lncursesw ...)
        # through LIBS.  The ncurses package is the wide-character build (its
        # libs are formw/menuw/w panelw/ncursesw), so the macro upstream would
        # have defined is set explicitly: without it mcabber compiles its
        # narrow-curses code paths and drops UTF-8 input/display.  The define is
        # self-checking -- any build that is not really linked against the wide
        # API fails at link time on the waddnwstr* references.
        tc.extra_defines.append("HAVE_UNICODE")
        if self.settings.os == "OHOS":
            # The 2018-era config.guess cannot guess HarmonyOS as the build
            # type.  Declare --host ALONE (no matching --build): a lone --host
            # keeps autoconf in cross_compiling=maybe, so configure skips its
            # runtime probes instead of aborting with "cannot run C compiled
            # programs"; ac_cv_build is pre-seeded in build().
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()

        # configure.ac probes loudmouth through `loudmouth-1.0` (PKG_CHECK_MODULES),
        # while loudmouth's package_info sets pkg_config_name="loudmouth-1", so
        # PkgConfigDeps writes loudmouth-1.pc.  Alias it under the module name
        # mcabber looks for.
        pc = os.path.join(self.generators_folder, "loudmouth-1.pc")
        if os.path.isfile(pc):
            shutil.copyfile(pc, os.path.join(self.generators_folder, "loudmouth-1.0.pc"))

    def _ohos_shell_env(self):
        """Environment that forces configure/config.status/make subprocesses
        onto /bin/sh (toybox ash, whose getcwd(2) works on HMDFS) instead of the
        HNP bash, whose getcwd(2) fails there ("working directory cannot be
        determined").  PWD is preset so the shell trusts a valid logical path."""
        return {
            "SHELL": "/bin/sh",
            "CONFIG_SHELL": "/bin/sh",
            "PWD": self.build_folder,
        }

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # E129/E011: HMDFS sets the setgid bit on new directories; with
            # configure's `umask 077` the config.status temp dirs become
            # drwx--S--- and config.status fails to write its subs files.
            for key, value in self._ohos_shell_env().items():
                os.environ[key] = value
            os.environ["ac_cv_build"] = "aarch64-unknown-linux-gnu"
            autotools.configure(args=["--no-create"])
            config_status = os.path.join(self.build_folder, "config.status")
            if os.path.isfile(config_status):
                text = load(self, config_status)
                if "umask 077" in text:
                    save(self, config_status, text.replace("umask 077", "umask 022"))
            self.run('"/bin/sh" "%s"' % config_status, cwd=self.build_folder)
        else:
            autotools.configure()
        autotools.make(args=["-j%d" % (os.cpu_count() or 1)])

    def package(self):
        Autotools(self).install()
        # libtool archives embed absolute build-machine paths and are not needed
        # at runtime: the plug-ins (lib/mcabber/*.so) are dlopen()ed directly.
        # NB: rm() is non-recursive by default and the plug-ins land one level
        # below lib/ (lib/mcabber/), so recursion has to be requested.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)

    def package_info(self):
        # mcabber is a stand-alone terminal application: it installs a binary
        # (bin/mcabber) plus dlopen()ed modules (lib/mcabber/*.so) -- there is
        # no library for consumers to link against.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Keep the binary on PATH for the consumer's VirtualRunEnv.
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
