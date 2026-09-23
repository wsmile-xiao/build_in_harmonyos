#!/usr/bin/env python3
"""Conan recipe — libuio 0.3.0 (Userspace I/O helper library + lsuio/readuio).

libuio enumerates and accesses Linux UIO (Userspace I/O) devices through
sysfs (/sys/class/uio) and /dev/uio*. The package builds the shared/static
libuio library plus the two upstream CLI tools lsuio and readuio.

Adaptation notes (details in notes.md):
* The GitHub tag archive ships no generated configure script; build()
  bootstraps with autogen.sh (autoreconf). autoconf/m4 come from the SDK
  (avahi / accel-config precedent); automake and libtool come from Conan
  tool_requires.
* argp is a glibc extension absent from OHOS musl — patch 0001 switches the
  CLI tools to getopt_long and drops the configure check.
* gettext i18n and texinfo docs are stripped (patches 0002/0003): OHOS has
  no libintl runtime and the cross toolchain has neither autopoint nor
  makeinfo.
* Optional glib-2.0 support is disabled (--without-glib): the library has
  built-in no-glib fallbacks, keeping the dependency closure empty.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibuioConan(ConanFile):
    name = "libuio"
    version = "0.3.0"
    description = "Userspace I/O (UIO) helper library for Linux: enumerate and access UIO devices via sysfs and /dev/uio*"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/missinglinkelectronics/libuio"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # UIO is a Linux kernel interface; R32: platform checks use the tuple.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def build_requirements(self):
        # The GitHub tag archive has no generated configure; autogen.sh runs
        # autoreconf and needs libtoolize + aclocal. autoconf and m4 are
        # provided by the SDK (/data/service/hnp/bin), see avahi recipe.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-glib")
        # Upstream defaults to building with -Werror; clang -Wextra on this
        # 2011-era code warns, so keep warnings non-fatal.
        tc.configure_args.append("--without-werror")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Upstream config.guess/config.sub (2009) does not recognise
        # HarmonyOS or linux-ohos.  Use the generic linux-gnu triplet
        # (celt / libx11 precedent); libuio is plain POSIX C.
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()
        # Save configure args for build() to use when running configure
        # under bash on OHOS (see build()).
        args_file = os.path.join(self.build_folder, "conan", "configure_args.txt")
        os.makedirs(os.path.dirname(args_file), exist_ok=True)
        with open(args_file, "w", encoding="utf-8") as f:
            f.write(" ".join(tc.configure_args))

    def _ohos_autogen_env(self):
        """Env overrides so autoreconf can drive the conan automake/libtool
        packages on OHOS: user storage (HMDFS) refuses to exec #! scripts,
        so the packages' shims (bin/aclocal, bin/automake) and their
        .aclocal-real/.automake-real perl scripts in the conan cache cannot
        be executed directly.  autoreconf honours $ACLOCAL/$AUTOMAKE/
        $LIBTOOLIZE overrides, so drive the scripts through their
        interpreters, replicating the relocation flags the shims pass.
        The SDK's autoconf/autoheader/autom4te (on /data) exec directly.
        Returns a dict for inline command-line assignment, which reaches
        the subprocess regardless of Conan's conanbuild env plumbing.
        """
        perl = shutil.which("perl") or "/data/service/hnp/bin/perl"
        am = self.dependencies.build["automake"].package_folder
        libdir = None
        for entry in sorted(glob.glob(os.path.join(am, "share", "automake-*"))):
            if os.path.isdir(entry):
                libdir = entry
                break
        if not libdir:
            self.output.warning(
                f"automake package lacks share/automake-*: {am}; "
                "falling back to plain autogen.sh")
            return {}
        aclocal_ver = os.path.basename(libdir).replace("automake-", "")
        aclocal_cmd = (
            f"{perl} -I{libdir} "
            f"{os.path.join(am, 'bin', '.aclocal-real')} "
            f"--automake-acdir={os.path.join(am, 'share', 'aclocal-' + aclocal_ver)} "
            f"--system-acdir={os.path.join(am, 'share', 'aclocal')}"
        )
        automake_cmd = (
            f"{perl} -I{libdir} "
            f"{os.path.join(am, 'bin', '.automake-real')} "
            f"--libdir={libdir}"
        )
        # The published libtool/2.5.4 binary drives libtoolize through
        # $_lt_pkgdatadir (exported by the conanbuild env as
        # share/libtool-conan), but that directory is empty in the package
        # and share/libtool lacks the m4/ subdir libtoolize expects under
        # it.  Assemble a complete libtoolize data dir in the build folder
        # (plain file copies work on HMDFS) and override the env var.
        lt = self.dependencies.build["libtool"].package_folder
        ltdata = os.path.join(self.build_folder, "ltdata")
        os.makedirs(os.path.join(ltdata, "build-aux"), exist_ok=True)
        os.makedirs(os.path.join(ltdata, "m4"), exist_ok=True)
        copy(self, "*", os.path.join(lt, "share", "libtool", "build-aux"),
             os.path.join(ltdata, "build-aux"))
        copy(self, "*.m4", os.path.join(lt, "share", "aclocal"),
             os.path.join(ltdata, "m4"))
        ltdl_dst = os.path.join(ltdata, "libltdl")
        os.makedirs(ltdl_dst, exist_ok=True)
        copy(self, "*", os.path.join(lt, "share", "libtool", "libltdl"), ltdl_dst)
        env = {
            "ACLOCAL": aclocal_cmd,
            "AUTOMAKE": automake_cmd,
            "LIBTOOLIZE": f"sh {os.path.join(lt, 'bin', 'libtoolize')}",
            "_lt_pkgdatadir": ltdata,
        }
        return env

    def build(self):
        autogen_env = None
        if str(self.settings.os) == "OHOS":
            # Old autotools probes for bare "ld"; OHOS only ships ld.lld.
            # Configure/libtool honour a preset $LD, which works regardless
            # of the filesystem: on device user storage (HMDFS) symlink
            # creation is refused, and copied #!/bin/sh wrapper scripts
            # cannot be exec'd, so a PATH-shim approach is not viable.
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = executables.get("c", "clang")
            if os.path.isabs(cc):
                lld_path = os.path.join(os.path.dirname(cc), "ld.lld")
                if os.path.isfile(lld_path):
                    os.environ["LD"] = lld_path
            # OHOS /tmp is read-only; autoreconf, libtoolize and configure
            # all need a writable temp directory.
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir
            # The hnp bash in PATH cannot getcwd() on HMDFS user storage
            # ("working directory cannot be determined"); bash's logical
            # pwd works from a preset $PWD, which propagates to every
            # child shell (configure, config.status, libtool, make).
            os.environ["PWD"] = self.build_folder
            # HMDFS on the .conan2 mount maps the process to a numeric
            # owner that does not match its own identity, so directory
            # access is granted through the file_manager group instead:
            # umask-022 directories (group rw) are writable, but the
            # `umask 077` mktemp directories of autoconf's AS_TMPDIR
            # (drwx--S---) are not — config.status dies with "could not
            # setup config files machinery".  BASH_ENV is sourced by every
            # non-interactive bash (configure, config.status via
            # CONFIG_SHELL below, make via $SHELL), so interpose a mktemp
            # wrapper that relaxes the umask.
            real_mktemp = shutil.which("mktemp") or "/bin/mktemp"
            bash_env = os.path.join(self.build_folder, "bash_env.sh")
            with open(bash_env, "w", encoding="utf-8") as f:
                f.write(
                    "mktemp() {\n"
                    "  local out\n"
                    '  out=$( (umask 022; ' + real_mktemp + ' "$@") )\n'
                    "  retval=$?\n"
                    "  [ $retval -ne 0 ] && return $retval\n"
                    "  printf '%s\\n' \"$out\"\n"
                    "  return 0\n"
                    "}\n"
                    "export -f mktemp\n"
                )
            os.environ["BASH_ENV"] = bash_env
            # config.status and the Makefile's $(SHELL) default to /bin/sh
            # (mksh), which does not source BASH_ENV; pin bash so the
            # mktemp wrapper is active everywhere (bash's getcwd is
            # already handled by the preset $PWD).
            os.environ["CONFIG_SHELL"] = (
                shutil.which("bash") or "/data/service/hnp/bin/bash")
            autogen_env = self._ohos_autogen_env()

        # Bootstrap: the GitHub tag archive ships no configure script.
        # Inline env-prefix form reaches autoreconf regardless of how Conan
        # composes the conanbuild environment.
        prefix = " ".join(f'{k}="{v}"' for k, v in autogen_env.items())
        if str(self.settings.os) == "OHOS":
            # autogen.sh passes `autoreconf -s` (--symlink); HMDFS refuses
            # link(2), so replicate the bootstrap with copy semantics (-i).
            self.run("mkdir -p m4 && touch ChangeLog",
                     cwd=self.source_folder, env="conanbuild")
            self.run(f"{prefix} autoreconf -f -i",
                     cwd=self.source_folder, env="conanbuild")
        else:
            self.run(f"{prefix} bash autogen.sh".strip(),
                     cwd=self.source_folder, env="conanbuild")

        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            configure_cmd = os.path.join(self.source_folder, "configure")
            args_file = os.path.join(self.build_folder, "conan", "configure_args.txt")
            with open(args_file, encoding="utf-8") as f:
                configure_args = f.read().strip()
            self.run(f'bash "{configure_cmd}" {configure_args}', env="conanbuild")
        else:
            autotools.configure()
        autotools.make()
        # Upstream has no test suite at all: no tests/ directory, no TESTS /
        # check_PROGRAMS in Makefile.am (inventory recorded in notes.md and
        # test_package/MANIFEST.yml per R51). `make check` would be a no-op.

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", folder=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["uio"]
        self.cpp_info.set_property("pkg_config_name", "libuio")
