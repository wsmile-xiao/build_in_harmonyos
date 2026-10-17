#!/usr/bin/env python3
"""Conan recipe for squashfs-tools-ng 1.3.2.

A new generation of SquashFS tools and library (libsquashfs).
Builds CLI tools (gensquashfs, rdsquashfs, sqfs2tar, tar2sqfs, sqfsdiff)
and the libsquashfs library with support for gzip, xz, lz4, zstd,
bzip2, and lzo compression.

Source: https://github.com/AgentD/squashfs-tools-ng (v1.3.2 tag)
Build: autoreconf -fi && configure && make && make check

HarmonyOS adaptations:
  - GitHub archive tarball lacks pre-generated configure; autoreconf -fi
    generates it using automake/libtool from tool_requires.
  - ACLOCAL_PATH includes libtool's and pkg-config's m4 macros for autoreconf.
  - PKG_CHECK_MODULES bypassed by pre-setting <dep>_CFLAGS/<dep>_LIBS env vars
    (conan deps don't ship .pc files).
  - mktemp wrapper forces autoconf AS_TMPDIR to use mkdir fallback (HMFS perms).
  - config.status ac_tmp directory umask 077 fixed to use writable tmpdir.
  - --disable-maintainer-mode prevents make from re-running autotools chain.
"""
import glob as _glob
import os
import shutil
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class SquashfsToolsNgConan(ConanFile):
    name = "squashfs-tools-ng"
    version = "1.3.2"
    description = "New generation SquashFS tools and libsquashfs library"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/AgentD/squashfs-tools-ng"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("xz/5.6.2")
        self.requires("lz4/1.10.0")
        # zstd/1.5.7.1 is the first registry version shipping libzstd.a.
        # The CLI tools must not get a NEEDED libzstd.so.1 entry: they are
        # registered in commands.json and executed outside conanrun env
        # (L2 platform smoke test failed with exit 127 on 1.5.6, which
        # ships only shared libs).
        self.requires("zstd/1.5.7.1")
        self.requires("bzip2/1.0.8")
        self.requires("lzo2/2.10")
        self.requires("readline/8.3")
        self.requires("ncurses/6.6")  # readline terminfo dependency (tgetstr, tgetflag, etc.)

    def build_requirements(self):
        # GitHub archive tarball lacks pre-generated configure.
        # autoreconf needs automake (aclocal) and libtool (libtoolize);
        # CI worker lacks these system tools (E178), inject via conan.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "squashfs-tools-ng is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with broken perms (HMFS MAC),
        # causing autoconf's config.status to fail. Create a mktemp wrapper
        # that fails so autoconf AS_TMPDIR uses its mkdir fallback.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            "#!/bin/sh\n"
            "# HarmonyOS: mktemp -d creates dirs with broken perms (HMFS MAC).\n"
            "# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n"
            "exit 1\n"
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # config.guess cannot detect HarmonyOS; pass --build explicitly.
        # Derive from settings.arch so native Linux x86_64 builds are not
        # misdetected as cross compiles.
        arch = "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
        tc.configure_args.append(f"--build={arch}-unknown-linux-gnu")
        # Disable maintainer mode to prevent make from re-running autotools
        # (which would overwrite the configure umask fix).
        tc.configure_args.append("--disable-maintainer-mode")
        # Disable shared library building: conan deps are static (no -fPIC),
        # and squashfs-tools-ng package_type is "application" (CLI tools only).
        # Building shared libs would fail linking static deps without -fPIC.
        tc.configure_args.append("--disable-shared")

        # Inject dependency include/lib paths for compilation and linking.
        # zstd libdirs are skipped here on purpose: they also contain
        # libzstd.so, and the linker searches -L paths in order — the
        # private static-only dir below must be the only place -lzstd
        # can resolve from, otherwise the tools get NEEDED libzstd.so.1.
        dep_names = ["zlib", "xz", "lz4", "zstd", "bzip2", "lzo2", "readline", "ncurses"]
        for dep_name in dep_names:
            dep = self.dependencies[dep_name]
            for incdir in dep.cpp_info.includedirs:
                tc.extra_cflags.append(f"-I{incdir}")
            if dep_name != "zstd":
                for libdir in dep.cpp_info.libdirs:
                    tc.extra_ldflags.append(f"-L{libdir}")

        tc.generate()

        # Set up environment for autoreconf and configure
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))

        # zstd (and any future shared-library deps) live in the conan cache;
        # make check binaries need to find libzstd.so.1 at runtime. Static
        # lib dirs in LD_LIBRARY_PATH are harmless, so inject them all.
        for dep_name in dep_names:
            dep = self.dependencies[dep_name]
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)

        # ACLOCAL_PATH for autoreconf:
        # libtool provides libtool.m4 (LT_INIT), automake provides automake m4s,
        # pkg-config provides pkg.m4 (PKG_PROG_PKG_CONFIG macro).
        libtool_dep = self.dependencies.build["libtool"]
        libtool_aclocal = os.path.join(
            libtool_dep.package_folder, "share", "aclocal")
        automake_dep = self.dependencies.build["automake"]
        automake_aclocal = os.path.join(
            automake_dep.package_folder, "share", "aclocal")

        # pkg.m4: probe via pkg-config on PATH first (survives hnp layout
        # upgrades), fall back to the known hnp install location.
        aclocal_paths = []
        for p in [libtool_aclocal, automake_aclocal]:
            if os.path.isdir(p):
                aclocal_paths.append(p)
        pkg_config_bin = shutil.which("pkg-config")
        if pkg_config_bin:
            hnp_root = os.path.dirname(os.path.dirname(pkg_config_bin))
            for cand in _glob.glob(os.path.join(
                    hnp_root, "pkg-config.org", "pkg-config_*", "share", "aclocal")):
                if os.path.isdir(cand):
                    aclocal_paths.append(cand)
        pkg_aclocal = (
            "/data/service/hnp/pkg-config.org/"
            "pkg-config_0.29.2/share/aclocal"
        )
        if os.path.isdir(pkg_aclocal):
            aclocal_paths.append(pkg_aclocal)
        if aclocal_paths:
            env.define("ACLOCAL_PATH", ":".join(aclocal_paths))

        # Pre-set CFLAGS/LIBS for each dependency to bypass pkg-config.
        # PKG_CHECK_MODULES uses pre-set CFLAGS/LIBS if available, skipping
        # the pkg-config call entirely. Conan deps don't ship .pc files,
        # so this is required for configure to detect all compressors.
        pkg_config_deps = {
            "zlib": ("ZLIB", ["z"]),
            "xz": ("XZ", ["lzma"]),
            "lz4": ("LZ4", ["lz4"]),
            "readline": ("READLINE", ["readline", "ncursesw"]),
        }
        for dep_name, (env_prefix, lib_names) in pkg_config_deps.items():
            dep = self.dependencies[dep_name]
            cflags = " ".join(f"-I{d}" for d in dep.cpp_info.includedirs)
            libs = " ".join(f"-L{d}" for d in dep.cpp_info.libdirs)
            for lib_name in lib_names:
                libs += f" -l{lib_name}"
            env.define(f"{env_prefix}_CFLAGS", cflags)
            env.define(f"{env_prefix}_LIBS", libs)

        # zstd: link statically so the CLI tools never gain a NEEDED
        # libzstd.so.1 entry (they must run outside conanrun env; see
        # requirements() note). Two pitfalls ruled out:
        #  - passing the .a path directly makes libtool nest the archive
        #    into libsquashfs.a ("neither ET_REL" from ld.lld);
        #  - "-Wl,-Bstatic ... -Wl,-Bdynamic" is reordered by libtool (all
        #    -Wl flags are hoisted before -L/-l), turning the pair into a
        #    no-op and silently linking libzstd.so.
        # So: copy libzstd.a into a private dir that contains no .so and
        # point -L only there.
        zstd_dep = self.dependencies["zstd"]
        zstd_static_dir = os.path.join(self.build_folder, "zstd_static")
        os.makedirs(zstd_static_dir, exist_ok=True)
        zstd_static_copied = False
        for libdir in zstd_dep.cpp_info.libdirs:
            src = os.path.join(libdir, "libzstd.a")
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(zstd_static_dir, "libzstd.a"))
                zstd_static_copied = True
                break
        if not zstd_static_copied:
            raise ConanInvalidConfiguration(
                "zstd dependency has no libzstd.a — use zstd/1.5.7.1 or "
                "newer (first registry version shipping the static archive). "
                "Required so the tools do not depend on libzstd.so.1"
            )
        env.define(
            "ZSTD_CFLAGS",
            " ".join(f"-I{d}" for d in zstd_dep.cpp_info.includedirs),
        )
        env.define("ZSTD_LIBS", f"-L{zstd_static_dir} -lzstd")

        # Add ncurses lib directory to READLINE_LIBS so linker finds libncursesw.a
        ncurses_dep = self.dependencies["ncurses"]
        for libdir in ncurses_dep.cpp_info.libdirs:
            env.append("READLINE_LIBS", f"-L{libdir}")

        # bzip2 and lzo2 use AC_CHECK_LIB (not PKG_CHECK_MODULES).
        # Setting BZIP2_LIBS/LZO_LIBS bypasses the AC_CHECK_LIB test.
        bzip2_dep = self.dependencies["bzip2"]
        env.define(
            "BZIP2_CFLAGS",
            " ".join(f"-I{d}" for d in bzip2_dep.cpp_info.includedirs),
        )
        env.define(
            "BZIP2_LIBS",
            " ".join(f"-L{d}" for d in bzip2_dep.cpp_info.libdirs) + " -lbz2",
        )

        lzo_dep = self.dependencies["lzo2"]
        env.define(
            "LZO_CFLAGS",
            " ".join(f"-I{d}" for d in lzo_dep.cpp_info.includedirs),
        )
        env.define(
            "LZO_LIBS",
            " ".join(f"-L{d}" for d in lzo_dep.cpp_info.libdirs) + " -llzo2",
        )

        env.vars(self).save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        env = ["conanbuild", "hmos_env"]

        # GitHub archive tarball does not include configure — generate it.
        self.run("autoreconf -fi", cwd=self.source_folder, env=env)

        autotools = Autotools(self)
        autotools.configure()
        # Fix config.status umask issue (HMFS: umask 077 creates inaccessible
        # temp dirs for config.status's ac_tmp mechanism).
        self._fix_config_status()
        autotools.make(args=["-j1"])

        # L1: Run upstream test suite (make check) — R51: failures propagate
        # honestly. All 67 upstream tests must pass for the recipe to build.
        autotools.make(target="check")

    def _fix_config_status(self):
        """Fix config.status ac_tmp directory permission issue on OHOS/HMFS.

        autoconf's config.status creates temp dirs with
        'umask 077 && mktemp -d "./confXXXXXX"', which on HMFS creates
        directories inaccessible to the build process. Replace with a
        fixed writable temp directory (same approach as bitcoin/gnupg).
        """
        for cs_path in [
            os.path.join(self.build_folder, "config.status"),
            os.path.join(self.source_folder, "config.status"),
        ]:
            if not os.path.isfile(cs_path):
                continue
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            abs_tmp = os.path.join(tmpdir, "conf$$")
            s = open(cs_path, encoding="latin-1").read()
            s2 = s.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                f"tmp={abs_tmp}",
            )
            s2 = s2.replace(
                '(umask 077 && mkdir "$tmp")',
                'mkdir -p "$tmp" 2>/dev/null || mkdir "$tmp"',
            )
            if s2 != s:
                open(cs_path, "w", encoding="latin-1").write(s2)
                self.output.info("config.status ac_tmp fixed (dynamic tmpdir)")
                self.run(
                    f"sh {cs_path}",
                    cwd=os.path.dirname(cs_path),
                    env=["conanbuild", "hmos_env"],
                )
            break

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libsquashfs library (built static via --disable-shared); tools in bin/
        self.cpp_info.libs = ["squashfs"]
        self.cpp_info.bindirs = ["bin"]
