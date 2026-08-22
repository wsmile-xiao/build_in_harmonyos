#!/usr/bin/env python3
"""Conan recipe — agg 2.7.0.r145 (Anti-Grain Geometry).

The dfsg orig tarball only ships configure.ac (no pre-generated
configure). We therefore run autoreconf LOCALLY (on a machine that
has libtoolize/aclocal/automake) and ship the result as plain text
files under preconf/ in the recipe. The CI buildbot worker lacks
libtoolize/aclocal/automake, so it cannot run autoreconf itself —
this pre-generated configure lets CI build without any host autotools
toolchain. (The preconf products are committed as text files, NOT as
a tar.xz archive: binary patches are rejected by CI checkout-pr and
archive tarballs are forbidden in this repo.)

SDL/FT2 autodetection macros are stripped from configure.ac via
patch (AM_PATH_SDL / PKG_CHECK_MODULES not available on OHOS); all
optional layers are disabled.
"""
import os

from conan import ConanFile
from conan.tools.files import get, chdir, patch
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AggConan(ConanFile):
    name = "agg"
    version = "2.7.0.r145"
    description = "Anti-Grain Geometry (AGG) - high-quality 2D C++ rendering engine"
    license = "BSD-3-Clause"
    homepage = "https://sourceforge.net/projects/agg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe repo

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Patches declared here (no conandata.yml) — avoids the CI
    # build_and_test.sh "Pre-download" BUILD_DIR crash.
    exports_sources = "patches/*", "preconf/*"
    # Ship the pre-generated autoreconf products (configure, aclocal.m4,
    # ltmain.sh, Makefile.in, config.{sub,guess}, install-sh, missing,
    # depcomp) as plain text files under preconf/. CI workers lack
    # libtoolize/aclocal/automake, so they cannot run autoreconf
    # themselves. (Do NOT pack them into a tar.xz: binary patches are
    # rejected by CI checkout-pr and archive tarballs are forbidden.)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Source url/sha256 hardcoded here (no conandata.yml) to avoid the CI
        # build_and_test.sh "Pre-download" stage crashing on an unset BUILD_DIR
        # variable. See commits 9b4660e5cf (iso-codes) / 1d55a9cccc (xmodem).
        get(
            self,
            url="https://sources.voidlinux.org/agg-2.7.0.r145/agg_2.7.0.r145+dfsg.orig.tar.xz",
            sha256="b7181085d3c06166a972211cd17741cc5429adc7c1f58e4d528206f7208e6328",
            strip_root=True,
        )
        # Overlay the pre-generated autoreconf products (configure,
        # aclocal.m4, ltmain.sh, Makefile.in (+ subdirs), config.{sub,guess},
        # compile, install-sh, missing, depcomp) on top of the dfsg tree.
        # CI workers lack libtoolize/aclocal/automake, so they cannot
        # run autoreconf themselves. We generated these locally and
        # ship them as plain text files under preconf/ (recipe cache
        # via exports_sources -> self.export_sources_folder/preconf);
        # copy them (recursively) into the source tree.
        import shutil as _sh
        preconf_dir = os.path.join(self.export_sources_folder, "preconf")
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
                _sh.copyfile(src, dst)
                # configure/config.sub/config.guess/install-sh etc. are
                # scripts — keep their executable bit.
                st = os.stat(src)
                if st.st_mode & 0o111:
                    os.chmod(dst, st.st_mode)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
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
        # 0001-configure.ac.patch already applied to the preconf tarball
        # (PKG_CHECK_MODULES/FREETYPE and AM_PATH_SDL removed before
        # autoreconf). No need to re-apply here.
        # HMDFS workaround: configure's generated config.status uses
        # `(umask 077 && mktemp -d "./confXXXXXX")` which creates a 700-permission
        # subdir; HMDFS refuses writes inside such dirs.
        # Pre-patch the configure template so the generated config.status uses
        # mkdir with umask 022 (775 perm) instead.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r", encoding="utf-8") as f:
                cfg = f.read()
            # E165: autoreconf-generated configure shebang is #!/bin/bash or
            # #!/bin/sh — neither exists on OHOS. Rewrite to the real paths.
            # Note: autoconf emits "#! /bin/sh" (with a space); handle both.
            cfg = cfg.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash")
            cfg = cfg.replace("#! /bin/bash", "#! /data/service/hnp/bin/bash")
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
