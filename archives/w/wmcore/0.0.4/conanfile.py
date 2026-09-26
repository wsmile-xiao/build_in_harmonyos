#!/usr/bin/env python3
"""Conan recipe for wmcore 0.0.4.

wmcore is an X11 **dockapp application** (a per-CPU-core load bar graph that
lives in a Window Maker / dock applet socket), not a library: it is built with
GNU Autotools from a single C file (``wmcore.c``, 215 lines) plus two embedded
image sources (``wmcore_master.xpm`` / ``wmcore_mask.xbm``), and the release
installs one program and one manual page.

Build surface, read from the unpacked 0.0.4 tarball:

* ``configure.ac:16`` is ``PKG_CHECK_MODULES([pkg_config], [x11 xext xpm dockapp])``
  ⇒ the four modules must be resolvable by pkg-config, so ``PkgConfigDeps`` is
  mandatory (``AutotoolsDeps`` alone does not feed ``PKG_CHECK_MODULES``).
* ``Makefile.am`` declares ``bin_PROGRAMS = wmcore`` and ``man_MANS = wmcore.1``;
  the man page is produced by ``AC_CONFIG_FILES([Makefile wmcore.1])`` from
  ``wmcore.1.in`` (a plain ``@PACKAGE_VERSION@`` substitution) ⇒ no asciidoc /
  xmlto toolchain is needed.
* ``wmcore.c`` includes ``X11/Xlib.h``, ``X11/xpm.h``, ``X11/extensions/shape.h``
  and ``libdockapp/{wmgeneral,misc}.h`` ⇒ all four direct dependencies carry
  headers *and* link flags into this package.
* The tree ships **no** ``config.guess``/``config.sub`` and ``configure.ac`` has
  no ``AC_CANONICAL_HOST``, so the config.* family of OHOS patches does not
  apply here; ``/usr/local`` appearing in ``configure`` is only autoconf's
  default prefix, which Conan overrides with ``--prefix``.

OHOS notes
----------
* ``build()`` does not call ``autotools.configure()`` directly: the ohos-aarch64
  profile's ``[buildenv]`` injects ``CONFIG_SHELL=/data/service/hnp/bin/bash``,
  and that bash returns ``EPERM`` from ``getcwd()`` on HMDFS, which makes
  configure die with "working directory cannot be determined" (E386).  The
  unset therefore happens *inside the same shell command*, because Conan sources
  ``conanbuild.sh`` right before running it (a ``generate()``-time
  ``env.unset()`` loses to that re-injection).  The configure arguments are
  still taken from what ``AutotoolsToolchain`` wrote, not hand-assembled here.
* Upstream has no test suite at all (see ``test_package/MANIFEST.yml`` for the
  measured evidence); the canonical ``make check`` target is still executed once
  so the log records "0 tests" instead of silence.
* The device and the CI worker are headless, so ``test_package/`` asserts on the
  two code paths that run before the X connection plus the ELF/platform
  properties of the packaged binary.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class WmcoreConan(ConanFile):
    name = "wmcore"
    version = "0.0.4"
    description = ("X11 dockapp that shows the load of every CPU core as a "
                   "stacked bar graph (Window Maker / libdockapp family)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.dockapps.net/wmcore"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("x11", "dockapp", "cpu", "monitor", "window-maker")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # R32: platform check must accept the OHOS enum as well as Linux.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "wmcore is adapted for Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # configure.ac PKG_CHECK_MODULES asks for exactly these four modules.
        # The version track is the one the published libdockapp/0.7.3 pins
        # (its own requires are libx11/6.4.0 + libxext/6.4.0 + libxpm/3.5.17),
        # so repeating it here keeps a single X11 graph instead of forking it.
        self.requires("libdockapp/0.7.3",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libx11/6.4.0",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17",
                      transitive_headers=True, transitive_libs=True)

    def export_sources(self):
        # No patch today; kept so a future upstream fix ships as a real patch
        # instead of an in-recipe string replace (G1/W2 shape).
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)

    def generate(self):
        # Order mirrors the published libdockapp/0.7.3 recipe: dependency flags
        # first, then the pkg-config .pc files consumed by PKG_CHECK_MODULES,
        # then the toolchain that writes configure_args / CC / CFLAGS.
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._fix_configure_umask()
        autotools = Autotools(self)
        self._configure(autotools)
        autotools.make(args=["-j1"])
        # 上游 0 个测试（实测见 test_package/MANIFEST.yml），canonical check
        # 目标仍执行一次：让日志留下"没有测试可跑"的原始证据而不是沉默。
        autotools.make(target="check", args=["-j1"])

    def _fix_configure_umask(self):
        """E011 / E114: ``umask 077`` in the generated configure breaks HMDFS.

        autoconf 2.69 lets ``config.status`` build its scratch directory with
        ``(umask 077 && mktemp -d "./confXXXXXX")``.  On HMDFS a 0700 directory
        comes back as 0660 (no search bit), so the next
        ``cat >"$ac_tmp/subs1.awk"`` fails with::

            ./config.status: can't create ./conffxDNxi/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery

        Rewriting the literal to ``umask 022`` is the documented prescription
        (E011 rec_approach ``edit-umask-in-configure``) and is applied in place
        inside ``build()`` rather than through ``patches/``, because ``configure``
        is a generated file of the release tarball (corpus convention: 1000+
        recipes, 4ti2/1.6.10 spells out the same R6 rationale).
        """
        path = os.path.join(self.source_folder, "configure")
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        hits = text.count("umask 077")
        if not hits:
            self.output.warn("E011: 'umask 077' not found in configure — "
                             "upstream text changed, config.status may fail")
            return
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.replace("umask 077", "umask 022"))
        self.output.info("E011: rewrote %d occurrence(s) of 'umask 077' "
                         "to 'umask 022' in configure" % hits)

    def _dependency_libdirs(self):
        """Absolute lib directories of the whole host dependency closure."""
        found, seen = [], set()
        for _, dep in self.dependencies.host.items():
            base = dep.package_folder or ""
            for entry in dep.cpp_info.libdirs:
                path = entry if os.path.isabs(entry) else os.path.join(base, entry)
                if os.path.isdir(path) and path not in seen:
                    seen.add(path)
                    found.append(path)
        return found

    def _configure(self, autotools):
        """Run configure with CONFIG_SHELL removed in the very same command.

        E386: the profile ``[buildenv]`` exports
        ``CONFIG_SHELL=/data/service/hnp/bin/bash``, and that bash cannot
        ``getcwd()`` on HMDFS (measured in this very build folder: ``bash -c
        pwd`` prints "shell-init: error retrieving current directory" and exits
        1) ⇒ configure would die with "working directory cannot be determined".
        Conan sources ``conanbuild.sh`` immediately before the command, so a
        ``generate()``-time ``env.unset()`` loses; the variable has to go inside
        the command itself.

        ``LD_LIBRARY_PATH`` is injected for the same run: ``AutotoolsDeps`` puts
        the dependency ``-l`` flags into ``$LIBS``, so autoconf's very first
        program run ("checking whether we are cross compiling") links against
        libdockapp/libX11/... and would otherwise be refused by the loader,
        which configure misreports as "cannot run C compiled programs".
        Arguments still come from ``AutotoolsToolchain``
        (``Autotools._configure_args``), never from hand-written compiler
        switches (R1/R33/R49).
        """
        base_args = getattr(autotools, "_configure_args", None)
        if base_args is None:
            # 回退路径：现代 autoconf 的 configure 未必读 CONFIG_SHELL；届时若
            # 真中招会照原样报错，但至少不会跳过 make。
            self.output.warn("Autotools._configure_args unavailable, "
                             "falling back to autotools.configure()")
            autotools.configure()
            return
        cfg_path = os.path.relpath(os.path.join(self.source_folder, "configure"),
                                   self.build_folder)
        ldpath = ":".join(self._dependency_libdirs())
        self.output.info("configure LD_LIBRARY_PATH=" + ldpath)
        self.run("unset CONFIG_SHELL; LD_LIBRARY_PATH=\"" + ldpath + "\" "
                 + cfg_path + " " + base_args, cwd=self.build_folder)

    def package(self):
        Autotools(self).install(target="install", args=["-j1"])
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # A standalone dockapp program: it exports no header and no library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # `make install DESTDIR=<pkg>` with the toolchain's --prefix=/ puts the
        # manual page under <pkg>/share/man/man1, so `share` is the resource dir.
        self.cpp_info.resdirs = ["share"]
