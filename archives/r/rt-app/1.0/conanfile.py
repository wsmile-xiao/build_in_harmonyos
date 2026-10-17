#!/usr/bin/env python3
"""Conan recipe for rt-app, a real-time scheduling test application."""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RtAppConan(ConanFile):
    name = "rt-app"
    version = "1.0"
    description = "Real-time scheduling test application that drives periodic synthetic workloads"
    license = "GPL-2.0-only"
    homepage = "https://github.com/scheduler-tools/rt-app"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must be matched with an ``in`` tuple, never ``== "Linux"``.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rt-app is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds of rt-app require armv8/aarch64")

    def requirements(self):
        self.requires("json-c/0.17", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # The release archive ships only configure.ac, so build() has to
        # bootstrap it with autoreconf, and configure.ac asks for both halves
        # of the autotools stack: AM_INIT_AUTOMAKE (aclocal/automake/
        # autoheader) and AC_PROG_LIBTOOL (libtoolize + libtool.m4).
        # The HarmonyOS SDK ships only the autoconf half under
        # /data/service/hnp/bin, so a bare `autoreconf --install --force`
        # dies there with:
        #   Can't exec "aclocal": No such file or directory at
        #   .../autoconf/Autom4te/FileUtils.pm line 299
        #   autoreconf: error: aclocal failed with exit status: 2
        # (CI build #67859 on worker OpenHarmonyPCDeveloper-CI-033).  Declare
        # the missing half explicitly as build context tools; both recipes
        # already expose ACLOCAL/AUTOMAKE/LIBTOOLIZE plus ACLOCAL_PATH and the
        # relocatability fixups (automake PERL5LIB, libtool _lt_pkgdatadir) via
        # their buildenv_info, which is the same mechanism jool-modules-lts
        # 6.18.39, jbig2enc 0.32 and quickfix 1.15.1 already use.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency_flags(self):
        """Search paths for the recipe's dependencies.

        rt-app's configure.ac locates its dependencies with AC_CHECK_LIB, not
        PKG_CHECK_MODULES, so the pkg-config generator cannot supply the paths
        and they have to be passed to configure explicitly (R49: every path is
        resolved inside the dependency's own conan package folder, i.e. a
        private prefix owned by this build - never a shared /usr/local).
        """
        inc_flags, lib_flags = [], []
        for dep in self.dependencies.values():
            for d in dep.cpp_info.includedirs:
                inc_flags.append("-I" + os.path.join(dep.package_folder, d))
            for d in dep.cpp_info.libdirs:
                lib_flags.append("-L" + os.path.join(dep.package_folder, d))
        return inc_flags, lib_flags

    def generate(self):
        # Put the tool_requires autotools half (aclocal/automake/libtoolize and
        # their ACLOCAL_PATH / PERL5LIB / _lt_pkgdatadir fixups) into the
        # conanbuild environment the Autotools helper runs under; the CI
        # sandbox cannot see the toolchain that was installed by hand under
        # $HOME/.local, so it has to arrive through the recipe.
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # The bundled config.sub (automake 1.16) rejects the ``aarch64-linux-ohos``
        # triplet that Conan derives for OHOS, so target the canonical aarch64
        # triple instead. It canonicalizes to aarch64-unknown-linux-gnu, which
        # config.sub accepts, while the compiler wrapper keeps emitting
        # aarch64-linux-ohos objects and linking against the OHOS sysroot.
        # Both --build and --host are pinned so the behaviour is identical on a
        # native OHOS runner and on a cross host; rt-app's configure.ac contains
        # no AC_RUN_IFELSE, so declaring a native-looking triplet is safe.
        tc.configure_args.extend([
            "--host=aarch64-linux-gnu",
            "--build=aarch64-linux-gnu",
        ])
        tc.generate()

        inc_flags, lib_flags = self._dependency_flags()
        # rt-app's configure.ac declares no AC_ARG_VAR for CPPFLAGS/LDFLAGS, so
        # autoconf rejects both --CPPFLAGS= and --LDFLAGS= on the command line;
        # they are only settable through the environment. The Autotools helper
        # runs configure under the toolchain environment, which is extended in
        # build() with these dependency paths.
        self._configure_argv = list(tc.configure_args)
        self._dep_cppflags = " ".join(inc_flags)
        self._dep_ldflags = " ".join(lib_flags)

    @staticmethod
    def _relax_autoreconf_tmpdir_umask(configure_script):
        """Drop the ``umask 077`` from autoconf's temporary-directory block.

        E011/E129 class: HarmonyOS workers keep their build tree on HMDFS,
        which forces the setgid bit and ignores chmod, so autoconf's
        ``(umask 077 && mktemp -d "./confXXXXXX")`` yields a ``drwx--S---``
        directory that not even its own owner may write. configure then dies
        with::

            ./config.status: line 818: ./confMOKcFd/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery

        (CI build #68375 on worker OpenHarmonyPCDeveloper-CI-019.)

        The block lives in the *generated* configure, so this is a runtime text
        replacement rather than a conandata patch: the tarball has no
        pre-generated configure (patch() runs before autoreconf here), and
        automake 1.18 emits it at a drifting line number anyway, so a patch
        hunk would miss. Same approach as jbig2enc 0.32.

        configure copies this block verbatim into the config.status it
        generates, so relaxing it in configure also fixes config.status.
        Fail-closed: if the expected text is absent the build stops here rather
        than shipping a recipe that only fails on the worker.
        """
        import re
        with open(configure_script, "r", encoding="utf-8") as f:
            data = f.read()
        # Matches "(umask 077 && mktemp -d ...)" and "(umask 077 && mkdir ...)"
        # for either the 2.71 (077) or 2.72 (077) spelling of the mask.
        patched, n = re.subn(r"\(\s*umask 0?0?77\s*&&\s*", "(", data)
        if n == 0:
            raise ConanException(
                "autoreconf-generated configure carries no '(umask 077 && ...)' "
                "temporary-directory block; refusing to continue because the "
                "HMDFS drwx--S--- workaround could not be applied"
            )
        with open(configure_script, "w", encoding="utf-8") as f:
            f.write(patched)
        print("  [ok] E011/E129: dropped %d umask 077 guard(s) in configure" % n)

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)
        # The release archive ships autogen.sh only; no pre-generated configure.
        autotools.autoreconf(args=["--install", "--force"])

        configure_script = os.path.join(self.source_folder, "configure")
        self._relax_autoreconf_tmpdir_umask(configure_script)
        cmd = " ".join([
            f'CPPFLAGS="{self._dep_cppflags}"',
            f'LDFLAGS="{self._dep_ldflags}"',
            f'"{configure_script}"',
        ] + self._configure_argv)
        self.run(cmd)

        autotools.make(args=["-j1"])
        autotools.install()

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # libtool may drop *.la wrappers next to the installed binary.
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        # rt-app is a CLI application: expose the binary and keep it on PATH.
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
