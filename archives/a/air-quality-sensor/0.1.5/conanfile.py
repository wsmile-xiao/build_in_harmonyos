#!/usr/bin/env python3
"""Conan recipe — air-quality-sensor 0.1.5 (Autotools)

User space driver for AppliedSensor's Indoor Air Monitor (USB CO2 sensor).
Single CLI binary `air-quality-sensor` built from src/air10.c; talks to the
sensor over USB via libusb-1.0 (pkg-config module `libusb-1.0`).

HarmonyOS adaptation:
  - 0.1.5 has no GitHub tag; the authoritative source is the pristine Debian
    orig tarball (Debian pool + PureOS mirror, same content, sha256 pinned).
  - The release tarball ships configure.ac without a pre-generated configure
    script -> bootstrap with autoreconf (tool_requires automake + libtool).
  - help2man is unavailable on OHOS: the src/Makefile.am manpage regeneration
    rule is dropped by patch; the pre-generated manpage ships in the tarball.
  - E114: autoconf's config.status creates temp dirs with umask 077 which the
    HMDFS sandbox cannot write into; relax to 000 (afuse E114 precedent).
  - E002: OHOS /tmp is an erofs read-only mount; autotools steps (configure,
    make, install, mktemp, shell temp files) fall back to /tmp unless TMPDIR
    points at a writable dir. generate()/build() export a writable TMPDIR
    (hmbs-injected task dir first, $HOME/tmp fallback).
  - [shell_getcwd] HMDFS: getcwd()'s upward ".." parent walk fails even though
    forward path resolution works, so configure's dircheck (`ac_pwd=\`pwd\``)
    aborts with "working directory cannot be determined". Fix: export PWD=
    build_folder (bash/mksh `pwd` trust a valid $PWD) and patch configure to
    fall back to $PWD (nspr/4.37 + analog/homebrew precedent).
  - [run_conftest] Freshly compiled configure test programs cannot be executed
    on OHOS (build-sandbox exec/loader restrictions), so the "checking whether
    we are cross compiling" probe fails with "cannot run C compiled programs".
    Fix: declare --host (WITHOUT a matching --build — equal triplets keep
    cross_compiling=no per autoconf _AC_INIT_PARSE_ARGS), so the run failure
    flips cross_compiling=maybe -> yes and runtime probes are skipped
    (a52dec/nspr triplet pattern); also pre-seed ac_cv_build to skip
    config.guess.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AirQualitySensorConan(ConanFile):
    name = "air-quality-sensor"
    version = "0.1.5"
    description = "User space driver for AppliedSensor's Indoor Air Monitor (USB CO2 sensor)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/bwildenhain/air-quality-sensor"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def build_requirements(self):
        # The release tarball ships configure.ac only (no generated configure):
        # bootstrap with autoreconf; device lacks automake/aclocal (E178).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"air-quality-sensor supports Linux/OHOS, got {self.settings.os}"
            )

    def _writable_tmpdir(self):
        """E002: OHOS /tmp is an erofs read-only mount; autotools tools
        (configure/make/install, mktemp, shell temp files) fall back to /tmp
        unless TMPDIR points at a writable dir. Prefer the hmbs-injected task
        temp dir (HMBS_TMPDIR/TMPDIR/TMP/TEMP), else a per-package dir under
        $HOME; ensure it exists (acl/aaphoto/acme-redirect precedent).
        """
        for _var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            _value = os.environ.get(_var)
            if _value:
                tmpdir = _value
                break
        else:
            tmpdir = os.path.expanduser("~/tmp/air-quality-sensor")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Make libusb's libusb-1.0.pc visible to configure's PKG_CHECK_MODULES.
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # [run_conftest] Freshly compiled configure test programs cannot be
            # executed on OHOS (build-sandbox exec/loader restrictions), so the
            # "checking whether we are cross compiling" probe fails with
            # "cannot run C compiled programs". Declaring --host (WITHOUT a
            # matching --build — equal triplets keep cross_compiling=no per
            # autoconf _AC_INIT_PARSE_ARGS) makes the run failure flip
            # cross_compiling=maybe -> yes, skipping runtime probes
            # (a52dec/nspr triplet pattern).
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        env = tc.environment()
        # pkg.m4 (PKG_CHECK_MODULES) lives under the hnp pkg-config install.
        # aclocal must find it while we bootstrap configure.ac (afuse pattern).
        for _d in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            env.append_path("ACLOCAL_PATH", _d)
        # E002: /tmp is read-only on OHOS — export a writable TMPDIR through the
        # toolchain env so every build step (autoreconf/configure/make/install
        # and their temp files) avoids /tmp; reuse hmbs-injected task temp dir.
        tmpdir = self._writable_tmpdir()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tc.generate(env=env)

    def build(self):
        os.umask(0)
        # E002: /tmp is erofs read-only on OHOS; make every spawned tool
        # (autoreconf, configure, make, mktemp, shell temp files) use a
        # writable TMPDIR instead of falling back to /tmp. Also keeps
        # configure's ac_pwd/pwd working-directory probe from failing.
        tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        apply_conandata_patches(self)

        # Also inject pkg.m4 path dynamically (aircrack-ng pattern) in case the
        # glob above misses the actual pkg-config prefix.
        pkg_config = shutil.which("pkg-config")
        if pkg_config:
            real = os.path.realpath(pkg_config)
            prefix = os.path.dirname(os.path.dirname(real))
            aclocal_dir = os.path.join(prefix, "share", "aclocal")
            if os.path.isfile(os.path.join(aclocal_dir, "pkg.m4")):
                existing = os.environ.get("ACLOCAL_PATH", "")
                os.environ["ACLOCAL_PATH"] = (
                    f"{aclocal_dir}:{existing}" if existing else aclocal_dir
                )

        # Bootstrap configure (tarball ships configure.ac only).
        self.run("autoreconf --install --verbose", cwd=self.source_folder)

        # E114: config.status creates its temp dir with `umask 077`, yielding a
        # mode the HMDFS sandbox cannot write into. Relax to 000.
        # [shell_getcwd] HMDFS: getcwd()'s upward ".." parent walk fails even
        # though forward path resolution works, so configure's dircheck
        # (`ac_pwd=`pwd``) aborts with "working directory cannot be
        # determined". Patch it to fall back to $PWD (exported below) —
        # nspr/4.37 + analog/homebrew precedent for this exact error.
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            with open(configure, encoding="utf-8") as fh:
                content = fh.read()
            content = content.replace("umask 077", "umask 000")
            old_pwd_pattern = 'ac_pwd=`pwd` && test -n "$ac_pwd" &&'
            new_pwd_pattern = 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\ntest -n "$ac_pwd" &&'
            if old_pwd_pattern in content:
                content = content.replace(old_pwd_pattern, new_pwd_pattern, 1)
            else:
                self.output.warning(
                    "[shell_getcwd] working-dir pattern not found in configure; "
                    "relying on PWD env var only"
                )
            with open(configure, "w", encoding="utf-8") as fh:
                fh.write(content)

        if str(self.settings.os) == "OHOS":
            # [shell_getcwd] HMDFS upward getcwd fails; bash/mksh `pwd` trust a
            # valid absolute $PWD without calling getcwd, so export the build
            # dir explicitly (nspr/4.37 + analog/homebrew precedent).
            os.environ["PWD"] = self.build_folder
            # [run_conftest] Pre-seed ac_cv_build so AC_CANONICAL_BUILD skips
            # config.guess (may not run cleanly on OHOS); pairs with the
            # --host declaration in generate() (nspr pattern).
            os.environ["ac_cv_build"] = "aarch64-unknown-linux-gnu"
        # Ensure the build process CWD is the (forward-resolvable) build dir
        # before configure starts (nspr v12 pattern).
        os.chdir(self.build_folder)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream ships no test suite (audited: no tests/ dir, no check
        # target); nothing to run here.

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command-line tool: expose bin/, no libraries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
