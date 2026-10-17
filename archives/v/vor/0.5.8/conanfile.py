#!/usr/bin/env python3
"""Conan recipe — Variations on Rockdodger (vor) 0.5.8 for HarmonyOS PC (aarch64).

What this package is
====================
vor is an SDL 1.2 arcade game (12 .c + 14 .h, GPL-2.0-or-later).  Upstream
builds one executable (``bin/vor``) plus a data directory (``share/vor`` with
59 PNGs, bang.wav and mph.xm) installed by ``make install``.  There are no
libraries and no public headers, hence ``package_type = "application"``.

Adaptation notes
================
* SDL 1.2 stack.  The SDL 1.2 API (``<SDL.h>``, ``SDL_keysym.h``, SDL_image,
  SDL_mixer) is provided in this repository by **sdl12-compat/1.2.68**; the
  two add-ons are the repo recipes ``sdl_image/1.2.12`` and
  ``sdl_mixer/1.2.12``, which themselves ``requires("sdl12-compat/1.2.68")``
  (archives/s/sdl_image/1.2.12/conanfile.py:37,
   archives/s/sdl_mixer/1.2.12/conanfile.py:37).  There is no ``sdl/1.2.x``
  recipe in the ohpcd registry — do not "correct" these references.
* pkg-config module names.  ``configure.ac`` probes ``PKG_CHECK_MODULES([SDL],
  [sdl >= 1.2])`` (no fallback branch), plus ``SDL_image`` and ``SDL_mixer``.
  Conan's PkgConfigDeps emits ``sdl12-compat.pc`` / ``sdl_image.pc`` /
  ``sdl_mixer.pc``; module lookup is by file name and is case sensitive, so
  none of the three upstream names would resolve.  ``generate()`` therefore
  publishes the three upstream names as copies of the generated files (see
  ``_write_pkgconfig_aliases`` for the HMDFS case-insensitivity trap this
  dodges) - no source patching, no autoreconf run, and AutotoolsToolchain
  already prepends the generators folder to PKG_CONFIG_PATH.
* Data path.  ``Makefile.in`` bakes ``-DDATA_PREFIX="$(pkgdatadir)"`` into the
  binary and ``file.c:find_data_dir()`` uses it as its third candidate, so
  ``--prefix`` has to be the *final absolute package folder* (Conan's
  AutotoolsToolchain default prefix is ``/``, which would freeze the runtime
  path to ``/share/vor``).  Upstream's own ``VOR_DATA`` hook is additionally
  exported through ``runenv_info``.
* autoconf run probes.  A freshly linked ELF cannot be executed in the build
  sandbox (it is unsigned until ``package()`` signs it), so the dual triplet
  pins autoconf into cross mode and skips "cannot run C compiled programs"
  (same technique as the criticalmass recipe, and 522 repo recipes use the
  ``aarch64-unknown-linux-ohos`` triplet).
* ``make -j1``: HMDFS rejects the GNU-make jobserver mkfifo under
  ``$TMPDIR`` (``jobserver mkfifo: ... Operation not permitted``).
* Self-signing: OHOS refuses to execute unsigned ELFs, so ``package()`` strips
  the ``.codesign`` section and re-signs with ``-selfSign 1``.
* Upstream ships **no** test suite: ``Makefile.in`` has no ``check``/``TESTS``
  target at all and ``configure.ac`` has no ``AC_CONFIG_TESTDIR``, therefore no
  ``autotools.make(target="check")`` is issued here (it would be "No rule to
  make target 'check'").  The five-dimension ledger lives in notes.md.
"""
import glob
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cmd_args_to_string
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# (upstream pkg-config module name, Conan-generated module name, conan dep name)
_PKGCONFIG_ALIASES = (
    ("sdl", "sdl12-compat", "sdl12-compat"),
    ("SDL_image", "sdl_image", "sdl_image"),
    ("SDL_mixer", "sdl_mixer", "sdl_mixer"),
)


class VorConan(ConanFile):
    name = "vor"
    version = "0.5.8"
    description = (
        "Variations on Rockdodger (VoR) - SDL 1.2 space rock-dodging arcade game"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://sametwice.com/vor"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("game", "sdl", "sdl1.2", "arcade", "ohos")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must be an explicit allow-list, never == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vor supports Linux and OHOS only, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Every requirement is consumed at link time; no host-machine luck.
        self.requires("sdl12-compat/1.2.68")
        self.requires("sdl_image/1.2.12")
        self.requires("sdl_mixer/1.2.12")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _write_pkgconfig_aliases(self):
        """Expose the upstream (case-sensitive) module names to pkg-config.

        ``configure.ac`` asks for ``sdl``, ``SDL_image`` and ``SDL_mixer`` while
        PkgConfigDeps writes ``sdl12-compat.pc``, ``sdl_image.pc`` and
        ``sdl_mixer.pc``.  Each alias is therefore a *copy* of the generated
        file (Libs/Requires/Version kept verbatim, so the static add-on libs and
        their transitive png/jpeg/tiff/webp/zlib/zstd chain still resolve) with
        only Name/Description rewritten and the second include spelling added -
        the SDL 1.2 add-ons keep ``SDL_image.h``/``SDL_mixer.h`` under
        ``include/SDL`` while their ``cpp_info.includedirs`` is ``include``
        (same observation as the criticalmass recipe).

        HMDFS is case-insensitive: ``SDL_image.pc`` and ``sdl_image.pc`` are the
        SAME file there, so a forwarding stub (``Requires: sdl_image``) would
        clobber the real file and pkg-config would answer "Package sdl_image
        already in requires chain, skipping" with empty --cflags/--libs, which
        shows up later as "undefined symbol: IMG_Load / Mix_*".  Rewriting the
        file in place from its own content is safe on both case-sensitive and
        case-insensitive file systems.
        """
        for module, generated, dep in _PKGCONFIG_ALIASES:
            source = os.path.join(self.generators_folder, generated + ".pc")
            if not os.path.isfile(source):
                raise ConanException("PkgConfigDeps did not generate %s" % source)
            with open(source, encoding="utf-8") as handle:
                lines = handle.read().splitlines()
            include = self.dependencies[dep].package_folder.replace("\\", "/")
            rewritten = []
            for line in lines:
                if line.startswith("Cflags:"):
                    line = line + ' -I"%s/include/SDL" -I"%s/include"' % (include, include)
                elif line.startswith("Name:"):
                    line = "Name: %s" % module
                elif line.startswith("Description:"):
                    line = ("Description: copy of Conan's %s.pc published under the"
                            " case-sensitive module name %s used by upstream"
                            " configure.ac" % (generated, module))
                rewritten.append(line)
            target = os.path.join(self.generators_folder, module + ".pc")
            with open(target, "w", encoding="utf-8") as handle:
                handle.write("\n".join(rewritten) + "\n")
            self.output.info("pkg-config module %s -> %s" % (module, generated))

    def generate(self):
        # DATA_PREFIX is compiled from $(pkgdatadir), so the prefix must be the
        # folder the package will live in at run time.
        prefix = self.package_folder.replace("\\", "/")
        tc = AutotoolsToolchain(self, prefix=prefix)
        if self.settings.os == "OHOS":
            # Skip autoconf's "can we run conftest?" probe: unsigned ELFs cannot
            # execute in the build sandbox.
            tc.configure_args.extend(
                [
                    "--build=x86_64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        tc.generate()
        # LDFLAGS/CPPFLAGS for the bare AC_CHECK_LIB() probes in configure.ac
        AutotoolsDeps(self).generate()
        # real .pc files (sdl12-compat/sdl_image/sdl_mixer + transitive png/jpeg/tiff/webp/zlib/zstd)
        PkgConfigDeps(self).generate()
        self._write_pkgconfig_aliases()

    def _toolchain_configure_args(self):
        """Read back the arguments AutotoolsToolchain generated for configure().

        ``conanbuild.conf`` is the file the ``Autotools`` helper itself consumes,
        so re-using it keeps this recipe from duplicating (and drifting from) the
        toolchain-computed ``--prefix``/``--bindir``/triplet set.
        """
        conf = os.path.join(self.generators_folder, "conanbuild.conf")
        if not os.path.isfile(conf):
            raise ConanException("missing %s (AutotoolsToolchain.generate()?)" % conf)
        with open(conf, encoding="utf-8") as handle:
            for line in handle:
                if line.strip().startswith("configure_args"):
                    return shlex.split(line.split("=", 1)[1].strip())
        raise ConanException("configure_args not found in %s" % conf)

    def _hmdfs_relax_umask(self):
        """HMDFS: autoconf's ``umask 077`` temp dir makes config.status unable to
        write its own ``./confXXXXXX/subs1.awk`` ("Permission denied"), which
        aborts with ``config.status: error: could not setup config files
        machinery``.  Relaxing to 022 in the shipped ``configure`` is the
        workaround already used by the criticalmass/cheops/pakchois recipes; it
        is a build-time relaxation of a *generated* file, not a source patch, so
        nothing is committed into patches/.
        """
        for name in ("configure", "config.guess", "config.sub"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
            if "umask 077" in text:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text.replace("umask 077", "umask 022"))
                self.output.info("HMDFS umask 077 -> 022 in %s" % name)

    def build(self):
        apply_conandata_patches(self)
        self._hmdfs_relax_umask()
        autotools = Autotools(self)
        # CONFIG_SHELL trap (autoconf 2.69 re-exec), HMDFS getcwd:
        # the CI profile exports CONFIG_SHELL=/data/service/hnp/bin/bash, and that
        # bash cannot getcwd() inside HMDFS trees (it prints
        # "shell-init: error retrieving current directory: getcwd: ..." and then
        # configure dies with "working directory cannot be determined").  An
        # autoconf 2.69 configure re-executes itself with $CONFIG_SHELL whenever
        # that variable is non-empty, so the shebang/`sh` used to start it does
        # not matter.  The profile value is exported by the *last* script sourced
        # by conanbuild.sh, so neither os.environ nor a recipe env script can
        # beat it - only a per-command assignment can.  /bin/sh (toybox ash) is
        # the shell autoconf itself falls back to and probes clean on this
        # platform.  Same fix shape as the libfec draft
        # (knowledge/drafts/libfec-...-configshell-bash-getcwd-hmdfs.md).
        configure_script = os.path.join(self.source_folder, "configure")
        args = cmd_args_to_string(self._toolchain_configure_args())
        self.run(
            'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "%s" %s' % (configure_script, args),
            env="conanbuild",
        )
        # HMDFS: the jobserver mkfifo is rejected, so keep this serial
        autotools.make(args=["-j1"])
        # R51: upstream registers zero tests (no check/TESTS target) - see
        # notes.md "五维测试账本"; the consumer suite in test_package/ carries
        # the functional verification instead.

    def package(self):
        autotools = Autotools(self)
        # DESTDIR stays empty on purpose: --prefix already *is* the package
        # folder (needed for the baked DATA_PREFIX), and GNU make's install
        # rules concatenate "$(DESTDIR)$(pkgdatadir)", which with an absolute
        # prefix would otherwise produce <pkg><pkg>/share/vor.
        # -j1: same HMDFS jobserver/mkfifo reason as build().
        autotools.install(args=["DESTDIR=", "-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        binary = os.path.join(self.package_folder, "bin", "vor")
        if not os.path.isfile(binary):
            raise ConanException("make install produced no bin/vor at %s" % binary)
        self._sign_binaries()

    def _sign_binaries(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for path in glob.glob(os.path.join(self.package_folder, "bin", "*")):
            if not os.path.isfile(path):
                continue
            self.run(
                '"%s" --remove-section .codesign "%s" 2>/dev/null || true'
                % (objcopy, path)
            )
            self.run(
                '"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                % (signer, path, path)
            )

    def package_info(self):
        # application: nothing to link, nothing to include
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        # upstream's own data-path hook (file.c find_data_dir first candidate),
        # so the game also starts when launched from a directory without data/
        self.runenv_info.define_path(
            "VOR_DATA", os.path.join(self.package_folder, "share", "vor")
        )
