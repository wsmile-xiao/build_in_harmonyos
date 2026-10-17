#!/usr/bin/env python3
"""Conan recipe for GNU oSIP 5.3.2 (package name: libosip).

Upstream tarball/configure name is ``libosip2`` and it builds two libraries:

* ``libosip2``       — SIP transaction/state-machine layer (osip2/osip.h)
* ``libosipparser2`` — SIP message parser layer (osipparser2/osip_parser.h)

Both carry SONAME ``*.so.15`` (``-version-info 15:1:0``). The package name
``libosip`` follows this repository's branch/dir naming (branch
feat/libosip-5.3.2); ``cpp_info`` exposes both libs so consumers can link
either layer. No third-party dependency: optional pthread, librt
(clock_gettime); libsocket only on non-Linux (not used on OHOS).

OHOS adaptation notes (verified on the real device, 2026-09-10):

* E007 — the tarball ships config.guess (2014-03-23) / config.sub
  (2014-09-11), which do NOT know ``aarch64-unknown-linux-ohos``:
  config.guess cannot guess the build type on HarmonyOS at all
  (``uname -s`` returns ``HarmonyOS``) and config.sub rejects the
  triplet. Fixed by 0001-config-guess-config-sub-ohos.patch (teaches
  both scripts ``linux-ohos``) plus explicit
  ``--build/--host=aarch64-unknown-linux-ohos`` in generate(). The
  scripts are deliberately NOT borrowed from the host automake: stock
  automake does not know HarmonyOS either, and CI workers may not even
  have that share dir.
* E011 — HMDFS uid-mapping makes config.status's ``umask 077`` temp dirs
  unwritable; fix by rewriting ``umask 077`` → ``umask 022`` in configure
  (and friends) before configuring.
* No RPATH — libtool bakes an absolute build RUNPATH into the installed
  .so (``hardcode_libdir_flag_spec`` with ``-rpath $libdir``). There is no
  patchelf on this host and lld has no --no-rpath; instead the recipe
  patches the generated ``libtool`` script to set
  ``hardcode_libdir_flag_spec=""`` right after configure, which drops
  DT_RUNPATH from every .so while keeping DT_SONAME/DT_NEEDED intact
  (verified: libosip2.so.15.0.1 & libosipparser2.so.15.0.1 both clean).
  In-tree test binaries then need LD_LIBRARY_PATH, set in
  _run_upstream_tests().
* install-sh — the tarball's 2003-era scripts/install-sh is broken on
  hmfs: batched (and repeated single) installs write over the destination
  directory as if it were a file, silently dropping every header past the
  first. The recipe swaps in the host automake-1.16 helper (together with
  missing/compile/depcomp - best-effort: when no automake share dir is
  found the tarball versions are kept).
* Upstream tests (--enable-test, default no): the ``tst`` script (what
  ``make check`` invokes) drives torture_test over 161 res/ files —
  122 cases, run in both normal and -c (clone) modes — plus 10 noinst
  unit programs (turl tfrom tto tcontact tvia tcallid tcontentt trecordr
  troute twwwa) that must be run by hand with ``res/`` as argument.
  build() runs all of them; failure aborts the package. ``make check``
  itself is NOT invoked directly: under hmfs its relative
  ``./$(top_srcdir)/src/test/tst`` invocation fails with "inaccessible
  or not found"; running ``sh tst`` with absolute paths is identical.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibosipConan(ConanFile):
    name = "libosip"
    version = "5.3.2"
    description = (
        "GNU oSIP: an LGPL C library implementing the SIP signaling "
        "protocol — osip2 (transaction/state machine) and osipparser2 "
        "(SIP message parser)."
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gnu.org/software/osip/"
    url = ""
    topics = ("sip", "voip", "signaling", "osip", "telephony", "gnu")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_pthread": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_pthread": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Pure C package: drop C++ settings so the package id stays stable.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E007: patch the pristine tarball's scripts/config.guess and
        # scripts/config.sub so they accept aarch64-unknown-linux-ohos.
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ #
    # E007 + E011 fixes, applied to the extracted source before configure.
    def _patch_source_tree(self):
        # E011: HMDFS + umask 077 → config.status cannot create its temp
        # subs*.awk/subs*.sed files ("could not setup config files
        # machinery"). Relax the umask in the scripts that hardcode it
        # (only configure and config.status do).
        for script in ("configure", "config.status"):
            p = os.path.join(self.source_folder, script)
            if os.path.isfile(p):
                replace_in_file(self, p, "umask 077", "umask 022",
                                strict=False)
        # tarball files may be read-only (HMDFS uid mapping): make the
        # tree user-writable so configure can regenerate files.
        for root, dirs, files in os.walk(self.source_folder):
            for name in dirs + files:
                path = os.path.join(root, name)
                try:
                    os.chmod(path, os.stat(path).st_mode | 0o200)
                except OSError:
                    pass

        # The tarball's 2003-era scripts/install-sh is broken on hmfs:
        # a second single-file install (and every batched install) writes
        # over the destination directory as if it were a file, silently
        # losing headers/libs. Replace it with the host automake-1.16
        # version (verified working on this fs).
        import glob as _glob
        am_dir = _glob.glob(os.path.join(
            os.path.dirname(os.path.dirname(
                shutil.which("clang") or "/usr/bin/clang")),
            "share", "automake-*"))
        if am_dir:
            # E007: config.guess/config.sub are deliberately NOT copied
            # from here - they are fixed by the conandata patch (0001)
            # plus the explicit --build/--host triplet in generate();
            # host automake's own versions may not know HarmonyOS either.
            # install-sh/missing/compile/depcomp replaced for the same
            # vintage/robustness reasons as above.
            for name in ("install-sh", "missing", "compile", "depcomp"):
                src = os.path.join(sorted(am_dir)[-1], name)
                dst = os.path.join(self.source_folder, "scripts", name)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    os.chmod(dst, 0o755)

    # ------------------------------------------------------------------ #
    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26 default static; explicit toggles keep configure deterministic.
        if self.options.shared:
            tc.configure_args += ["--enable-shared", "--disable-static"]
        else:
            tc.configure_args += ["--disable-shared", "--enable-static"]
        # pthread/sem: upstream checks for them; keep the default (yes on
        # OHOS — musl provides them) but expose the toggle.
        if not self.options.with_pthread:
            tc.configure_args.append("--disable-pthread")
        # Build the upstream test programs (torture suite + unit tools);
        # default is "no", which would skip everything.
        tc.configure_args.append("--enable-test")
        if self.settings.os == "OHOS":
            if self.settings.arch != "armv8":
                raise ConanInvalidConfiguration(
                    "libosip/5.3.2 currently supports only OHOS armv8"
                )
            # E007: pass the real target triplet explicitly. The patched
            # config.guess/config.sub accept aarch64-unknown-linux-ohos,
            # and configure must never fall back to guessing the build
            # type (the 2014 originals cannot: uname -s is "HarmonyOS").
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.generate()

    def build(self):
        self._patch_source_tree()
        autotools = Autotools(self)
        autotools.configure()
        self._drop_libtool_rpath()
        autotools.make(args=["-j1"])
        self._run_upstream_tests(autotools)

    # ------------------------------------------------------------------ #
    # libtool bakes an absolute RUNPATH into every .so it links. Empty the
    # hardcode spec so the final .so files carry no DT_RUNPATH/DT_RPATH;
    # DT_SONAME and DT_NEEDED stay untouched (verified on device).
    def _drop_libtool_rpath(self):
        p = os.path.join(self.build_folder, "libtool")
        replace_in_file(
            self, p,
            'hardcode_libdir_flag_spec="\\$wl-rpath \\$wl\\$libdir"',
            'hardcode_libdir_flag_spec=""',
        )

    # Run the upstream suite: the `tst` script (what `make check` invokes)
    # drives torture_test over the 161 res/ files — 122 cases — plus the
    # 10 noinst unit programs run by hand with res/ as argument.
    # All binaries link against the uninstalled .so via LD_LIBRARY_PATH.
    # We do NOT call `make check`: under hmfs the Makefile's relative
    # `./$(top_srcdir)/src/test/tst` invocation fails with "inaccessible
    # or not found"; running `sh tst` with absolute paths is identical.
    def _run_upstream_tests(self, autotools):
        from conan.tools.env import Environment
        bdir = os.path.join(self.build_folder, "src", "test")
        srcdir = os.path.join(self.source_folder, "src", "test")
        libpath = os.pathsep.join([
            os.path.join(self.build_folder, "src", "osipparser2", ".libs"),
            os.path.join(self.build_folder, "src", "osip2", ".libs"),
        ])
        env = Environment()
        env.define("LD_LIBRARY_PATH", libpath)
        env.define("TMPDIR", os.environ.get("TMPDIR", "/data/local/tmp"))
        envvars = env.vars(self, scope="run")

        # torture suite: tst → torture_test × 161 res/ files (122 cases),
        # normal + -c (clone) modes, exactly as `make check` would.
        with envvars.apply():
            for extra in (None, "-c"):
                cmd = 'sh "{}" "{}"'.format(
                    os.path.join(srcdir, "tst"),
                    os.path.join(srcdir, "res"))
                if extra:
                    cmd += " " + extra
                rc = self.run(cmd, env=None, cwd=bdir)
                if rc != 0:
                    from conan.errors import ConanException
                    raise ConanException(
                        "upstream torture suite failed (mode={}): rc={}"
                        .format(extra or "normal", rc))
                # torture_test exit code IS the failing-case count on
                # this suite; rc==0 above means all cases passed (the
                # "unit testing failed: 0" summary is printed by tst).

        # 10 unit programs (binary names differ from source names:
        # turls.c → turl)
        unit_bins = ["turl", "tfrom", "tto", "tcontact", "tvia",
                     "tcallid", "tcontentt", "trecordr", "troute", "twwwa"]
        res_dir = os.path.join(srcdir, "res")
        failures = []
        with envvars.apply():
            for name in unit_bins:
                binpath = os.path.join(bdir, name)
                rc = self.run('"{}" "{}"'.format(binpath, res_dir),
                              env=None, cwd=bdir)
                if rc != 0:
                    failures.append("{} (rc={})".format(name, rc))
        if failures:
            from conan.errors import ConanException
            raise ConanException(
                "upstream unit tests failed: " + ", ".join(failures))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # .la files reference build-tree paths; remove them.
        for root, _, files in os.walk(os.path.join(self.package_folder, "lib")):
            for fn in files:
                if fn.endswith(".la") or fn.endswith(".lai"):
                    os.unlink(os.path.join(root, fn))
        if self.options.shared:
            self._sign_shared_libs()

    # OHOS clang self-signs .so at link time with a signature tied to the
    # build tree; strip and re-sign so the packaged library is valid
    # (practice from libxml2/2.15.3).
    def _sign_shared_libs(self):
        import glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = [p for p in glob.glob(os.path.join(libdir, "**", "lib*.so*"),
                                    recursive=True)
               if not os.path.islink(p)]
        for so in sos:
            self.run('objcopy --remove-section .codesign "{}" 2>/dev/null || true'
                     .format(so))
            self.run('binary-sign-tool sign -inFile "{}" -outFile "{}" '
                     '-selfSign 1'.format(so, so))

    def package_info(self):
        self.cpp_info.libs = ["osip2", "osipparser2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libosip")
        self.cpp_info.set_property("cmake_target_name", "libosip::libosip")
        self.cpp_info.set_property("pkg_config_name", "libosip2")
        # musl provides pthread/rt in libc, but keep them explicit for
        # portability of consumer link lines.
        self.cpp_info.system_libs = ["pthread", "rt"]
