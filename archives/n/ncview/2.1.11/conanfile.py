#!/usr/bin/env python3
"""Conan recipe — ncview 2.1.11 for OHOS (HarmonyOS PC).

ncview is an X11/Athena-widget visual browser for netCDF files, built with
plain autotools. Its generated `configure` performs host-style discovery that
cannot succeed on OHOS, so build() rewrites the shipped configure (CI workers
have no autoreconf) and replaces each detection block with direct assignments,
baking dependency paths in as literals:

* AC_PATH_NETCDF   — hard-requires a runnable nc-config; replaced by direct
  -I/-L/-lnetcdf injection (the conan netcdf package does ship bin/nc-config,
  but its /bin/sh shebang and cache-path dependence make it fragile).
* AC_PATH_X / AC_PATH_XTRA — replaced by direct X11 path injection.
* Xaw/Xt link+header checks — replaced by direct -l injection.
* AC_PATH_PNG — replaced by direct injection; HAVE_PNG is defined so the
  -frames support compiles (src/Makefile.am hardcodes -lpng in ncview_LDADD,
  so libpng must always be linkable).
* AC_PATH_UDUNITS2 — replaced by direct injection of vendored libudunits2.
  NOTE: although configure presents udunits2 as optional, src/utCalendar2_cal.c
  unconditionally includes udunits2.h and references ut_* symbols, so the
  library is a hard compile/link dependency.

Vendored static libraries (no recipes exist on the ohpcd remote), built into a
private prefix inside the build folder (R49) and linked into the ncview
executable; none of them are packaged:
* libXext 1.3.7  — shape extension, required by libXmu (the remote libxext
                   packages pin libx11/6.4.0 which conflicts with libxt's
                   libx11/1.8.13, so it is vendored instead)
* libXpm  3.5.17 — pixmap loader required by Xaw7 (same remote libx11/6.4.0
                   pin problem, vendored for the same reason)
* libXmu  1.2.1  — required by Xaw7
* libXaw  1.0.16 — Athena widget set ncview's UI is built on
* udunits 2.2.28 — time units conversion

All configure scripts (ncview + 3 vendored) get the standard OHOS autotools
fixes: shebang rewrite, config.status "umask 077 && mktemp" → "umask 022 &&
mkdir" (HMDFS refuses writes inside 700-permission directories), and SHELL
fallback rewrites (agg 2.7.0.r145 pattern).
"""
import os
import re

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

_SOURCES = {
    # URL lists: conan tries them in order. Mirror hosts are byte-identical
    # distfiles re-hosts on domains proven reachable from restricted CI
    # workers (cirrus.ucsd.edu and downloads.unidata.ucar.edu time out there).
    "ncview-2.1.11": (
        [
            "https://distfiles.macports.org/ncview/ncview-2.1.11.tar.gz",
            "https://cirrus.ucsd.edu/~pierce/ncview/ncview-2.1.11.tar.gz",
        ],
        "597cfddf9c2d7993e9b0b86bca1b73839567ee9116ee33f6d750a449b5033d91",
    ),
    "libXext-1.3.7": (
        "https://xorg.freedesktop.org/archive/individual/lib/libXext-1.3.7.tar.xz",
        "6c643c7035cdacf67afd68f25d01b90ef889d546c9fcd7c0adf7c2cf91e3a32d",
    ),
    "libXmu-1.2.1": (
        "https://www.x.org/archive/individual/lib/libXmu-1.2.1.tar.xz",
        "fcb27793248a39e5fcc5b9c4aec40cc0734b3ca76aac3d7d1c264e7f7e14e8b2",
    ),
    "libXpm-3.5.17": (
        "https://www.x.org/archive/individual/lib/libXpm-3.5.17.tar.xz",
        "64b31f81019e7d388c822b0b28af8d51c4622b83f1f0cb6fa3fc95e271226e43",
    ),
    "libXaw-1.0.16": (
        "https://www.x.org/archive/individual/lib/libXaw-1.0.16.tar.xz",
        "731d572b54c708f81e197a6afa8016918e2e06dfd3025e066ca642a5b8c39c8f",
    ),
    "udunits-2.2.28": (
        [
            "https://mirrors.ustc.edu.cn/freebsd-ports/distfiles/udunits-2.2.28.tar.gz",
            "https://downloads.unidata.ucar.edu/udunits/2.2.28/udunits-2.2.28.tar.gz",
        ],
        "590baec83161a3fd62c00efa66f6113cec8a7c461e3f61a5182167e0cc5d579e",
    ),
}


def _fix_autotools_sh(text):
    """Standard OHOS fixes for autoconf-generated shell scripts (E165/HMDFS)."""
    text = text.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash")
    text = text.replace("#! /bin/bash", "#! /data/service/hnp/bin/bash")
    text = text.replace("#!/bin/sh", "#!/system/bin/sh")
    text = text.replace("#! /bin/sh", "#! /system/bin/sh")
    text = text.replace(
        "${CONFIG_SHELL-/bin/sh}", "${CONFIG_SHELL-/system/bin/sh}"
    )
    text = text.replace("${SHELL-/bin/sh}", "${SHELL-/system/bin/sh}")
    text = text.replace(
        "${SHELL-${CONFIG_SHELL-/bin/sh}}",
        "${SHELL-${CONFIG_SHELL-/system/bin/sh}}",
    )
    text = text.replace("SHELL = /bin/sh", "SHELL = /system/bin/sh")
    text = text.replace(
        '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
        '  test -d "$tmp"',
        "  tmp=./conf$$-$RANDOM\n"
        '  (umask 022 && mkdir "$tmp" && chmod 755 "$tmp")',
    )
    text = text.replace(
        '(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null',
        "(umask 022 && mkdir ./conf$$-$RANDOM && chmod 755 ./conf$$-$RANDOM)",
    )
    return text


def _replace_region(text, start_marker, end_marker, replacement):
    """Replace [start_marker, end_marker) with `replacement` (single pass)."""
    i = text.index(start_marker)
    j = text.index(end_marker, i + len(start_marker))
    return text[:i] + replacement + text[j:]


def _patch_ohos_config_scripts(root):
    """E007: teach config.guess/config.sub about HarmonyOS.

    Python port of the knowledge-base script patch-autotools-ohos.pl so the
    recipe stays self-contained for CI. config.guess gains a HarmonyOS case
    (uname -s = HarmonyOS) emitting aarch64-unknown-linux-ohos; config.sub
    gains the matching ohos-linux / ohos* / linux-ohos entries.
    """
    patched = []
    for dirpath, _, files in os.walk(root):
        if not {"config.guess", "config.sub"}.issubset(files):
            continue
        cg_path = os.path.join(dirpath, "config.guess")
        cs_path = os.path.join(dirpath, "config.sub")
        with open(cg_path, "r", encoding="utf-8") as f:
            cg = f.read()
        # Older config.guess (<=2019) builds its temp dir with
        # "umask 077 && mktemp -d"; mktemp -d creates mode-700 directories
        # *unconditionally* and HMDFS refuses writes inside them, which kills
        # the whole script. Replace with an umask-022 mkdir branch and relax
        # the remaining umask-077 fallbacks to 022 (755 dirs).
        cg = cg.replace(
            '(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX") 2>/dev/null',
            '(umask 022 && mkdir "$TMPDIR/cgXXXXXX.$$" && '
            'echo "$TMPDIR/cgXXXXXX.$$") 2>/dev/null',
        )
        cg = cg.replace("(umask 077 &&", "(umask 022 &&")
        if "__OHOS__" not in cg:
            cg, n = re.subn(
                r"(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                cg,
                count=1,
                flags=re.MULTILINE,
            )
        if "HarmonyOS" not in cg:
            # Two upstream styles exist: newer scripts assign GUESS and echo
            # it after the case; older ones (<=2019) echo+exit inside each
            # branch. Match the style, or the branch silently falls through
            # to the compiler-based fallback (which dies on OHOS).
            if re.search(r"echo[ \t]+\"\$GUESS\"|echo[ \t]+\$GUESS", cg):
                ohos_block = (
                    "    *:HarmonyOS:*:*)\n"
                    '\tcase "$UNAME_MACHINE" in\n'
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    i?86)         MACHINE=i686 ;;\n"
                    '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                    "\tesac\n"
                    "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                    "\t;;\n\n"
                )
            else:
                # Old-style scripts pair with pre-aarch64-ohos config.sub
                # variants that reject *-linux-ohos; emit the classic
                # linux-gnu triplet there instead (CC comes from the
                # environment either way, so configure behaves identically).
                ohos_block = (
                    "    *:HarmonyOS:*:*)\n"
                    '\tcase "$UNAME_MACHINE" in\n'
                    "\t    aarch64|arm64) echo aarch64-unknown-linux-gnu ;;\n"
                    "\t    armv7*|armv8*) echo arm-unknown-linux-gnu ;;\n"
                    "\t    x86_64|amd64)  echo x86_64-unknown-linux-gnu ;;\n"
                    '\t    *)             echo ${UNAME_MACHINE}-unknown-linux-gnu ;;\n'
                    "\tesac\n"
                    "\texit ;;\n\n"
                )
            cg, n = re.subn(
                r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)",
                lambda m: ohos_block + m.group(1),
                cg,
                count=1,
                flags=re.MULTILINE,
            )
        with open(cg_path, "w", encoding="utf-8") as f:
            f.write(cg)

        with open(cs_path, "r", encoding="utf-8") as f:
            cs = f.read()
        if "ohos-linux" not in cs:
            cs, n = re.subn(
                r"^(\s*android-linux\)\s*\n)"
                r"((\s*)basic_machine=\$field1-unknown\s*\n)"
                r"((\s*)basic_os=linux-android\s*\n)"
                r"(\s*;;\s*\n)",
                lambda m: (
                    m.group(1)
                    + m.group(2)
                    + m.group(4)
                    + m.group(6)
                    + "\tohos-linux)\n"
                    + m.group(3)
                    + "basic_machine=$field1-unknown\n"
                    + m.group(5)
                    + "basic_os=linux-ohos\n"
                    + m.group(6)
                ),
                cs,
                count=1,
                flags=re.MULTILINE,
            )
        if not re.search(r"gnu\*\s*\|\s*android\*\s*\|\s*ohos\*", cs):
            cs = re.sub(
                r"(gnu\*\s*\|\s*android\*)",
                r"\1 | ohos*",
                cs,
                count=1,
            )
        if "linux-ohos*)" not in cs:
            cs = re.sub(
                r"(linux-uclibc\*[/-]?\s*)\)",
                r"\1| linux-ohos*)",
                cs,
                count=1,
            )
        # New-style config.sub (>=2023) validates kernel-OS combinations in a
        # dedicated case; extend its linux family with linux-ohos. (Do not
        # guard on bare "linux-ohos": the ohos-linux triplet patch above
        # already introduces that string elsewhere.)
        if "linux-gnu* | linux-dietlibc* | linux-ohos*" not in cs:
            cs = cs.replace(
                "linux-gnu* | linux-dietlibc*",
                "linux-gnu* | linux-dietlibc* | linux-ohos*",
                1,
            )
        with open(cs_path, "w", encoding="utf-8") as f:
            f.write(cs)

        patched.append(os.path.relpath(dirpath, root))
    return patched


class NcviewConan(ConanFile):
    name = "ncview"
    version = "2.1.11"
    description = "Interactive visual browser for netCDF data files (X11/Athena widgets)"
    license = "GPL-3.0-or-later"
    homepage = "https://cirrus.ucsd.edu/~pierce/ncview/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe repo

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("netcdf/4.9.3")
        self.requires("libx11/1.8.13")
        self.requires("libxt/1.3.1")
        self.requires("xorgproto/2025.1")
        self.requires("libpng/1.6.58")
        self.requires("expat/2.8.2.1.1")

    def layout(self):
        basic_layout(self)

    # ------------------------------------------------------------------
    # dependency path helpers
    # ------------------------------------------------------------------
    def _dep_dir(self, ref, kind):
        dep = self.dependencies[ref]
        dirs = dep.cpp_info.includedirs if kind == "include" else dep.cpp_info.libdirs
        path = dirs[0]
        if not os.path.isabs(path):
            path = os.path.join(dep.package_folder, path)
        return path

    def generate(self):
        # Paths are resolved here and baked into configure as literals in
        # build(); valid for the duration of this build session.
        self._netcdf_inc = self._dep_dir("netcdf", "include")
        self._netcdf_lib = self._dep_dir("netcdf", "lib")
        self._png_inc = self._dep_dir("libpng", "include")
        self._png_lib = self._dep_dir("libpng", "lib")
        self._expat_inc = self._dep_dir("expat", "include")
        self._expat_lib = self._dep_dir("expat", "lib")
        self._x_incs = [
            self._dep_dir(r, "include")
            for r in ("libx11", "libxt", "xorgproto", "libxau", "libsm", "libice")
        ]
        self._x_libs = [
            self._dep_dir(r, "lib") for r in ("libx11", "libxt")
        ]
        self._x11_lib = self._x_libs[0]
        self._xt_lib = self._x_libs[1]

        tc = AutotoolsToolchain(self)
        tc.generate()

    def source(self):
        url, sha = _SOURCES["ncview-2.1.11"]
        get(self, url=url, sha256=sha, strip_root=True)
        vendor = os.path.join(self.source_folder, "vendor")
        for name in (
            "libXext-1.3.7",
            "libXmu-1.2.1",
            "libXpm-3.5.17",
            "libXaw-1.0.16",
            "udunits-2.2.28",
        ):
            url, sha = _SOURCES[name]
            get(
                self,
                url=url,
                sha256=sha,
                destination=os.path.join(vendor, name),
                strip_root=True,
            )

    # ------------------------------------------------------------------
    # configure rewriting
    # ------------------------------------------------------------------
    def _patch_ncview_configure(self, vendor_prefix):
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r", encoding="utf-8") as f:
            cfg = f.read()

        x_cflags = " ".join(f"-I{p}" for p in self._x_incs)
        x_cflags += f" -I{vendor_prefix}/include"
        x_libs = " ".join(f"-L{p}" for p in self._x_libs)
        x_libs += f" -L{vendor_prefix}/lib"

        cfg = _replace_region(
            cfg,
            "# Handle netcdf\n",
            "# For ncview-2.0, I've chosen to REQUIRE",
            f"""# Handle netcdf
# [OHOS adaptation] AC_PATH_NETCDF stripped: no PATH-visible nc-config here;
# the recipe injects netcdf flags directly.
NETCDF_CC="$CC"
NETCDF_LDFLAGS="-L{self._netcdf_lib} -lnetcdf"
NETCDF_CPPFLAGS="-I{self._netcdf_inc}"
NETCDF_VERSION="{self.version}"
NETCDF_V4="yes"
$as_echo "#define HAVE_NETCDF 1" >>confdefs.h
$as_echo "#define HAVE_NETCDF4 1" >>confdefs.h

""",
        )

        cfg = _replace_region(
            cfg,
            "# Check whether --with-x was given.",
            'if test "x$no_x" == "xyes"; then',
            f"""# Check whether --with-x was given.
# [OHOS adaptation] AC_PATH_X stripped: X11 comes from conan packages.
no_x=
X_CFLAGS="{x_cflags}"
X_LIBS="{x_libs}"
X_PRE_LIBS=""
X_EXTRA_LIBS=""

""",
        )

        cfg = _replace_region(
            cfg,
            'if test "$no_x" = yes; then',
            "#looking for Athena widgets",
            "# [OHOS adaptation] AC_PATH_XTRA stripped (paths injected above).\n\n",
        )

        cfg = _replace_region(
            cfg,
            "#looking for Athena widgets",
            "# Check for X11 library.",
            f"""#looking for Athena widgets
# [OHOS adaptation] Xaw/Xt detection stripped: libXaw7 + libXmu are vendored
# and built by this recipe; -L paths arrive via X_LIBS (ld collects -L globally).
XAW_LIBS="-lXaw7 -lXmu -lXpm -lXt -lXext"

""",
        )

        cfg = _replace_region(
            cfg,
            "# Check for X11 library.",
            "# Handle udunits2",
            """# Check for X11 library.
# [OHOS adaptation] stripped: direct injection.
X11_LIBS="-lX11"

""",
        )

        cfg = _replace_region(
            cfg,
            "# Handle udunits2\n",
            "# Handle png\n",
            f"""# Handle udunits2
# [OHOS adaptation] AC_PATH_UDUNITS2 stripped: vendored static libudunits2.
# HAVE_UDUNITS2 intentionally stays undefined (upstream's default-off for the
# udu.c helpers), but src/utCalendar2_cal.c hard-references ut_* symbols, so
# the link flags must always be present.
UDUNITS2_LDFLAGS="-L{vendor_prefix}/lib -ludunits2 -L{self._expat_lib} -lexpat"
UDUNITS2_CPPFLAGS="-I{vendor_prefix}/include"

""",
        )

        cfg = _replace_region(
            cfg,
            "# Handle png\n",
            "PREFIX=${prefix}",
            f"""# Handle png
# [OHOS adaptation] AC_PATH_PNG stripped: libpng comes from a conan package.
PNG_INCDIR="{self._png_inc}"
PNG_LIBDIR="{self._png_lib}"
PNG_CPPFLAGS="-I$PNG_INCDIR"
PNG_LIBS="-lpng"
PNG_LDFLAGS="-L$PNG_LIBDIR $PNG_LIBS"
$as_echo "#define HAVE_PNG 1" >>confdefs.h

PREFIX=${{prefix}}""",
        )

        # Drop the -Wl,-rpath loop: it would bake this build's absolute conan
        # cache paths into the installed binary.
        cfg = cfg.replace(
            '\tRPATH_FLAGS=""\n'
            "\tfor word in $UDUNITS2_LDFLAGS $NETCDF_LDFLAGS; do\n"
            "\t\tif test `expr $word : -L/` -eq 3; then\n"
            "\t\t\t#RPDIR=`expr substr $word 3 999`;\n"
            "\t\t\tRPDIR=${word:2}\n"
            '\t\t\tRPATH_FLAGS="$RPATH_FLAGS -Wl,-rpath,$RPDIR"\n'
            "\t\tfi\n"
            "\tdone",
            '\tRPATH_FLAGS=""',
        )

        cfg = _fix_autotools_sh(cfg)

        with open(configure_path, "w", encoding="utf-8") as f:
            f.write(cfg)

    # ------------------------------------------------------------------
    # vendored builds
    # ------------------------------------------------------------------
    def _run_in(self, workdir, command):
        self.run(command, cwd=workdir)

    def _build_vendored(self, vendor_prefix):
        vendor = os.path.join(self.source_folder, "vendor")
        xext_src = os.path.join(vendor, "libXext-1.3.7")
        xmu_src = os.path.join(vendor, "libXmu-1.2.1")
        xpm_src = os.path.join(vendor, "libXpm-3.5.17")
        xaw_src = os.path.join(vendor, "libXaw-1.0.16")
        ud_src = os.path.join(vendor, "udunits-2.2.28")

        for name in (xext_src, xmu_src, xpm_src, xaw_src, ud_src):
            configure_path = os.path.join(name, "configure")
            with open(configure_path, "r", encoding="utf-8") as f:
                cfg = f.read()
            with open(configure_path, "w", encoding="utf-8") as f:
                f.write(_fix_autotools_sh(cfg))

        # Keep the prebuilt texinfo docs "fresh" so make never invokes
        # makeinfo/mdate-sh (absent on OHOS).
        for doc in ("version.texi", "stamp-vti", "udunits2.info"):
            doc_path = os.path.join(ud_src, doc)
            if os.path.exists(doc_path):
                os.utime(doc_path, None)

        common_inc = " ".join(f"-I{p}" for p in self._x_incs)
        common_inc += f" -I{vendor_prefix}/include -I{self._expat_inc}"
        common_lib = " ".join(f"-L{p}" for p in self._x_libs)
        common_lib += f" -L{vendor_prefix}/lib -L{self._expat_lib}"
        common_ldpath = ":".join(list(self._x_libs) + [
            f"{vendor_prefix}/lib", self._expat_lib,
        ])

        # The conan X packages ship .la files whose dependency_libs reference
        # stale absolute cache paths from their original build machine; GNU
        # libtool chokes on them when resolving -l flags. Pass explicit
        # .so/.a file paths instead — libtool forwards them verbatim without
        # any .la lookup.
        x11_so = f"{self._x11_lib}/libX11.so"
        xt_so = f"{self._xt_lib}/libXt.so"
        vendor_a = f"{vendor_prefix}/lib"

        # The conan X packages ship .la files whose dependency_libs reference
        # stale absolute cache paths from their original build machine; GNU
        # libtool chokes on them when resolving -l flags. Pass explicit
        # .so/.a file paths instead - libtool forwards them verbatim without
        # any .la lookup.
        x11_so = f"{self._x11_lib}/libX11.so"
        xt_so = f"{self._xt_lib}/libXt.so"
        vendor_a = f"{vendor_prefix}/lib"

        env = Environment()
        env.define("CPPFLAGS", common_inc)
        env.define("LDFLAGS", common_lib)
        env.prepend_path("LD_LIBRARY_PATH", common_ldpath)
        # pkg-config override vars: skip pkg-config entirely (not available).
        env.define("XMU_CFLAGS", " ".join(f"-I{p}" for p in self._x_incs))
        env.define("XMU_LIBS", f"{vendor_a}/libXext.a {xt_so} {x11_so}")
        env.define("XAW7_CFLAGS", common_inc)
        env.define(
            "XAW7_LIBS",
            f"{vendor_a}/libXmu.a {vendor_a}/libXpm.a {xt_so} {x11_so}",
        )
        env.define(
            "XEXT_CFLAGS",
            " ".join(f"-I{p}" for p in self._x_incs),
        )
        env.define("XEXT_LIBS", x11_so)
        env.define("XPM_CFLAGS", " ".join(f"-I{p}" for p in self._x_incs))
        env.define("XPM_LIBS", x11_so)
        env.define("XMUU_CFLAGS", " ".join(f"-I{p}" for p in self._x_incs))
        env.define("XMUU_LIBS", x11_so)
        env.define("SXPM_CFLAGS", " ".join(f"-I{p}" for p in self._x_incs))
        env.define(
            "SXPM_LIBS",
            f"{vendor_a}/libXext.a {x11_so} {xt_so}",
        )

        with env.vars(self).apply():
            # libXext (shape extension): static, private prefix
            self._run_in(
                xext_src,
                f"./configure --prefix=\"{vendor_prefix}\" "
                "--disable-shared --enable-static --disable-dependency-tracking",
            )
            self._run_in(xext_src, "make -j1")
            self._run_in(xext_src, "make install")

            # libXmu: static, private prefix
            self._run_in(
                xmu_src,
                f"./configure --prefix=\"{vendor_prefix}\" "
                "--disable-shared --enable-static --disable-dependency-tracking",
            )
            self._run_in(xmu_src, "make -j1")
            self._run_in(xmu_src, "make install")

            # libXpm: static, private prefix
            self._run_in(
                xpm_src,
                f"./configure --prefix=\"{vendor_prefix}\" "
                "--disable-shared --enable-static --disable-dependency-tracking",
            )
            self._run_in(xpm_src, "make -j1")
            self._run_in(xpm_src, "make install")

            # libXaw (xaw7 only): static, private prefix
            self._run_in(
                xaw_src,
                f"./configure --prefix=\"{vendor_prefix}\" "
                "--disable-xaw6 --disable-shared --enable-static "
                "--disable-dependency-tracking",
            )
            self._run_in(xaw_src, "make -j1")
            self._run_in(xaw_src, "make install")

            # udunits2: static, private prefix (expat found via env).
            # MAKEINFO=true: automake wants to (re)build udunits2.info and
            # makeinfo does not exist on OHOS; the prebuilt .info ships in
            # the tarball and installs via VPATH.
            self._run_in(
                ud_src,
                f"./configure --prefix=\"{vendor_prefix}\" "
                "--disable-shared --enable-static --disable-dependency-tracking",
            )
            self._run_in(ud_src, "make -j1 MAKEINFO=true")
            # vti/info rebuilds during `make` can refresh version.texi and
            # leave the prebuilt .info stale-looking; re-touch so
            # `make install` never re-runs the (makeinfo) rule.
            for doc in ("version.texi", "stamp-vti", "udunits2.info"):
                doc_path = os.path.join(ud_src, doc)
                if os.path.exists(doc_path):
                    os.utime(doc_path, None)
            self._run_in(ud_src, "make install MAKEINFO=true")

    # ------------------------------------------------------------------
    # standard conan flow
    # ------------------------------------------------------------------
    def build(self):
        vendor_prefix = os.path.join(self.build_folder, "vendor-prefix")
        os.makedirs(vendor_prefix, exist_ok=True)

        # E007: config.guess/config.sub must recognize uname -s = HarmonyOS
        # (ncview + every vendored autotools tree).
        _patch_ohos_config_scripts(self.source_folder)

        self._build_vendored(vendor_prefix)
        self._patch_ncview_configure(vendor_prefix)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Ship the udunits XML database so time-axis conversion works at
        # runtime via UDUNITS2_XML_PATH (see notes.md).
        xml_src = os.path.join(self.build_folder, "vendor-prefix", "share", "udunits")
        if os.path.isdir(xml_src):
            copy(
                self,
                "*.xml",
                src=xml_src,
                dst=os.path.join(self.package_folder, "share", "udunits"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
