#!/usr/bin/env python3
"""Conan recipe for rmw 0.9.5.

rmw (ReMove to Waste) is a command-line trashcan/recycle-bin utility written
in C and built with Meson.  It installs a single executable plus docs; the
internal static libraries (librmw, libbsdutilsrm) are not part of the public
API, so the package type is "application".

OHOS notes:
- canfigger: patch 0001 replaces the pkg-config dependency() (and its
  wrap-git fallback, which needs GitHub access) with
  cc.find_library('canfigger') against the conan package libdir.
- ncurses: patch 0002 resolves curses/menu via
  cc.find_library('ncursesw'/'menuw') because the OHOS ncurses package
  exports only ncursesw.pc (no curses.pc/menuw.pc usable on this host).
- fts(3): musl/OHOS has no fts_open and no libfts, and the bundled bsdutils
  rm_tree() hard-requires it.  The recipe vendors the musl-fts 1.2.7
  implementation (NetBSD code, BSD-3-Clause) as fts.c/fts.h, copies both into
  src/bsdutils/ before building, and patch 0003 compiles fts.c into the
  bsdutilsrm static library (source files must be textual patches).
- gettext/NLS: musl has no libintl; upstream's src/gettext.h already provides
  an inline fallback when ENABLE_NLS is undefined, so meson option nls=false
  needs no source change.
- btrfs clone support is only probed when host_machine.system() == 'linux';
  meson on OHOS reports 'harmonyos', so want_btrfs_clone is disabled
  explicitly for determinism.  (This also keeps test_btrfs_clone.sh
  unregistered, giving exactly 7 upstream tests.)
- Upstream tests are built and REALLY RUN via 'meson test' during build():
  3 C unit tests (test_strings_rmw, test_utils, test_restore) plus 4 shell
  workflow scripts.  Patches 0004-0007 are platform-only test adjustments:
  * 0004 src/utils.c: the OHOS SELinux policy denies symlink(2)/lstat() on
    symlinks to untrusted (unsigned) processes, so the symlink assertions
    probe the capability and skip gracefully when denied;
  * 0005/0006 shell tests: toybox id(1) fails ("bad uid") for the OHOS
    multi-user uid space (20020170), so $(id -u) becomes $(stat -c %u .),
    and the media-root test prefers the writable user-storage tmpfs mount
    over the read-only erofs /tmp;
  * 0007 test_restore.sh: the symlink move/restore section is probed the
    same way as 0004 and skipped when the platform denies symlink handling.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class RmwConan(ConanFile):
    name = "rmw"
    version = "0.9.5"
    description = (
        "Command-line trashcan / recycle-bin utility: moves and restores "
        "files to and from configured waste directories (FreeDesktop.org "
        "Trash spec support)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/theimpossibleastronaut/rmw"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "without_curses": [True, False],
    }
    default_options = {
        "without_curses": False,
    }

    def export_sources(self):
        export_conandata_patches(self)
        # Vendored fts(3) (musl-fts 1.2.7, BSD-3-Clause) travels with the
        # recipe; export() copies the whole recipe folder, but be explicit so
        # the dependency of build() is obvious.
        for name in ("fts.c", "fts.h", "COPYING"):
            copy(
                self,
                name,
                src=os.path.join(self.recipe_folder, "vendored"),
                dst=os.path.join(self.export_sources_folder, "vendored"),
                keep_path=False,
            )

    def requirements(self):
        # canfigger >= 0.3.0 (config parsing) and ncurses (wide-char curses +
        # menu for the interactive restore UI) are both already adapted for
        # OHOS aarch64 in this repository.
        self.requires("canfigger/0.3.2")
        self.requires("ncurses/6.6")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rmw requires a POSIX-like target (Linux or OHOS), "
                f"not {self.settings.os}"
            )

    def build_requirements(self):
        # ohpcd prebuilt Meson tool package (1.11.0.1 has no prebuilt binary).
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["without-curses"] = (
            "true" if bool(self.options.without_curses) else "false"
        )
        tc.project_options["nls"] = "false"
        tc.project_options["want_btrfs_clone"] = "false"
        tc.project_options["build_tests"] = "true"
        tc.project_options["install_shell_completions"] = "false"
        # The meson.build patches resolve curses/menu/canfigger through
        # cc.find_library() (pkg-config is unreliable on this host: the
        # ncurses package ships prefix=/ .pc files and PkgConfigDeps is not
        # used), so make every dependency include/lib dir visible to both
        # the header probes and the linker.
        for dep in self.dependencies.host.values():
            for incdir in (dep.cpp_info.includedirs or []):
                if incdir:
                    if not os.path.isabs(incdir):
                        incdir = os.path.join(dep.package_folder, incdir)
                    tc.c_args.append(f"-I{incdir}")
            for libdir in (dep.cpp_info.libdirs or []):
                if libdir:
                    if not os.path.isabs(libdir):
                        libdir = os.path.join(dep.package_folder, libdir)
                    tc.c_link_args.append(f"-L{libdir}")
        tc.generate()

        self._inject_archive_tools()

    def build(self):
        # Drop the vendored fts(3) into src/bsdutils/ before configuring.
        bsdutils_dir = os.path.join(self.source_folder, "src", "bsdutils")
        for name in ("fts.c", "fts.h"):
            copy(
                self,
                name,
                src=os.path.join(self.export_sources_folder, "vendored"),
                dst=bsdutils_dir,
                keep_path=False,
            )
        copy(
            self,
            "COPYING",
            src=os.path.join(self.export_sources_folder, "vendored"),
            dst=os.path.join(self.source_folder, "licenses", "fts"),
            keep_path=False,
        )
        # musl-fts ships an autotools config.h include; provide the minimal
        # set of probes for musl (dirfd() exists; no d_namlen in musl dirent).
        with open(os.path.join(bsdutils_dir, "config.h"), "w",
                  encoding="utf-8") as handle:
            handle.write("/* minimal config.h for vendored musl-fts 1.2.7 */\n"
                         "#define HAVE_DIRFD 1\n")
        apply_conandata_patches(self)
        meson = Meson(self)
        with self._meson_environment().vars(self).apply():
            meson.configure()
            # -j1: device-default serial build (jobserver noise on this
            # device shows up with higher parallelism).
            self.run(f'meson compile -C "{self.build_folder}" -j1')
            # Really run the upstream test suite (3 C unit tests + 4 shell
            # workflow scripts; test_btrfs_clone.sh stays unregistered on
            # OHOS).  Any failure aborts the build.
            self.run(
                f'meson test -C "{self.build_folder}" '
                f'--timeout 180 --print-errorlogs'
            )

    def package(self):
        with self._meson_environment().vars(self).apply():
            Meson(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    def _meson_environment(self):
        """Conan-scoped environment for Meson (compiler dir on PATH)."""
        environment = Environment()
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        if bindir and os.path.isdir(bindir):
            environment.prepend_path("PATH", bindir)
        # The shell tests invoke the just-built rmw binary, which dynamically
        # links the conan canfigger/ncurses libraries; meson test does not
        # know about conan's runtime environment, so provide it here.
        for dep in self.dependencies.host.values():
            for libdir in (dep.cpp_info.libdirs or []):
                if libdir:
                    if not os.path.isabs(libdir):
                        libdir = os.path.join(dep.package_folder, libdir)
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _inject_archive_tools(self):
        """Add llvm-ar/llvm-ranlib when the profile omits Meson's names."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        ar = executables.get("ar") or (
            os.path.join(bindir, "llvm-ar") if bindir else ""
        )
        ranlib = executables.get("ranlib") or (
            os.path.join(bindir, "llvm-ranlib") if bindir else ""
        )

        for filename in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not ar or not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content or "\nar =" in content:
                continue
            insertion = "[binaries]\nar = %r\n" % ar
            if ranlib:
                insertion += "ranlib = %r\n" % ranlib
            content = content.replace("[binaries]\n", insertion, 1)
            with open(machine_file, "w", encoding="utf-8") as handle:
                handle.write(content)
