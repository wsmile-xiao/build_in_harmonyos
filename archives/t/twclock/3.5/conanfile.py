#!/usr/bin/env python3
"""Conan recipe — twclock 3.5 (X11/Motif world clock + CW ID generator)

twclock is a ham-radio desktop world clock by Ted Williams (WA0EIR): an
X Toolkit (Xt) + Motif GUI that shows the time in several call areas and can
beep or send a Morse (CW) station ID through PulseAudio.  It is a single
autotools-built C binary; there are no linkable libraries.

OHOS PC (aarch64, os=OHOS) adaptation notes:
- Motif (libXm) does not exist upstream of this repository; it is supplied by
  the locally adapted ``motif/2.3.8`` package (libXm.so.4 + Xm/*.h), exactly
  like the ``dinotrace/9.4f`` precedent.
- The upstream ``AC_FIND_MOTIF`` macro (acinclude.m4) hard-scans system
  directories; it is satisfied deterministically through its own
  ``--with-motif-includes`` / ``--with-motif-libraries`` override knobs.
- ``AC_PATH_XTRA`` is satisfied with ``--x-includes`` / ``--x-libraries``
  pointing at the packaged ``libx11`` headers/libs (dinotrace precedent).
- ``PKG_CHECK_MODULES(APPDEFS, xt)`` must resolve ``xt.pc``; the packaged
  ``libxt/1.3.1`` exports ``pkg_config_name = "xt"`` and appends its own
  pkgconfig dir to ``PKG_CONFIG_PATH``.  The app-defaults directory itself is
  pinned with ``--with-appdefaultdir`` so the missing ``appdefaultdir``
  variable in generated pc files cannot matter.
- Cross-build reality: the shipped configure runs the AC_FUNC_MALLOC test
  program; the pessimistic cross default (``malloc`` -> ``rpl_malloc``) would
  break linking, so ``ac_cv_func_malloc_0_nonnull=yes`` is pinned as a
  configure argument.
- Dependency include/lib roots are injected through the private Conan build
  folder (R49) — never a shared ``/usr/local`` prefix.
- E011: ``/bin/sh`` shebangs of ``configure`` and the ``config/`` helpers are
  repointed at the OHOS shell before configuring (no source patches).
- Packaging is an explicit copy() staging with loud verification: on the
  OHOS/HMDFS CI worker ``make install`` cannot be the authoritative driver
  (HMDFS ignores chmod, so ``config/install-sh`` cannot be executed), the
  same defect dinotrace documented.  An evidence-only ``make install`` trace
  is still captured, non-fatally.
- Headless reality: neither this machine nor OHOS provides an X server, so
  code paths reaching ``XtVaOpenApplication`` cannot succeed; without DISPLAY
  the binary prints the real Xt display error and exits non-zero.  The
  consumer test asserts exactly that (plus the ELF DT_NEEDED Motif/X11/
  PulseAudio chain); see test_package/MANIFEST.yml.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    copy,
    export_conandata_patches,
    get,
    load,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class TwclockConan(ConanFile):
    name = "twclock"
    version = "3.5"
    description = "Ham-radio world clock with beep/CW ID (X11/Motif) by WA0EIR"
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/sid/twclock"
    url = "https://ftp.debian.org/debian/pool/main/t/twclock/twclock_3.5.orig.tar.gz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: accept both Linux and OHOS, never `== "Linux"` only.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"twclock supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Motif (libXm.so.4 + <Xm/*.h>) — the widget toolkit twclock is
        # written against.  Its public headers transitively pull
        # <X11/Intrinsic.h> (libXt), <X11/Xlib.h> (libx11) and the xorgproto
        # protocol headers, so mark it transitive_headers; libXm links
        # libXt/libXext/libX11 so mark it transitive_libs as well.
        self.requires("motif/2.3.8", transitive_headers=True, transitive_libs=True)
        # Explicit direct requirements: twclock itself links -lXt -lX11
        # -lpulse-simple -lpulse (see configure.ac), and libxt must be on the
        # graph so PKG_CHECK_MODULES(APPDEFS, xt) resolves xt.pc.
        self.requires("libxt/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("libx11/1.8.13", transitive_headers=True, transitive_libs=True)
        self.requires("pulseaudio/17.0", transitive_headers=True, transitive_libs=True)
        # xorgproto owns <X11/X.h>, <X11/Xfuncproto.h>; declare it explicitly
        # so the header roots are guaranteed present on a clean graph.
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # libxpm is OPTIONAL: twclock's configure.ac detects it for the window
        # icon but has fallback (MAKE_ICON=0 if not found).  libxpm binary in
        # registry uses libx11/6.4.0 track which conflicts with motif's forced
        # libx11/1.8.13 track.  Omit libxpm; build will succeed without XPM icon.
        # self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)

    def layout(self):
        # Standard automake project: the shipped configure.ac/Makefile.in are
        # VPATH-capable, so a clean out-of-source build folder is used.
        basic_layout(self)

    def source(self):
        source_data = dict(self.conan_data["sources"])
        # These keys document the archive but are not get() arguments.
        source_data.pop("tar_format", None)
        source_data.pop("upstream_version", None)
        get(self, **source_data, strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            shell = self._ohos_shell()
            environment = tc.environment()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            environment.define_path("CC", self._compiler_executable("c", "clang"))
            environment.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            environment.define_path("LD", self._tool_executable("ld.lld", "lld", "ld"))
            environment.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            environment.define_path(
                "RANLIB", self._tool_executable("llvm-ranlib", "ranlib")
            )
            environment.define_path(
                "STRIP", self._tool_executable("llvm-strip", "strip")
            )
            environment.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            # R49: private build-folder include/lib roots only — never a
            # shared system prefix.
            environment.append("CPPFLAGS", self._dep_cppflags())
            environment.append("LDFLAGS", self._dep_ldflags())
            # PKG_CHECK_MODULES(APPDEFS, xt) must resolve xt.pc: make the
            # PkgConfigDeps generators folder visible (the libxt package also
            # appends its own lib/pkgconfig through buildenv_info).
            environment.append("PKG_CONFIG_PATH", self.generators_folder)
        # AC_PATH_XTRA/AC_PATH_X read --x-includes / --x-libraries; point them
        # at the packaged libx11 (which owns <X11/Xlib.h>) and its lib dir.
        libx11 = self.dependencies["libx11"]
        tc.configure_args.append(f"--x-includes={libx11.package_folder}/include")
        tc.configure_args.append(f"--x-libraries={libx11.package_folder}/lib")
        # AC_FIND_MOTIF (acinclude.m4) honours these two knobs, skipping its
        # hard-coded system directory scan.
        motif = self.dependencies["motif"]
        tc.configure_args.append(f"--with-motif-includes={motif.package_folder}/include")
        tc.configure_args.append(f"--with-motif-libraries={motif.package_folder}/lib")
        # The app-defaults resource file (Twclock) is a real runtime input of
        # twclock; install it inside the package prefix, not the host tree.
        tc.configure_args.append(
            "--with-appdefaultdir="
            + os.path.join(self.package_folder, "share", "X11", "app-defaults")
        )
        # AC_FUNC_MALLOC: the pessimistic cross default would #define malloc
        # to rpl_malloc and break the link; pin the well-known glibc/musl
        # behaviour (malloc(0) returns a non-NULL pointer).
        tc.configure_args.append("ac_cv_func_malloc_0_nonnull=yes")
        if str(self.settings.os) == "OHOS":
            tc.generate(env=environment)
        else:
            tc.generate()

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._patch_configure_runtime_shell()
            self._patch_shell_scripts()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # === Upstream test step (R51 / docs/TEST_QUALITY_SPEC.md §3.3) ===
        # twclock 3.5 ships NO test suite: no TESTS, no test sources.  The
        # automake `check` target exists but is an empty pass-through
        # (check-am: all-am).  It is still invoked verbatim, with the raw
        # output captured into the build log; the census evidence and the
        # platform exemption live in test_package/MANIFEST.yml and notes.md.
        self._run_upstream_tests()

    def package(self):
        # ---- Authoritative staging: mirror the upstream install set ------
        # `make install` is NOT the packaging driver: on the OHOS/HMDFS CI
        # worker `config/install-sh` cannot be executed (HMDFS ignores chmod)
        # and `cp` cannot overwrite live executables — the same defects the
        # dinotrace adaptation documented.  The real artifacts are staged
        # explicitly with copy() and then VERIFIED.
        #
        # The binary lands in <build>/src/twclock for a VPATH build, or in
        # <source>/src/twclock for an in-source build; accept either.
        twclock_src = os.path.join(self.build_folder, "src")
        if not os.path.isfile(os.path.join(twclock_src, "twclock")):
            twclock_src = os.path.join(self.source_folder, "src")
        copy(
            self,
            "twclock",
            src=twclock_src,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "twclock.1",
            src=os.path.join(self.source_folder, "man", "en"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        # The Twclock app-defaults resource file: twclock reads it for the
        # timezone/cwID configuration (dist_appdefault_DATA upstream).
        copy(
            self,
            "Twclock",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "share", "X11", "app-defaults"),
            keep_path=False,
        )
        copy(
            self,
            "twclock.desktop",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "applications"),
            keep_path=False,
        )
        copy(
            self,
            "twclock.png",
            src=os.path.join(self.source_folder, "src", "icons"),
            dst=os.path.join(self.package_folder, "share", "pixmaps"),
            keep_path=False,
        )
        # ---- Evidence-only upstream `make install` trace -----------------
        # Run upstream's installer to the extent the build host allows and
        # surface the raw output in the build log, staged OUTSIDE the package
        # folder and non-fatally, so it can never contribute to (or break)
        # the package.
        staging = os.path.join(self.build_folder, "install-staging")
        self.output.info("=== upstream `make install` trace (non-authoritative) ===")
        self.run(
            f"make install DESTDIR={shlex.quote(staging)}",
            ignore_errors=True,
            env="conanbuild",
        )
        self.output.info("=== end upstream `make install` trace ===")
        # ---- Loud verification: never silently ship an incomplete package -
        expected = {
            "bin/twclock": os.path.join(self.package_folder, "bin", "twclock"),
            "share/X11/app-defaults/Twclock": os.path.join(
                self.package_folder, "share", "X11", "app-defaults", "Twclock"
            ),
            "share/man/man1/twclock.1": os.path.join(
                self.package_folder, "share", "man", "man1", "twclock.1"
            ),
            "licenses/COPYING": os.path.join(
                self.package_folder, "licenses", "COPYING"
            ),
            "share/applications/twclock.desktop": os.path.join(
                self.package_folder, "share", "applications", "twclock.desktop"
            ),
            "share/pixmaps/twclock.png": os.path.join(
                self.package_folder, "share", "pixmaps", "twclock.png"
            ),
        }
        missing = [rel for rel, path in expected.items() if not os.path.isfile(path)]
        if missing:
            raise ConanException(
                "twclock/3.5 packaging incomplete; missing required artifact(s): "
                + ", ".join(missing)
                + f" under {self.package_folder}"
            )

    def package_info(self):
        # CLI/application package: only bin/, no linkable library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.cpp_info.requires = [
            "motif::motif",
            "libxt::libxt",
            "libx11::libx11",
            "pulseaudio::pulse-simple",
            "pulseaudio::pulse",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.set_property("cmake_file_name", "twclock")
        self.cpp_info.set_property("cmake_target_name", "twclock::twclock")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------------
    # OHOS helpers (mirrors archives/d/dinotrace/9.4f and archives/m/motif/2.3.8)
    # ------------------------------------------------------------------

    def _ohos_shell(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
            "/data/service/hnp/bin/bash",
        ]
        # Prefer an executable probe (WSL / conventional Linux).
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        # HMDFS ignores chmod (R49): fall back to an existence probe so a
        # present-but-non-executable-by-mode shell is still preferred over a
        # hard-coded path that does not exist on the worker.
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return "/system/bin/sh"

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _tool_executable(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    def _dependency_dirs(self, subdir):
        result = []
        for dependency in self.dependencies.host.values():
            path = os.path.join(dependency.package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _dep_cppflags(self):
        return [f"-I{path}" for path in self._dependency_dirs("include")]

    def _dep_ldflags(self):
        flags = []
        for path in self._dependency_dirs("lib"):
            flags.append(f"-L{path}")
            flags.append(f"-Wl,-rpath-link,{path}")
        return flags

    def _patch_configure_runtime_shell(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        shell = self._ohos_shell()
        # E011: HMDFS ignores chmod; be defensive about umask and repoint the
        # /bin/sh shebang at the OHOS shell.
        replace_in_file(
            self,
            configure_path,
            "umask 077",
            "umask 022",
            strict=False,
        )
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            replace_in_file(
                self,
                configure_path,
                pattern,
                f"#!{shell}",
                strict=False,
            )

    def _patch_shell_scripts(self):
        # The config/ helpers (install-sh, missing, depcomp, compile) carry
        # /bin/sh shebangs that do not resolve on OHOS; repoint them at the
        # OHOS shell.
        shell = self._ohos_shell()
        helpers = [
            os.path.join(self.source_folder, "config", name)
            for name in ("install-sh", "missing", "depcomp", "compile")
        ]
        for path in helpers:
            if not os.path.isfile(path):
                continue
            for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
                replace_in_file(self, path, pattern, f"#!{shell}", strict=False)

    def _run_upstream_tests(self):
        # R51: run the upstream test targets verbatim (never fake them).
        # `make check` on twclock is an empty automake pass-through, so it is
        # expected to succeed without exercising anything; the raw output is
        # captured into the build log as evidence.  The GUI itself cannot be
        # exercised headlessly (see test_package/MANIFEST.yml exemption).
        log_name = "upstream-test.log"
        script = (
            "{\n"
            '  echo "### upstream test census (twclock 3.5) ###"\n'
            "  echo \"$(grep -nE '^(check|test):' Makefile.in)\"\n"
            '  echo "### make check verbatim ###"\n'
            "  ( unset DISPLAY; timeout 300 make check ) 2>&1 ; echo \"CHECK_EXIT=$?\"\n"
            f"}} > {log_name} 2>&1\n"
        )
        self.run(script, ignore_errors=True, env="conanbuild")
        output = load(self, log_name)
        self.output.info("=== twclock 3.5 upstream test step (raw output) ===")
        for line in output.splitlines():
            self.output.info(f"[upstream-test] {line}")
        self.output.info("=== end twclock upstream test step ===")
