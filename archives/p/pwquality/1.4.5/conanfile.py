#!/usr/bin/env python3
"""Conan recipe for pwquality (libpwquality) 1.4.5 — password quality checker.

HarmonyOS PC adaptation of the C library + its two CLI tools.

Products (from ``src/Makefile.am``): ``libpwquality.so``, ``pwquality.h``,
``pwquality.pc``, and the executables ``pwscore`` / ``pwmake``.

## Dependencies

| Dependency | Need | Availability |
|---|---|---|
| ``cracklib`` | **required** by default (``AC_CHECK_LIB([crack], [FascistCheck])``; configure errors "No or unusable cracklib library" if absent) | ohpcd: **cracklib/2.10.3** ✓ |
| ``libintl`` | NLS via ``AM_GNU_GETTEXT([external])`` | ohpcd: **libintl/0.26.1** ✓ |
| PAM | ``AC_ARG_ENABLE([pam])`` default ``check`` → silently disabled when absent | ohpcd: linux-pam/1.7.2 ✓ (not used; see below) |

PAM is explicitly **disabled**: this package's purpose here is the library and
the ``pwscore``/``pwmake`` tools. The PAM module (``pam_pwquality.so``) belongs
in the system secure-lib directory and needs consumer-side PAM configuration,
so it is out of scope — and disabling it also removes a dependency the tools do
not need.

Python bindings are **disabled** too (upstream default is *yes*): they would
require the conan ``python`` package for a small binding, and the Python side is
covered separately in this archive.

## OHOS adaptations (see patches/)

1. **``config.guess`` / ``config.sub`` for the OHOS triplet** (R15). Upstream
   ships the **2018**-generation helpers ("unable to guess system type",
   ``--build``/``--host`` hard-coding is forbidden by this archive's rule, see
   ``scripts/patch-autotools-ohos.pl``'s header). The stock script only patched
   1/5 of this pair because that generation has no ``GUESS=`` variable and its
   ``config.sub`` lacks the ``linux-ohos`` patterns — so the patch here follows
   the **old format**: ``config.guess`` gets a self-echoing
   ``*:HarmonyOS:*:*)`` branch, and ``config.sub`` gets ``linux-ohos*`` added to
   both the ``maybe_os`` list and the os-validity list. Verified: the patched
   ``config.guess`` prints ``aarch64-unknown-linux-ohos`` and ``config.sub``
   accepts both ``aarch64-unknown-linux-ohos`` and ``aarch64-linux-ohos``.

2. **``umask 077`` widened to ``022``** in ``configure`` — same HMDFS trap this
   archive hit with cracklib: ``config.status`` creates its ``confXXXXXX`` temp
   dir with ``umask 077`` in the *build* directory (not ``TMPDIR``), and HMDFS
   then refuses writes into that 700 dir (``Permission denied``). Widening the
   umask in ``configure`` also fixes the text inherited by ``config.status``.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain

_REQUIRED_HEADERS = ("src/pwquality.h", "src/pwscore.c", "src/pwmake.c")


class PwqualityConan(ConanFile):
    name = "pwquality"
    version = "1.4.5"
    description = "Password quality checker (libpwquality) with pwscore/pwmake"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/libpwquality/libpwquality"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        # cracklib is a hard requirement: configure aborts with
        # "No or unusable cracklib library" when FascistCheck is missing.
        self.requires("cracklib/2.10.3")
        # NLS/libintl is deliberately NOT required. This build passes
        # --disable-nls, and ohpcd's libintl is unusable for linking anyway:
        # its libintl.so.8 lists gettext/dgettext/bindtextdomain as *undefined*
        # symbols (measured with `nm -D -u`), so AutotoolsDeps injecting -lintl
        # makes lld abort with
        #   "undefined reference due to --no-allow-shlib-undefined: gettext"
        # which surfaces as configure's misleading
        #   "C compiler cannot create executables".

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps feeds the -I/-L/-l of cracklib (and libintl) into
        # configure/make; without it AC_CHECK_LIB([crack],[FascistCheck]) fails
        # and configure aborts with "No or unusable cracklib library".
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        # --build/--host are deliberately NOT set: config.guess/config.sub are
        # patched for OHOS instead (this archive's rule; see patches/).
        tc.configure_args.extend([
            "--disable-nls",              # libintl is wired via AutotoolsDeps
            "--disable-pam",              # PAM module is out of scope (see header)
            "--disable-python-bindings",  # upstream default is *yes*
            "--disable-static",
            "--enable-shared" if self.options.shared else "--disable-shared",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        for rel in _REQUIRED_HEADERS:
            if not os.path.isfile(os.path.join(self.source_folder, rel)):
                raise ConanException(f"{rel} missing from the source tree")

        # HMDFS trap (same as cracklib): config.status creates its temp dir with
        # `umask 077` in the build directory, and writes into it are refused.
        # The configure script embeds that text for config.status to inherit, so
        # widening it here fixes both.
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8") as fh:
            text = fh.read()
        if "umask 077" in text:
            with open(configure, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text.replace("umask 077", "umask 022"))
            self.output.info("widened umask 077 -> 022 in configure (HMDFS)")

        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits the HMDFS jobserver fifo (E074).
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Drop libtool wrappers: their hard-coded libdir breaks consumers.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    os.remove(os.path.join(libdir, name))

        so = [n for n in os.listdir(libdir) if n.startswith("libpwquality.so")
              ] if os.path.isdir(libdir) else []
        if not so:
            raise ConanException("libpwquality.so missing from the package folder")
        for tool in ("pwscore", "pwmake"):
            if not os.path.isfile(os.path.join(self.package_folder, "bin", tool)):
                raise ConanException(f"{tool} missing from the package folder")

    def package_info(self):
        self.cpp_info.libs = ["pwquality"]
        # The upstream pkg-config name is "pwquality" (src/pwquality.pc.in), which
        # already matches the conan package name, so no alias is needed — but set
        # it explicitly so consumers via pkg_config keep working.
        self.cpp_info.set_property("pkg_config_name", "pwquality")
