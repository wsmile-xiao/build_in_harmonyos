#!/usr/bin/env python3
"""Conan recipe for kcemu 0.5.2 - the KC85/CCS computer emulator.

KCemu is an autotools C++ project whose configure unconditionally requires the
GTK+2 frontend.  The full GTK stack is not available for OHOS here, so the
recipe provides a stub ``gtk+-2.0.pc`` (pointing at glib, which KCemu's GUI-
independent parts do need) so configure succeeds, and builds the non-GUI parts:
the preference/debug/sys convenience libraries, the CLI tools and the single
upstream test program that runs without cppunit (``t_prefs``).

``z80ex`` (a hard requirement, not available as a Conan package) is built from
its Debian source into a local prefix.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, get, save, unzip)
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.0"

Z80EX_URL = "https://deb.debian.org/debian/pool/main/z/z80ex/z80ex_1.1.21.orig.tar.gz"
Z80EX_SHA256 = "6f5e521d068a614b41e10180ad4ae45b1bc258ec28c962543feb9078856c2530"

DISABLE_CODECS = [
    "libaudiofile", "libsndfile", "libflac", "libvorbis", "libtheora",
    "libxvidcore", "libdirac", "libschroedinger", "libavformat", "libgif",
    "libvncserver", "libmp3lame",
]

# CLI tools (no GUI), as (directory, targets).
TOOLS = (
    ("src/fileio", ("kc2img", "kc2tap", "kc2wav", "kc2raw")),
    ("src/libdisk", ("tdtodump",)),
    ("src/libtape", ("kctape",)),
)


class KcemuConan(ConanFile):
    name = "kcemu"
    version = "0.5.2"
    description = "KC85/CCS (and related) computer emulator - CLI tools and core libraries"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/redcode/kc85_emu"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kcemu OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        # The OHOS image (device and CI sandbox) ships autoconf but no
        # automake/aclocal/libtoolize, so pull them in as tool_requires (same
        # approach as archives/l/libhbaapi).  The Conan perl their scripts use
        # clashes with the interpreter here, so _autotools_env() shims them.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    # Autotools (autoreconf/automake/autoconf/pkg-config/gettext) come from the
    # device's harmonybrew toolchain: the Conan perl package used by the Conan
    # autoconf/automake recipes cannot load its own XS modules here.

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        download(self, Z80EX_URL, "z80ex-1.1.21.tar.gz", sha256=Z80EX_SHA256)
        unzip(self, "z80ex-1.1.21.tar.gz", destination="z80ex", strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        # Stub gtk+-2.0 so configure's unguarded PKG_CHECK_MODULES passes; it
        # simply exposes glib, which the non-GUI code needs anyway.
        glib = self.dependencies["glib"].cpp_info
        glib_pkg = self.dependencies["glib"].package_folder
        glib_incs = list(glib.includedirs)
        for extra in (os.path.join(glib_pkg, "include", "glib-2.0"),
                      os.path.join(glib_pkg, "lib", "glib-2.0", "include")):
            if os.path.isdir(extra) and extra not in glib_incs:
                glib_incs.append(extra)
        cflags = " ".join('-I"{}"'.format(i) for i in glib_incs)
        dep_libs = list(glib.libs)
        if "glib-2.0" not in dep_libs:
            dep_libs.append("glib-2.0")
        libs = (" ".join('-L"{}"'.format(l) for l in glib.libdirs) + " " +
                " ".join("-l" + x for x in dep_libs))
        self._glib_incs = glib_incs
        save(self, os.path.join(self.generators_folder, "gtk+-2.0.pc"),
             'Name: gtk+-2.0\nDescription: OHOS stub exposing glib\n'
             'Version: 2.24.33\nRequires:\nCflags: {}\nLibs: {}\n'.format(
                 cflags, libs))

    def _tool_package(self, name):
        for accessor in (lambda: self.dependencies[name],
                         lambda: self.dependencies.build[name],
                         lambda: self.dependencies.test[name]):
            try:
                return accessor()
            except Exception:
                continue
        return None

    def _autotools_env(self):
        """Shim the automake perl scripts through an available perl.

        The published automake package ships ``aclocal``/``automake`` whose
        shebang points at the CI image perl; on machines without it the scripts
        cannot start, and its XS modules clash with the local perl.  Re-exec the
        real scripts through ``perl`` found on PATH and expose them via
        ``$ACLOCAL``/``$AUTOMAKE`` (same fix as archives/l/libhbaapi).
        """
        overrides = {}
        for tool, variable in (("autoconf", "AUTOCONF"),
                               ("autoheader", "AUTOHEADER"),
                               ("autom4te", "AUTOM4TE"),
                               ("sed", "SED")):
            if os.environ.get(variable):
                continue
            located = shutil.which(tool)
            if located:
                os.environ[variable] = located
        perl = shutil.which("perl")
        automake = self._tool_package("automake")
        if not perl or automake is None or not automake.package_folder:
            return overrides
        bindir = os.path.join(automake.package_folder, "bin")
        sharedir = os.path.join(automake.package_folder, "share")
        shim_dir = os.path.join(self.build_folder, ".autotools-shims")
        os.makedirs(shim_dir, exist_ok=True)
        acdir_args = ["--automake-acdir=" + os.path.join(sharedir, "aclocal-1.18"),
                      "--system-acdir=" + os.path.join(sharedir, "aclocal")]
        libdir_args = ["--libdir=" + os.path.join(sharedir, "automake-1.18")]
        shims = (("aclocal", ".aclocal-real", "ACLOCAL", acdir_args),
                 ("aclocal-1.18", ".aclocal-1.18-real", None, acdir_args),
                 ("automake", ".automake-real", "AUTOMAKE", libdir_args),
                 ("automake-1.18", ".automake-1.18-real", None, libdir_args))
        for name, real, variable, extra in shims:
            real_path = os.path.join(bindir, real)
            if not os.path.isfile(real_path):
                continue
            shim = os.path.join(shim_dir, name)
            with open(shim, "w", encoding="utf-8") as handle:
                handle.write('#!/bin/sh\nexec {} {} {} "$@"\n'.format(
                    shlex.quote(perl), shlex.quote(real_path),
                    " ".join(shlex.quote(item) for item in extra)))
            os.chmod(shim, 0o755)
            if variable:
                overrides[variable] = shim
        return overrides

    def _system_automake_dir(self):
        """Return a PATH entry holding a complete system automake suite.

        The device (harmonybrew) ships aclocal/automake/autoconf; the CI image
        does not.  Prefer the system suite when it exists so we never mix a
        Conan automake with a different autoconf; otherwise fall back to the
        Conan tool_requires + perl shims.
        """
        candidates = []
        for entry in os.environ.get("PATH", "").split(os.pathsep):
            if entry and ".conan2" not in entry.replace("\\", "/"):
                candidates.append(entry)
        home = os.environ.get("HOME") or os.path.expanduser("~")
        candidates.append(os.path.join(home, ".harmonybrew", "bin"))
        for entry in candidates:
            if (os.path.isfile(os.path.join(entry, "aclocal")) and
                    os.path.isfile(os.path.join(entry, "automake")) and
                    os.path.isfile(os.path.join(entry, "autoconf"))):
                return entry
        return None

    def _build_z80ex(self, cc, ar):
        srcdir = os.path.join(self.source_folder, "z80ex")
        if not os.path.isfile(os.path.join(srcdir, "z80ex.c")):
            srcdir = os.path.join(srcdir, "z80ex-1.1.21")
        prefix = os.path.join(self.source_folder, "_z80ex-install")
        os.makedirs(os.path.join(prefix, "lib"), exist_ok=True)
        os.makedirs(os.path.join(prefix, "include", "z80ex"), exist_ok=True)
        defs = ("-DWORDS_LITTLE_ENDIAN -DZ80EX_VERSION_STR=1.1.21 "
                "-DZ80EX_API_REVISION=1 -DZ80EX_VERSION_MAJOR=1 "
                "-DZ80EX_VERSION_MINOR=21 -DZ80EX_RELEASE_TYPE=")
        for src, obj, lib in (("z80ex.c", "z80ex.o", "libz80ex.a"),
                              ("z80ex_dasm.c", "z80ex_dasm.o", "libz80ex_dasm.a")):
            self.run('"{}" -O2 -fPIC -fno-common -std=gnu99 {} -I. -Iinclude '
                     '-c {} -o {}'.format(cc, defs, src, obj), cwd=srcdir)
            self.run('"{}" rcs "{}/lib/{}" {}'.format(ar, prefix, lib, obj),
                     cwd=srcdir)
        for h in ("z80ex.h", "z80ex_common.h", "z80ex_dasm.h"):
            copy(self, h, os.path.join(srcdir, "include"),
                 os.path.join(prefix, "include", "z80ex"))
        return prefix

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")
        bindir = os.path.dirname(cc)
        ar = os.path.join(bindir, "llvm-ar")

        z80ex = self._build_z80ex(cc, ar)

        # SDL is not used (--disable-sound) but configure.ac still expands
        # AM_PATH_SDL; provide a stub so autoconf does not fail.
        save(self, os.path.join(self.source_folder, "config", "m4", "sdl.m4"),
             "AC_DEFUN([AM_PATH_SDL], [:])\n")
        # The tree ships config/bootstrap (aclocal + autoheader + automake
        # --add-missing + autoconf).  Use it instead of `autoreconf --install`,
        # whose autopoint/gettext step forks heavily and is unnecessary with
        # --disable-nls (it also fails on this gettext-tools version).
        sysdir = self._system_automake_dir()
        if sysdir:
            env = ["PATH={}".format(sysdir + os.pathsep + os.environ.get("PATH", "")),
                   "ACLOCAL_PATH=", "PERL5LIB=", "PERL5OPT=", "ACLOCAL=", "AUTOMAKE="]
            self.run("sh config/bootstrap", cwd=self.source_folder, env=env)
        else:
            overrides = self._autotools_env()
            prefix = " ".join("{}={}".format(k, shlex.quote(v))
                              for k, v in overrides.items())
            self.run("{} sh config/bootstrap".format(prefix).strip(),
                     cwd=self.source_folder, env="conanbuild")
        # KB E011: HMDFS + autoconf's "umask 077" makes config.status's temp
        # meat dir unwritable; relax it to 022.
        self.run("sed -i 's/umask 077/umask 022/g' configure",
                 cwd=self.source_folder, env="conanbuild")

        depincs, deplibs = [], []
        for dep in self.dependencies.values():
            depincs.extend(dep.cpp_info.includedirs)
            deplibs.extend(dep.cpp_info.libdirs)
        depincs.extend(getattr(self, "_glib_incs", []))
        libdirs_list = list(dict.fromkeys(deplibs))
        depincs = " ".join('-I"{}"'.format(i) for i in dict.fromkeys(depincs))
        deplibs = " ".join('-L"{}"'.format(i) for i in libdirs_list)

        opts = ["--host=aarch64-linux-gnu", "--build=x86_64-pc-linux-gnu",
                "--with-debug-level=1", "--disable-sound", "--disable-nls"]
        opts += ["--disable-" + c for c in DISABLE_CODECS]
        env = ('PKG_CONFIG_PATH="{}:${{PKG_CONFIG_PATH:-}}" CC="{}" CXX="{}" '
               'CFLAGS="-O2 -fcommon -Wno-error" CXXFLAGS="-O2 -fcommon -std=gnu++14" '
               'CPPFLAGS="-I{}/include {}" LDFLAGS="-L{}/lib -Wl,-rpath,{}/lib {}" '
               'ac_cv_lib_z80ex_z80ex_create=yes'
               .format(self.generators_folder, cc, cxx, z80ex, depincs, z80ex,
                       z80ex, deplibs))
        self.run(env + " ./configure " + " ".join(opts),
                 cwd=self.source_folder, env="conanbuild")

        # Core convenience libraries (some tools depend on these).
        self.run("make -C src/sys/unix libsys_unix.a", cwd=self.source_folder, env="conanbuild")
        self.run("make -C src/libdbg libdbg.a", cwd=self.source_folder, env="conanbuild")
        self.run("make -C src/kc/prefs libprefs.a", cwd=self.source_folder, env="conanbuild")

        for directory, targets in TOOLS:
            self.run("make -C {} {}".format(directory, " ".join(targets)),
                     cwd=self.source_folder, env="conanbuild")

        # Upstream test (the only one built without cppunit).
        self.run("make -C test/kc/prefs t_prefs", cwd=self.source_folder, env="conanbuild")
        ld = ":".join([z80ex + "/lib"] + libdirs_list)
        self.run('LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}" ./test/kc/prefs/t_prefs'
                 .format(ld), cwd=self.source_folder, env="conanbuild")
        self.output.info("upstream t_prefs passed")

    def package(self):
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        for directory, targets in TOOLS:
            for tool in targets:
                copy(self, tool, os.path.join(self.source_folder, directory),
                     os.path.join(self.package_folder, "bin"))
        for lib, sub in (("libprefs.a", "src/kc/prefs"),
                         ("libdbg.a", "src/libdbg"),
                         ("libsys_unix.a", "src/sys/unix")):
            copy(self, lib, os.path.join(self.source_folder, sub),
                 os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["prefs", "dbg", "sys_unix"]
