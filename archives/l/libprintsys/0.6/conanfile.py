#!/usr/bin/env python3
"""Conan recipe — libprintsys 0.6 (printcap parser, helper for gnulpr's printfilters).

Upstream: https://lpr.sourceforge.net/  (GNU gnulpr / LPR-ng project)

OHOS adaptation notes (all verified during the explore build):

1. glib detection.  configure.in uses AM_PATH_GLIB(1.2.0), i.e. it probes for the
   `glib-config` helper script that GLib 1.x shipped and that no longer exists in
   GLib 2.x.  Debian fixes this by patching configure.in to AM_PATH_GLIB_2_0 and
   re-running autoconf; we instead feed the existing autoconf-2.13 `configure` a
   small `glib-config` shim whose flags come from the Conan glib dependency
   (via pkg-config on the generated .pc files).  That keeps the source tree
   untouched and needs no automake/libtool regeneration at build time.

2. tdb detection.  `src/printsys.c` does `#include <tdb.h>` and calls
   tdb_open/fetch/store/close unconditionally, so TDB is a hard build- and
   link-time dependency.  Upstream src/Makefile.am narrows both sides down to
   glib only — `INCLUDES=$(GLIB_CFLAGS)` and `LDFLAGS=$(GLIB_LIBS)` — so tdb
   reaches the compiler and linker through the same glib-config shim (verified:
   without it the build dies on "'tdb.h' file not found", and passing -L in
   LDFLAGS alone dies on "ld.lld: error: unable to find library -ltdb").

3. libtool 1.3.3.  The tarball ships its own `ltconfig`.  It runs its
   "Transform linux* to *-*-linux-gnu*" case on $host_os *before* host_os is
   assigned, so the normalisation never fires, host_os stays "linux-ohos",
   matches no OS branch, dynamic_linker stays unset and can_build_shared
   becomes "no" -> only libprintsys.a is produced.  Patch 0003 adds
   linux-ohos to the Linux ELF branch (same fix as archives/c/cpu/1.4.3).

4. Missing DT_NEEDED.  ltconfig sorts -lglib-2.0/-ltdb into old_deplibs rather
   than $deplibs, so archive_cmds never passes them to the linker and
   libprintsys.so ends up with only libc.so in DT_NEEDED while still
   referencing 24 g_* and 4 tdb_* symbols (the pcap executable built by the
   same libtool does get the full set).  Every consumer then fails, at link
   time with --no-allow-shlib-undefined or at run time with
   "Error relocating libprintsys.so.1: g_*: symbol not found".
   _relink_shared_library() rebuilds the .so from the already compiled objects
   with -Wl,--no-as-needed, which fixes the artifact itself instead of pushing
   linker workarounds onto consumers.
"""

import os
import re
import stat

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, load, rm, save)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibprintsysConan(ConanFile):
    name = "libprintsys"
    version = "0.6"
    description = ("C library that parses and writes /etc/printcap, providing the "
                   "printer-document database API used by gnulpr's printfilters")
    license = "GPL-2.0-or-later"
    homepage = "https://lpr.sourceforge.net/"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # glib: hard dependency (g_malloc/g_string_*/g_hash_table_*/g_list_* used
        #       in printsys.c and printcap.c)
        # tdb : hard dependency (#include <tdb.h>, tdb_open/fetch/store/close)
        self.requires("glib/2.88.3")
        self.requires("tdb/1.4.15")

    def build_requirements(self):
        # The glib-config shim resolves flags through pkg-config on the .pc files
        # that PkgConfigDeps generates, so a pkg-config binary must be present.
        self.tool_requires("pkgconf/3.0.6")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _shim_contents(self, pkgconfig_dir, glib_version):
        """glib-config replacement understood by the autoconf-2.13 AM_PATH_GLIB probe.

        Upstream src/Makefile.am narrows the compile and link flags down to
        $(GLIB_CFLAGS)/$(GLIB_LIBS) — which are exactly what this script is asked
        for — so tdb must be folded into the same output, otherwise printsys.c
        fails on `#include <tdb.h>` and the link loses -L for -ltdb.

        --version must agree with GLIB_MAJOR/MINOR/MICRO_VERSION baked into
        glibconfig.h, otherwise the macro's version cross-check fails.
        """
        return f"""#!/bin/sh
# glib-config shim generated by the libprintsys Conan recipe.
# GLib 1.x shipped a glib-config script; the bundled configure probes for it.
# Answers from pkg-config on the .pc files that PkgConfigDeps generated, and
# folds in tdb because upstream only propagates these two variables further.
PKG_CONFIG_PATH="{pkgconfig_dir}${{PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}}"
export PKG_CONFIG_PATH
case "$1" in
  --cflags)  exec pkg-config --cflags glib-2.0 tdb ;;
  --libs)
    # AM_PATH_GLIB compiles *and runs* its conftest, so the probe must also be
    # loadable at run time.  LD_LIBRARY_PATH does not reliably reach it (see
    # _strip_probe_rpaths: on the CI worker the value arriving from
    # VirtualBuildEnv was not usable by the conftest), so give the probe its own
    # DT_RUNPATH via -Wl,-rpath for each -L pkg-config reports.
    # NOTE: because upstream src/Makefile.am narrows LDFLAGS to $(GLIB_LIBS),
    # these rpath flags would otherwise be baked into bin/pcap too; build() strips
    # them from the generated Makefiles before make runs.
    libs=$(pkg-config --libs glib-2.0 tdb) || exit 1
    rpaths=$(echo "$libs" | tr ' ' '\\n' | grep '^-L' | sed 's/^-L/-Wl,-rpath,/' | tr '\\n' ' ')
    echo "$rpaths$libs" ;;
  --version) echo "{glib_version}" ;;
  --prefix)  pkg-config --variable=prefix glib-2.0 ;;
  *) echo "usage: glib-config {{--cflags|--libs|--version|--prefix}}" >&2; exit 1 ;;
esac
"""

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
        # The static archive doubles as the reliable input for
        # _relink_shared_library(); libtool's .libs/*.o objects are already gone
        # by the time package() runs.
        tc.configure_args.append("--enable-static")
        # E007 forbids --host/--build: they flip configure into cross-compiling
        # mode and make every AC_RUN_IFELSE probe return a hardcoded default.
        tc.generate()

        # .pc files for the glib-config shim to resolve flags against.
        PkgConfigDeps(self).generate()

        shim_path = os.path.join(self.build_folder, "glib-config")
        save(self, shim_path,
             self._shim_contents(self.generators_folder,
                                 self.dependencies["glib"].ref.version))
        os.chmod(shim_path, os.stat(shim_path).st_mode
                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # AM_PATH_GLIB compiles *and runs* a probe.  Under Conan the compiler is
        # treated as native (not a cross-compiler), so that probe really executes
        # and needs the dependency shared objects resolvable at run time,
        # otherwise configure aborts with "Could not run GLIB test program ...
        # set your LD_LIBRARY_PATH".
        env = Environment()
        env.define("GLIB_CONFIG", shim_path)
        libdirs = []
        for dep in self.dependencies.host.values():
            agg = dep.cpp_info.aggregated_components()
            libdirs.extend(os.path.join(dep.package_folder, d) for d in agg.libdirs)
        if libdirs:
            env.prepend_path("LD_LIBRARY_PATH", libdirs)
        env.vars(self, scope="build").save_script("libprintsys_configure_env")
        VirtualBuildEnv(self).generate()

    def _strip_probe_rpaths(self):
        """Drop the probe-only -Wl,-rpath flags before make links anything.

        The shim's rpaths exist solely so configure's conftest can load libglib.
        Since upstream puts $(GLIB_LIBS) into LDFLAGS, the same string would also
        be baked into bin/pcap as an absolute build-machine RUNPATH, so remove it
        from the generated Makefiles now that configure has finished.  The shared
        library is relinked later without them either way.
        """
        for makefile in ("Makefile", "src/Makefile"):
            path = os.path.join(self.build_folder, makefile)
            if not os.path.isfile(path):
                continue
            text = load(self, path)
            stripped = re.sub(r"\s*-Wl,-rpath,\S*", "", text)
            if stripped != text:
                save(self, path, stripped)

    def build(self):
        apply_conandata_patches(self)
        # E490: the tarball arrives without execute bits on the Autotools helper
        # scripts, which makes ./configure fail before it can probe anything.
        for script in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "mkinstalldirs", "ltconfig",
                       "ltmain.sh", "src/ltmain.sh"):
            path = os.path.join(self.source_folder, script)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode
                         | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        autotools = Autotools(self)
        autotools.configure()
        self._strip_probe_rpaths()
        autotools.make(args=["-j1"])

    def _link_dirs_and_libs(self):
        """Absolute -L/-l flags for the direct dependencies, from their cpp_info."""
        libdirs, libs = [], []
        for name in ("glib", "tdb"):
            dep = self.dependencies[name]
            agg = dep.cpp_info.aggregated_components()
            libdirs.extend(os.path.join(dep.package_folder, d) for d in agg.libdirs)
            libs.extend(agg.libs)
        return libdirs, libs

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        # src/Makefile.am installs only printsys.h although printcap.h is part of
        # the public API (pcaptest.c includes it), so ship it explicitly.
        copy(self, "printcap.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        # libtool .la files here point at glib/tdb .la paths from the build
        # machine; Debian had to widen its runtime deps because of them
        # (changelog 0.6-6.1). Conan resolves deps itself, so drop them.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        self._relink_shared_library()

    def _relink_shared_library(self):
        """Give libprintsys.so the DT_NEEDED entries libtool 1.3.3 never writes.

        ltconfig builds the shared object with
            archive_cmds='$CC -shared $libobjs $deplibs $linkopts ... -o $lib'
        and sorts the Conan-provided -lglib-2.0/-ltdb into old_deplibs instead of
        $deplibs, so they never reach the linker and the result carries only
        libc.so while still referencing 24 g_* and 4 tdb_* symbols.  The OHOS
        loader (lld --as-needed, musl ld.so) then fails for every consumer:
        either at link time with --no-allow-shlib-undefined, or at run time with
        "Error relocating libprintsys.so.1: g_list_prepend: symbol not found".
        Relinking the already built objects with --no-as-needed records the
        dependencies properly; this is the same command line libtool uses for
        the pcap executable, which does get the full set.
        """
        if not self.options.shared:
            return
        libdir = os.path.join(self.package_folder, "lib")
        soversioned = os.path.join(libdir, "libprintsys.so.1.0.0")
        archive = os.path.join(libdir, "libprintsys.a")
        if not (os.path.isfile(soversioned) and os.path.isfile(archive)):
            raise ConanException(
                "cannot relink libprintsys.so: expected "
                f"{soversioned} and {archive} (missing means the DT_NEEDED "
                "fix silently regressed)")
        libdirs, libs = self._link_dirs_and_libs()
        # R33: resolve the compiler from the profile conf, exactly like
        # AutotoolsToolchain does.  Note this must be self.conf (profile [conf])
        # and not self.conf_info (which only carries conf contributed by
        # dependencies and therefore reads back None here).
        cc = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict).get("c")
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables has no 'c' entry; refusing to "
                "relink libprintsys.so with a bare compiler name resolved via PATH")
        cmd = " ".join([
            f'"{cc}"', "-shared",
            "-Wl,-soname,libprintsys.so.1",
            "-Wl,--whole-archive", f'"{archive}"', "-Wl,--no-whole-archive",
            "-Wl,--no-as-needed",
            " ".join(f'-L"{d}"' for d in libdirs),
            " ".join(f"-l{l}" for l in libs),
            "-lm -lpthread",
            f'-o "{soversioned}"',
        ])
        self.output.info(f"relinking libprintsys.so with explicit DT_NEEDED")
        self.run(cmd, env=["conanbuild"])
        rm(self, "libprintsys.a", libdir)
        # HMDFS ignores chmod and cannot overwrite a symlink: unlink first (R9).
        for link in ("libprintsys.so.1", "libprintsys.so"):
            path = os.path.join(libdir, link)
            if os.path.islink(path) or os.path.exists(path):
                os.remove(path)
            os.symlink("libprintsys.so.1.0.0", path)

    def package_info(self):
        self.cpp_info.libs = ["printsys"]
        # bin/pcap ships with the package, so this is not a pure library: declare
        # it, otherwise R38/PF8 sees a library-type package carrying a
        # commands.json and rejects the combination.
        self.cpp_info.bindirs = ["bin"]
        # DT_NEEDED is repaired at packaging time (see _relink_shared_library),
        # so consumers only need the dependencies on their own link line.
        self.cpp_info.requires = ["glib::glib", "tdb::tdb"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
