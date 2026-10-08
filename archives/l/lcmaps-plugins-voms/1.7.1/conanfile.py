#!/usr/bin/env python3
"""Conan recipe — lcmaps-plugins-voms 1.7.1 (Autotools, LCMAPS plugin bundle).

What this package is
--------------------
Six LCMAPS evaluation plugins (liblcmaps_voms, liblcmaps_ban_fqan,
liblcmaps_voms_{localaccount,poolaccount,localgroup,poolgroup}) installed to
<prefix>/lib/lcmaps/ together with the `lcmaps_*.mod` symlink aliases the
LCMAPS plugin manager resolves. They are dlopen()ed by the LCMAPS framework at
run time; the FQAN/pool mapping data they operate on is supplied through the
LCMAPS credential delegate chain.

Adaptation notes (OHOS, aarch64/musl)
-------------------------------------
- Compile-time dependency closure is lcmaps only (plus libdl, which musl
  provides in libc — configure's AC_CHECK_LIB([dl],[dlsym]) passes, E013).
  The "voms" in the name is misleading for build purposes: configure.ac has no
  voms library check (the AC_VOMS macro is only referenced and never defined),
  src/Makefile.am has no voms LIBADD, and the plugin sources include only
  lcmaps/*.h headers. Verified against the 1.7.1 tarball.
- Patches (build-vehicle only, no source/platform macros):
  * 0001/0002: 2014-era config.guess/config.sub do not recognize
    `uname -s` = HarmonyOS (same root cause as lcmaps/1.6.7, hunks adapted to
    the older file format).
  * 0003: autoconf's config.status creates its tmp dir with
    `(umask 077 && mktemp -d ./confXXXXXX)`; toybox mktemp -d mkdir(0700)
    yields an unwritable drwx--S--- directory on HMDFS and chmod cannot repair
    it (E046), so `can't create ./confXXXXXX/subs1.awk: Permission denied`
    aborts config.status. The patch makes the mktemp call fail so config.status
    falls back to its own `./conf$$-$RANDOM` + mkdir path, which HMDFS
    normalizes to a writable drwxrws--x.
- Dependency metadata (R49): the lcmaps/1.6.7 package ships its .pc files with
  a hardcoded `prefix=/` (this package is the first pkg-config consumer to
  surface it). generate() rewrites the prefix to the dependency's
  package_folder inside a private <build_folder>/prefix/lib/pkgconfig and
  prepends that to PKG_CONFIG_PATH; no shared/system prefix is touched.
- No autoreconf (E089): the tarball ships a complete configure/aclocal.m4 and
  the project/ macro directory.
- E075: C_INCLUDE_PATH/CPLUS_INCLUDE_PATH/LIBRARY_PATH are unset so pkg-config
  --cflags and configure header probes stay honest.
- Shared delivery is mandatory: LCMAPS loads these plugins via dlopen(), so a
  static-only build would be unusable (upstream builds them with
  `-avoid-version` and symlinks lcmaps_*.mod -> liblcmaps_*.so).
- Upstream has NO automated test suite (no check target / TESTS /
  check_PROGRAMS in any Makefile.am, no tests/ directory). Verification is the
  OHOS smoke test in test_package/test.c: dlopen/dlsym of the packaged plugins
  plus packaged-file assertions.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, chmod, export_conandata_patches, get, mkdir, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LcmapsPluginsVomsConan(ConanFile):
    name = "lcmaps-plugins-voms"
    version = "1.7.1"
    description = (
        "LCMAPS plugins: VOMS/FQAN credential mapping (voms localaccount/"
        "poolaccount/localgroup/poolgroup, ban_fqan) for the LCMAPS framework"
    )
    license = "Apache-2.0"
    url = "https://software.nikhef.nl/security/lcmaps-plugins-voms/"
    homepage = "https://github.com/Nikhef-lcaae/lcmaps-plugins-voms"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lcmaps/1.6.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # HMDFS: autoconf's AC_PROG_MKDIR_P probe rejects the system mkdir -p
        # behaviour and falls back to `install-sh -c -d` as MKDIR_P; make then
        # execve()s that helper from a python-descended process, which HMDFS
        # denies outright (EACCES). Force the real mkdir instead.
        tc.configure_args.append("MKDIR_P=mkdir -p")
        env = tc.environment()
        # E075: keep pkg-config --cflags and configure header probes honest.
        env.unset("C_INCLUDE_PATH")
        env.unset("CPLUS_INCLUDE_PATH")
        env.unset("LIBRARY_PATH")
        # R49: private prefix for dependency metadata injection. The lcmaps
        # package's .pc files carry `prefix=/`; rewrite them into a
        # build-folder-local pkgconfig dir and prepend it to PKG_CONFIG_PATH.
        deps = self.dependencies["lcmaps"]
        pc_src = os.path.join(deps.package_folder, "lib", "pkgconfig")
        pc_dst = os.path.join(self.build_folder, "prefix", "lib", "pkgconfig")
        mkdir(self, pc_dst)
        for name in sorted(os.listdir(pc_src)):
            if not name.endswith(".pc"):
                continue
            with open(os.path.join(pc_src, name), "r") as fh:
                text = fh.read()
            text = text.replace("prefix=/", "prefix=%s" % deps.package_folder)
            with open(os.path.join(pc_dst, name), "w") as fh:
                fh.write(text)
        env.prepend("PKG_CONFIG_PATH", pc_dst)
        # NOTE: tc.generate() without an argument rebuilds a fresh env
        # internally (Environment() is constructed per-call), silently
        # dropping every unset()/prepend() made above. Pass the modified
        # instance explicitly.
        tc.generate(env=env)

    def _restore_exec_mode(self, script_path):
        # E490 (restore-known-autotools-script-modes), HMDFS variant: after a
        # content rewrite (conan patch application) the HMDFS-backed cache
        # leaves the file in a state where chmod cannot re-arm the executable
        # bit (verified: chmod 0o777 is silently ignored, /bin/sh exec fails
        # with "Permission denied"). Deleting and recreating the file resets
        # the state, after which chmod works and exec succeeds.
        with open(script_path, "rb") as fh:
            data = fh.read()
        # HMDFS lands chmod() as (mode & ~umask); conan runs with a restrictive
        # umask, so zero it for the recreate+chmod window.
        old_umask = os.umask(0)
        try:
            before = oct(os.stat(script_path).st_mode)
            os.remove(script_path)
            with open(script_path, "wb") as fh:
                fh.write(data)
            created = oct(os.stat(script_path).st_mode)
            chmod(self, script_path, 0o777)
            after = oct(os.stat(script_path).st_mode)
            if not os.access(script_path, os.X_OK):
                # In-process chmod is silently ignored by HMDFS inside the
                # conan runtime; delegate to the OS chmod binary instead.
                subprocess.run(
                    ["/system/bin/chmod", "777", script_path], check=False
                )
                after2 = oct(os.stat(script_path).st_mode)
            else:
                after2 = after
            self.output.warning(
                "### OHC-DEBUG umask=0 old=%s created=%s chmod777=%s chmodbin=%s %s"
                % (before, created, after, after2, script_path))
        finally:
            os.umask(old_umask)

    def build(self):
        # Platform-only patches: config.guess/config.sub HarmonyOS recognition
        # + config.status mktemp/HMDFS workaround (see module docstring).
        apply_conandata_patches(self)
        # The HMDFS-backed conan cache drops executable bits on the autotools
        # helper scripts (E490), making /bin/sh ./configure fail with
        # "Permission denied". Restore known modes before configure.
        for script in (
            "configure",
            "config.guess",
            "config.sub",
            "install-sh",
            "missing",
            "depcomp",
            "compile",
            "ltmain.sh",
        ):
            script_path = os.path.join(self.source_folder, script)
            if os.path.exists(script_path):
                self._restore_exec_mode(script_path)
        # HMDFS/kernel attr-cache latency: an exec() issued immediately after
        # the mode change still sees the old (non-executable) attributes and
        # fails with EACCES. Wait out the cache before invoking configure.
        import time
        time.sleep(2)
        # No autoreconf (E089): the tarball carries a complete configure.
        autotools = Autotools(self)
        # HMDFS execve restriction: processes born from the conan python
        # runtime cannot execve() files on HMDFS user storage at all (EACCES
        # even with mode 0o777; interpreter-mode execution is unaffected).
        # Autotools.configure() execs ./configure directly, so run it through
        # the shell interpreter instead, with the exact same args it would
        # have used (from the generated conanbuild.conf).
        configure_cmd = 'sh "{}/configure" {}'.format(
            self.source_folder, autotools._configure_args
        )
        self.run(configure_cmd, env="conanbuild")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Drop libtool archives: they embed absolute build paths and the
        # plugins are consumed via dlopen, never linked through libtool.
        rm(self, "*.la", os.path.join(self.package_folder, "lib", "lcmaps"))
        # Drop upstream docs/man pages: not part of the runtime deliverable
        # and they duplicate what the source tarball already provides.
        shutil.rmtree(os.path.join(self.package_folder, "share"), ignore_errors=True)
        # libtool leaves a .libs staging dir behind inside lib/lcmaps on some
        # installs; keep the package tree clean.
        shutil.rmtree(
            os.path.join(self.package_folder, "lib", "lcmaps", ".libs"),
            ignore_errors=True,
        )

    def package_info(self):
        # No headers are installed by this package.
        self.cpp_info.includedirs = []
        # Plugin objects live in lib/lcmaps/ (with lcmaps_*.mod symlink
        # aliases). They are dlopen()ed by the LCMAPS framework and must not
        # be linked into consumers, so no libs are advertised.
        self.cpp_info.libdirs = ["lib/lcmaps"]
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
