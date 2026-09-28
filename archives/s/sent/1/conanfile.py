#!/usr/bin/env python3
"""Conan recipe — sent 1 (suckless plain-text presentation tool for X11).

Build system: the upstream bare ``Makefile`` plus ``config.mk``.  There is no
configure script, no autotools and no CMake — the whole build is ``make``
followed by ``make install PREFIX=... MANPREFIX=...``.

How the Conan dependencies are injected into a suckless Makefile
---------------------------------------------------------------
``config.mk`` hardcodes host paths::

    X11INC = /usr/X11R6/include
    X11LIB = /usr/X11R6/lib
    INCS   = -I. -I/usr/include -I/usr/include/freetype2 -I${X11INC}
    LIBS   = -L/usr/lib -lc -lm -L${X11LIB} -lXft -lfontconfig -lX11
    CFLAGS += -g -std=c99 -pedantic -Wall ${INCS} ${CPPFLAGS}
    LDFLAGS += -g ${LIBS}
    CPPFLAGS = -DVERSION="${VERSION}" -D_XOPEN_SOURCE=600

The two variables that carry the bad host paths (``INCS`` / ``LIBS``) are
plain ``=`` assignments, so overriding them **on the make command line**
replaces them wholesale, while ``CFLAGS``/``LDFLAGS`` keep their ``+=``
append semantics and still contribute ``-std=c99 -pedantic -Wall`` and,
importantly, ``CPPFLAGS`` still contributes ``-DVERSION="1"``.

Passing ``CFLAGS=``/``LDFLAGS=``/``CPPFLAGS=`` on the command line instead
(the way farbfeld does) would silently discard ``-DVERSION`` — ``sent -v``
would then print ``sent-`` — which is why this recipe deliberately does *not*
touch them.  The ``-v`` assertion in test_package is what guards this.

Nothing is stripped: sent's Makefile has no ``STRIP`` variable and
``make install`` is a plain ``cp -f``, so no compiler or strip tool path can
end up baked into the installed binary.  The binary is ELF code-signed
afterwards because the OHOS kernel refuses to execute unsigned ELF.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
# Conan 2: AutotoolsToolchain lives in conan.tools.gnu (conan.tools.env only
# carries the Virtual*Env helpers); conan 1.x allowed the combined import.
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# Directly linked by upstream ``LIBS`` (``-lc`` is dropped: the compiler
# driver links libc implicitly, so naming it again is a no-op).
LINK_DEPS = ("libxft", "fontconfig", "libx11")
# libxft/libx11 already pin these; they are repeated here at the *identical*
# pinned versions so the recipe can reach their ``include/`` folders directly
# (``self.dependencies`` only exposes immediate requirements) and use them in
# place of upstream's hardcoded ``-I/usr/include``, ``-I/usr/include/freetype2``
# and ``-I/usr/X11R6/include``.  Same-version re-declaration cannot conflict.
HEADER_DEPS = ("libxrender", "freetype", "xorgproto")
ALL_DEPS = LINK_DEPS + HEADER_DEPS


class SentConan(ConanFile):
    name = "sent"
    description = "Simple plaintext presentation tool for X11"
    license = "ISC"
    homepage = "https://tools.suckless.org/sent/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def set_version(self):
        # Conan 2 rejects one-character versions (RecipeReference.validate_ref
        # requires >= 2 chars), so the artifact version is normalized to the
        # upstream release label "v1" (release artefact: sent-1.tar.gz).  The
        # archive directory and the branch keep the task-card value "1"
        # (house pattern: cronic/v3, rapidhash/v3, cutmp3/4.0, dbskkd-cdb/3.00;
        # see archives/c/cronic/3/notes.md).
        self.version = "v1"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # sent links -lXft -lfontconfig -lX11 (see config.mk above).
        self.requires("libxft/2.3.9")
        self.requires("fontconfig/2.18.3")
        self.requires("libx11/1.8.13")
        # Build-time header providers, pinned exactly as libxft/libx11 pin
        # them, so the dependency graph stays a single consistent closure.
        self.requires("libxrender/0.9.12")
        self.requires("freetype/2.14.3")
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never by == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sent needs a POSIX X11 host, got os={self.settings.os}"
            )

    def source(self):
        # ``sent-1.tar.gz`` as published by dl.suckless.org is FLAT — the
        # archive root contains Makefile/config.mk/*.c directly, with no
        # ``sent-1/`` leading directory (verified with ``tar -tzf``).
        # Therefore ``strip_root=True`` must NOT be passed: conan raises
        # ConanException("Can't untar a tgz containing files in the root with
        # strip_root enabled") on the very first member.  Do not copy that
        # flag from the farbfeld recipe — farbfeld's tarball does have a root
        # directory because its own ``dist`` target creates one.
        get(self, **self.conan_data["sources"])

    def generate(self):
        AutotoolsToolchain(self).generate()
        VirtualBuildEnv(self).generate()

    # -- flag computation ---------------------------------------------------
    def _resolve_cc(self):
        # R33: the compiler comes from Conan's conf, never from a bare
        # ${CC} shell variable (empty on the release worker).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return (
            compilers.get("c")
            or shutil.which("clang")
            or shutil.which("cc")
            or "clang"
        )

    def _incdirs(self):
        # ``-I.`` mirrors upstream and is what lets sent.c find the generated
        # ``config.h`` plus arg.h/util.h/drw.h in the source root.
        found = ["-I."]
        for dep in ALL_DEPS:
            folder = self.dependencies[dep].package_folder
            for sub in ("include", os.path.join("include", "freetype2")):
                path = os.path.join(folder, sub)
                if os.path.isdir(path):
                    flag = "-I" + path
                    if flag not in found:
                        found.append(flag)
        return found

    def _libdirs(self):
        found = []
        for dep in ALL_DEPS:
            path = os.path.join(self.dependencies[dep].package_folder, "lib")
            if os.path.isdir(path) and path not in found:
                found.append(path)
        return found

    def _incs(self):
        return " ".join(self._incdirs())

    def _libs(self):
        # Order follows upstream LIBS: -lXft -lfontconfig -lX11, then -lm.
        # sent only *includes* Xrender/FreeType/xorgproto headers and calls no
        # symbol from them, so they are not linked; their .so arrive through
        # libXft's own DT_NEEDED.  All six deps default to shared=True, so no
        # extra -l for the transitive libraries is needed here.
        parts = ["-L" + d for d in self._libdirs()]
        parts += ["-lXft", "-lfontconfig", "-lX11", "-lm"]
        return " ".join(parts)

    def _make_var_overrides(self):
        return " ".join(
            [
                "CC=" + shlex.quote(self._resolve_cc()),
                "INCS=" + shlex.quote(self._incs()),
                "LIBS=" + shlex.quote(self._libs()),
            ]
        )

    # -- build / package ----------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        # R9: -j1 only.  env="conanbuild" contributes the toolchain CFLAGS /
        # LDFLAGS, which config.mk appends its own flags to.
        self.run(
            "make -j1 " + self._make_var_overrides(),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        # The upstream ``install`` target concatenates ``${DESTDIR}${PREFIX}``
        # and ``${DESTDIR}${MANPREFIX}`` with no separator, so the prefixes
        # must be handed over pre-joined:
        #   PREFIX=             -> ${DESTDIR}${PREFIX}/bin      == <pkg>/bin
        #   MANPREFIX=/share/man-> ${DESTDIR}${MANPREFIX}/man1  == <pkg>/share/man/man1
        # ``install: all`` re-runs the build first, hence the identical
        # variable overrides so the relink sees the same flags.
        self.run(
            "make install "
            + self._make_var_overrides()
            + " PREFIX= MANPREFIX=/share/man DESTDIR="
            + shlex.quote(self.package_folder),
            cwd=self.source_folder,
            env="conanbuild",
        )

        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        sent_bin = os.path.join(self.package_folder, "bin", "sent")
        if not os.path.isfile(sent_bin):
            raise RuntimeError(f"make install produced no binary at {sent_bin}")
        self._sign_elf(sent_bin)

    def _sign_elf(self, path):
        """OHOS kernel rejects unsigned ELF; self-sign in place."""
        if str(self.settings.os) != "OHOS":
            return
        signer = self._find_hnp_tool("binary-sign-tool")
        if not signer:
            self.output.warning("binary-sign-tool not found; skipping ELF signing")
            return
        objcopy = self._find_hnp_tool("llvm-objcopy")
        if objcopy:
            self.run(
                f"{shlex.quote(objcopy)} --remove-section .codesign "
                f"{shlex.quote(path)} 2>/dev/null || true",
                quiet=True,
            )
        signed = path + ".signed"
        self.run(
            f"{shlex.quote(signer)} sign -inFile {shlex.quote(path)} "
            f"-outFile {shlex.quote(signed)} -selfSign 1",
            quiet=True,
        )
        if os.path.isfile(signed):
            os.replace(signed, path)
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # HMDFS may ignore chmod (HMBS_CAP_CHMOD=0)

    @staticmethod
    def _find_hnp_tool(name):
        candidate = os.path.join("/data/service/hnp/bin", name)
        if os.path.isfile(candidate):
            return candidate
        return shutil.which(name)

    def package_info(self):
        # Command-line tool: only bin/ is meaningful (R38).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
