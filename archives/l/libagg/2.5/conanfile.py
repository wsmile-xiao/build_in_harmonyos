#!/usr/bin/env python3
"""Conan recipe — libagg 2.5 (Anti-Grain Geometry).

The official tarball (antigrain.com, now defunct; mirrored on BLFS)
only ships configure.in (no pre-generated configure). We therefore run
autoreconf LOCALLY (on a machine that has libtoolize/aclocal/automake)
and ship the result as plain text files under preconf/ in the recipe.
The CI buildbot worker lacks libtoolize/aclocal/automake, so it cannot
run autoreconf itself — this pre-generated configure lets CI build
without any host autotools toolchain. (The preconf products are
committed as text files, NOT as a tar.xz archive: binary patches are
rejected by CI checkout-pr and archive tarballs are forbidden in this
repo.)

Two fixes were applied before autoreconf (patches/0001-configure.ac.patch):
  - AM_PATH_SDL / PKG_CHECK_MODULES(FREETYPE) stripped: m4 macros /
    pkg-config not available on OHOS; all optional layers are disabled.
  - AC_ISC_POSIX / AM_C_PROTOTYPES / $U check removed: obsolete macros,
    fatal on automake 1.16+.

Upstream 2.5 predates -std=... defaults and modern C++ rules; two issues:
  - agg_renderer_outline_aa.h has a non-const profile() overload binding a
    non-const reference from a const pointer (ill-formed since C++11, error
    under modern clang). Patched via 0002.
  - agg_basics.h / agg_image_accessors.h / agg_trans_affine.h use the
    obsolete 'register' storage class (hard error in C++17). Also fixed in
    0002.
This is the standard distro patch set carried by every agg 2.5 packager
(Debian/Fedora/BLFS all carry equivalents).
"""
import os

from conan import ConanFile
from conan.tools.files import get, chdir, patch
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibAggConan(ConanFile):
    name = "libagg"
    version = "2.5"
    description = "Anti-Grain Geometry (AGG) 2.5 - high-quality 2D C++ rendering engine"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/agg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe repo

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Patches declared here (no conandata.yml) — avoids the CI
    # build_and_test.sh "Pre-download" BUILD_DIR crash.
    exports_sources = "patches/*", "preconf/*"

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Source url/sha256 hardcoded here (no conandata.yml) to avoid the CI
        # build_and_test.sh "Pre-download" stage crashing on an unset BUILD_DIR
        # variable. See commits 9b4660e5cf (iso-codes) / 1d55a9cccc (xmodem).
        # Official site www.antigrain.com is defunct (DNS no longer resolves);
        # BLFS mirror carries the byte-identical tarball (md5 0229a488bc47be10a2fee6cf0b2febd6
        # cross-checked against BLFS book + Fedora agg-2.5 source rpm).
        get(
            self,
            url="https://ftp.osuosl.org/pub/blfs/conglomeration/agg/agg-2.5.tar.gz",
            sha256="ab1edc54cc32ba51a62ff120d501eecd55fceeedf869b9354e7e13812289911f",
            strip_root=True,
        )
        # Overlay the pre-generated autoreconf products (configure,
        # aclocal.m4, ltmain.sh, Makefile.in (+ subdirs), config.{sub,guess},
        # compile, install-sh, missing, depcomp) on top of the tarball tree.
        # CI workers lack libtoolize/aclocal/automake, so they cannot
        # run autoreconf themselves. We generated these locally and
        # ship them as plain text files under preconf/ (recipe cache
        # via exports_sources -> self.export_sources_folder/preconf);
        # copy them (recursively) into the source tree.
        import shutil as _sh
        preconf_dir = os.path.join(self.export_sources_folder, "preconf")
        # The 2.5 tarball names its autoconf input configure.in, but the
        # preconf products were generated from the patched configure.ac —
        # automake's Makefile rules reference $(top_srcdir)/configure.ac.
        # Without the rename, make considers aclocal.m4 permanently out of
        # date (missing prerequisite) and recurses into am--refresh forever.
        src_cfg_in = os.path.join(self.source_folder, "configure.in")
        if os.path.isfile(src_cfg_in):
            os.rename(src_cfg_in, os.path.join(self.source_folder, "configure.ac"))
        # Enforce autotools timestamp ordering (configure.ac < aclocal.m4 <
        # configure < Makefile.in), else make believes configure/Makefile.in
        # must be regenerated and loops in am--refresh (no autotools on CI).
        import time as _time
        _base = _time.time() - 3600
        for _i, _rel in enumerate(
            ("configure.ac", "aclocal.m4", "inc/config.h.in", "configure")
        ):
            _p = os.path.join(preconf_dir, _rel)
            if os.path.isfile(_p):
                _t = _base + _i
                os.utime(_p, (_t, _t))
        for root, _, files in os.walk(preconf_dir):
            for f in files:
                if f == "Makefile.in":
                    _p = os.path.join(root, f)
                    _t = _base + 10
                    os.utime(_p, (_t, _t))
        for root, _, files in os.walk(preconf_dir):
            rel_root = os.path.relpath(root, preconf_dir)
            # preconf/inc -> include/（仓库 .gitignore 忽略 archives/**/include/，
            # 故 preconf 内 include 相关文件放 inc/ 目录，复制时映射回 include/）
            if rel_root == "inc" or rel_root.startswith("inc/"):
                rel_root = "include" + rel_root[3:]
            for f in files:
                src = os.path.join(root, f)
                dst_dir = self.source_folder if rel_root == "." else os.path.join(self.source_folder, rel_root)
                os.makedirs(dst_dir, exist_ok=True)
                dst = os.path.join(dst_dir, f)
                _sh.copy2(src, dst)
                # configure/config.sub/config.guess/install-sh etc. are
                # scripts — keep their executable bit.
                st = os.stat(src)
                if st.st_mode & 0o111:
                    os.chmod(dst, st.st_mode)

    def generate(self):
        # NOTE: keep AutotoolsToolchain default prefix="/". Conan's
        # Autotools.install() runs `make install DESTDIR=<package_folder>`,
        # which combined with a non-root prefix would nest the tree twice
        # (DESTDIR/prefix/...). With prefix=/ the layout is exactly
        # package_folder/{include,lib}.
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # AGG minimal build: disable all optional platform/font/gui layers
        tc.configure_args.append("--disable-examples")
        tc.configure_args.append("--disable-ctrl")
        tc.configure_args.append("--disable-platform")
        tc.configure_args.append("--disable-freetype")
        tc.configure_args.append("--disable-gpc")
        tc.generate()

    def build(self):
        # 0001-configure.ac.patch is already baked into the preconf
        # products (configure generated from the patched configure.ac);
        # 0002 is a source patch applied to the extracted tarball.
        patch(self, patch_file="patches/0002-const-profile-fix.patch")
        # HMDFS workaround: configure's generated config.status uses
        # `(umask 077 && mktemp -d "./confXXXXXX")` which creates a 700-permission
        # subdir; HMDFS refuses writes inside such dirs.
        # Pre-patch the configure template so the generated config.status uses
        # mkdir with umask 022 (775 perm) instead.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r", encoding="utf-8") as f:
                cfg = f.read()
            # E165: autoreconf-generated configure may use /bin/bash or
            # /bin/sh, neither of which exists on OHOS. Autoconf configure
            # scripts are POSIX-sh compatible, so use the target shell
            # consistently instead of depending on a CI-runner host path.
            # Handle both compact and spaced shebang forms.
            cfg = cfg.replace("#!/bin/bash", "#!/system/bin/sh")
            cfg = cfg.replace("#! /bin/bash", "#! /system/bin/sh")
            cfg = cfg.replace("#!/bin/sh", "#!/system/bin/sh")
            cfg = cfg.replace("#! /bin/sh", "#! /system/bin/sh")
            # Also fix SHELL=${CONFIG_SHELL-/bin/sh} fallbacks inside configure
            # (make invokes ${SHELL} which resolves to /bin/sh → exit 127).
            # autoconf emits several nested forms; replace them all.
            cfg = cfg.replace("${CONFIG_SHELL-/bin/sh}", "${CONFIG_SHELL-/system/bin/sh}")
            cfg = cfg.replace("${SHELL-/bin/sh}", "${SHELL-/system/bin/sh}")
            cfg = cfg.replace("${SHELL-${CONFIG_SHELL-/bin/sh}}", "${SHELL-${CONFIG_SHELL-/system/bin/sh}}")
            # Makefile.in templates set `SHELL = /bin/sh` (autoconf's @SHELL@)
            # — catch the literal assignment so make's SHELL doesn't fall back.
            cfg = cfg.replace("SHELL = /bin/sh", "SHELL = /system/bin/sh")
            orig = (
                '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
                '  test -d "$tmp"'
            )
            repl = (
                '  tmp=./conf$$-$RANDOM\n'
                '  (umask 022 && mkdir "$tmp" && chmod 755 "$tmp")'
            )
            cfg = cfg.replace(orig, repl)
            # Also catch the fallback mktemp path
            cfg = cfg.replace(
                '(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null',
                '(umask 022 && mkdir ./conf$$-$RANDOM && chmod 755 ./conf$$-$RANDOM)',
            )
            with open(configure_path, "w", encoding="utf-8") as f:
                f.write(cfg)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["agg"]
        # Headers install to include/agg2/ (upstream convention)
        self.cpp_info.includedirs = ["include"]
