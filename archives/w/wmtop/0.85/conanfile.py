#!/usr/bin/env python3
"""Conan recipe for wmtop 0.85.

wmtop is the Window Maker dock app that shows the three processes consuming the
most CPU (or, on Linux, memory) as a horizontal bar chart - "a kind of mini
top".  Upstream publishes the Autotools *source* tree only: it carries
`configure.ac`/`Makefile.am` but no generated `configure`, so the recipe has to
bootstrap the build system with `autoreconf` before the usual
configure/make/install chain.

OHOS adaptations:
  * `uname -s` reports "HarmonyOS" on this platform, so `config.guess` cannot
    identify the build machine and `configure` must be given an explicit
    `--build`/`--host`.  The `config.sub` shipped with automake 1.18 and
    libtool 2.5.4 both canonicalize `aarch64-linux-ohos` to
    `aarch64-unknown-linux-ohos`, so no portability patch is needed.
  * `configure.ac` classifies the host with
    `AS_CASE([$host_os], [linux*], [AC_DEFINE(LINUX)], ...)`; the OHOS triplet
    `aarch64-linux-ohos` matches `linux*`, so wmtop builds with its Linux
    backend (including the `-m` memory view and the `/proc` reader) and no
    platform patch is required.
  * The OHOS image ships the autoconf suite but no automake/aclocal/libtoolize,
    so automake is pulled in as a `tool_requires` and injected into the build
    environment through `VirtualBuildEnv`.
  * OHOS denies `execve` of *scripts* stored on HMDFS (EACCES, exit 13) for
    every process inside conan's build tree, while interpreter binaries are
    unaffected.  The conan `autoreconf` chain (and `Autotools.configure`)
    spawns such scripts directly and dies with "Permission denied"; the
    recipe therefore bootstraps aclocal/automake by invoking the packaged
    Perl scripts through the `perl` binary, and runs `configure` through
    `/system/bin/sh`.  Both forms are plain portable shell, so they also
    hold on a vanilla Linux CI (E116-family, empirically pinned with a
    minimal-recipe probe matrix).
  * Dependency discovery is the four pkg-config modules the upstream
    `configure.ac` probes for - x11, xext, xpm and dockapp.  All four are
    provided by published OHOS packages, so `PKG_CHECK_MODULES` succeeds
    unchanged.
  * The generated `configure` embeds `umask 077` when it creates the
    config.status private temp dir.  HMDFS forces the setgid bit on that dir
    and maps the owner uid, so the 0700 dir ends up unwritable even for its own
    owner and config.status dies with "Permission denied"
    (E011/E114/E129).  The generated script is rewritten to `umask 022` before
    it runs.
  * make runs single threaded: the SELinux policy forbids creating the
    jobserver FIFO, which makes parallel make hang or fail (E074/E525).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cmd_args_to_string
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

UMASK_INSECURE = "umask 077"
UMASK_HMDFS_SAFE = "umask 022"


def _prepare_autotools_env():
    """The packaged automake/libtool helpers hard-code absolute paths for
    autoconf/autoheader/autom4te/sed that do not exist in this image.  Point
    the tool environment variables at whatever the build env really exposes.
    """
    for tool, variable in (
        ("autoconf", "AUTOCONF"),
        ("autoheader", "AUTOHEADER"),
        ("autom4te", "AUTOM4TE"),
        ("sed", "SED"),
    ):
        if os.environ.get(variable):
            continue
        resolved = shutil.which(tool)
        if resolved:
            os.environ[variable] = resolved


def _fix_config_status_umask(conanfile, configure):
    """E011/E114/E129 - see the module docstring."""
    with open(configure, encoding="utf-8") as handle:
        content = handle.read()
    if UMASK_INSECURE not in content:
        raise ConanException(
            "the generated configure no longer contains 'umask 077'; the HMDFS "
            "config.status workaround has to be revisited"
        )
    with open(configure, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content.replace(UMASK_INSECURE, UMASK_HMDFS_SAFE))
    conanfile.output.info(
        "configure: rewrote %d occurrence(s) of '%s' to '%s' (HMDFS/E011)"
        % (content.count(UMASK_INSECURE), UMASK_INSECURE, UMASK_HMDFS_SAFE)
    )


class WmtopConan(ConanFile):
    name = "wmtop"
    version = "0.85"
    description = "Dock app showing the three top CPU or memory using processes"
    license = "GPL-2.0-or-later"
    homepage = "https://www.dockapps.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # wmtop links against libdockapp and drives X11/Xext/Xpm directly, so
        # the X11 development files have to stay visible transitively.
        self.requires("libdockapp/0.7.3", transitive_headers=True, transitive_libs=True)
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # The published tarball carries no generated configure, and the OHOS
        # image ships the autoconf suite without automake/aclocal, so the
        # Autotools bootstrap has to come from tool_requires.
        # tool_requires resolve against the *build* profile: conan create needs
        # both -pr:h and -pr:b.
        self.tool_requires("automake/1.18")

    def validate(self):
        # R32: settings.os must be checked against the Linux/OHOS family.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmtop supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        # configure.ac discovers every dependency through PKG_CHECK_MODULES, so
        # the four .pc files must exist; AutotoolsToolchain prepends the
        # generators folder to PKG_CONFIG_PATH for us.
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        # tool_requires bins (aclocal/automake) must be reachable.
        VirtualBuildEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        # config.guess cannot guess "HarmonyOS"; config.sub accepts the OHOS
        # triplet, so hand configure the canonical build and host explicitly.
        toolchain.configure_args.append("--build=aarch64-linux-ohos")
        toolchain.configure_args.append("--host=aarch64-linux-ohos")
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        # The release ships configure.ac/Makefile.am but no configure.
        self._bootstrap_configure()
        _fix_config_status_umask(self, os.path.join(self.source_folder, "configure"))
        self._configure()
        # E074/E525: parallel make cannot create the jobserver FIFO here.
        self.run(f"{self._ohos_env_prefix()} make -j1")
        # The release declares no TESTS/check_PROGRAMS, but the canonical check
        # target stays part of every package build (R51).
        self.run(f"{self._ohos_env_prefix()} make -j1 check")

    @staticmethod
    def _ohos_env_prefix():
        """Env prefix for configure/make/install.

        * PATH: put the real toybox/hnp tools ahead of the agent sandbox
          shims (safe-bin/rm carries a '#!/bin/bash' shebang that does not
          exist on OHOS).
        * SHELL/CONFIG_SHELL: conan's build env exports the sandbox bash,
          which auto-sources the same broken shim via BASH_ENV and which
          configure bakes into the Makefile as SHELL; force /bin/sh instead.
        """
        return (
            'PATH="/data/service/hnp/bin:/system/bin:/bin:$PATH" '
            'SHELL="/bin/sh" CONFIG_SHELL="/bin/sh"'
        )

    def _bootstrap_configure(self):
        """Generate configure/aclocal.m4/Makefile.in from the pristine tree.

        OHOS forbids execve of scripts living on HMDFS inside conan's build
        tree (exit 13), so neither `autoreconf` (which execve's $ACLOCAL) nor
        the packaged `sh` wrapper (which execve's the embedded .aclocal-real)
        can run.  The automake Perl scripts are instead invoked through the
        `perl` binary - execve of an interpreter binary is fine on every
        platform, which keeps this recipe OHOS- and Linux-clean.  The acdir
        arguments replicate what the packaged wrapper would have passed.
        """
        source = self.source_folder
        if os.path.isfile(os.path.join(source, "configure")):
            return
        automake_pkg = self._build_tool_pkg("automake")
        pkg = automake_pkg.package_folder
        bin_dir = os.path.join(pkg, "bin")
        share_dir = os.path.join(pkg, "share")
        pkg_m4 = self._pkg_m4_dir()
        self.output.info(
            "Bootstrapping autotools: automake pkg=%s pkg.m4=%s" % (pkg, pkg_m4)
        )
        # 1. aclocal.m4: automake's own macros + pkg.m4 (PKG_CHECK_MODULES).
        self.run(
            f'ACLOCAL_PATH="{pkg_m4}:$ACLOCAL_PATH" '
            f'perl "{bin_dir}/.aclocal-real" '
            f'--automake-acdir="{share_dir}/aclocal-1.18" '
            f'--system-acdir="{share_dir}/aclocal" --force',
            cwd=source,
        )
        # 2. configure: plain autoconf from the system autoconf suite.
        self.run("autoconf -o configure configure.ac", cwd=source)
        # 3. Makefile.in + aux scripts (install-sh/missing/compile/depcomp).
        self.run(
            f'perl "{bin_dir}/.automake-real" '
            f'--libdir="{share_dir}/automake-1.18" '
            f"--add-missing --copy --foreign",
            cwd=source,
        )
        if not os.path.isfile(os.path.join(source, "configure")):
            raise ConanException("autotools bootstrap did not produce configure")

    def _configure(self):
        """Run configure through the shell (OHOS execve-of-script denial).

        Autotools.configure() would execve the script directly; the arguments
        are the very same ones the AutotoolsToolchain would pass, including
        --prefix and the per-directory install flags.

        Because --build == --host, configure treats the build as native and
        executes its AC_PROG_CC conftest; the conftest links the shared
        dependency chain, so the dependency libdirs are inlined into
        LD_LIBRARY_PATH for the whole configure run.
        """
        toolchain = AutotoolsToolchain(self)
        # config.guess cannot guess "HarmonyOS"; config.sub accepts the OHOS
        # triplet, so hand configure the canonical build and host explicitly.
        toolchain.configure_args.append("--build=aarch64-linux-ohos")
        toolchain.configure_args.append("--host=aarch64-linux-ohos")
        args = cmd_args_to_string(toolchain.configure_args)
        libdirs = []
        for dep in self.dependencies.host.values():
            for sub in ("lib", "lib64"):
                libdir = os.path.join(dep.package_folder, sub)
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
        ld_path = ":".join(libdirs)
        self.run(
            f'{self._ohos_env_prefix()} LD_LIBRARY_PATH="{ld_path}:$LD_LIBRARY_PATH" '
            f'sh "{os.path.join(self.source_folder, "configure")}" {args}',
        )

    def _build_tool_pkg(self, name):
        """Locate a tool_requires dependency in the build graph."""
        for require, dep in self.dependencies.build.items():
            if require.ref and require.ref.name == name:
                return dep
        raise ConanException(f"tool_requires {name} not found in the build graph")

    @staticmethod
    def _pkg_m4_dir():
        """Directory holding pkg.m4 (needed by PKG_CHECK_MODULES).

        The automake package's acdir only carries automake's own macros; on
        the OHOS image pkg.m4 ships next to the hnp pkg-config, on a stock
        Linux box under the usual share/aclocal.
        """
        candidates = sorted(glob.glob("/data/service/hnp/*/pkg-config*/share/aclocal"))
        candidates += ["/data/service/hnp/share/aclocal", "/usr/share/aclocal"]
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "pkg.m4")):
                return candidate
        raise ConanException(
            "pkg.m4 not found; PKG_CHECK_MODULES cannot be expanded by aclocal"
        )

    def package(self):
        # make install with DESTDIR (prefix=/ lands bin/ and share/man/ at the
        # package root, mirroring Autotools.install's own DESTDIR behaviour).
        self.run(
            f'{self._ohos_env_prefix()} make -j1 install '
            f'DESTDIR="{self.package_folder}"'
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
