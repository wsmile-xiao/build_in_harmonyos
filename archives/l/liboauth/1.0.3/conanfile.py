#!/usr/bin/env python3
"""Conan recipe for liboauth 1.0.3 (autotools).

liboauth — C library implementing OAuth 1.0 signature generation and
verification (HMAC-SHA1 / RSA-SHA1 / plaintext). Upstream:
https://github.com/x42/liboauth (tag v1.0.3).

Adaptation notes (HarmonyOS OHOS aarch64):
- Upstream tag tarball ships no generated `configure` (only configure.ac),
  so build() must bootstrap via aclocal/autoheader/autoconf/automake.
  automake/libtool are pulled in as tool_requires (published in ohpcd).
- hash.c used pre-OpenSSL-1.1 stack-allocated EVP_MD_CTX
  (EVP_MD_CTX_init/EVP_MD_CTX_cleanup), removed in OpenSSL 1.1+. Patch
  0001 migrates all four call sites to EVP_MD_CTX_new/EVP_MD_CTX_free
  (compatible with both OpenSSL 1.1.1 and 3.x).
- OHOS hmdfs: config.status creates ./confXXXXXX with `umask 077`, and a
  mode-0700 dir under the setgid hmdfs mount is not writable by the
  build user (local + CI reproduced; same family as E114 / a52dec 0002).
  The generated configure is patched to use umask 022, matching the
  a52dec-0.7.4 precedent.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LiboauthConan(ConanFile):
    name = "liboauth"
    version = "1.0.3"
    description = "C library implementing OAuth 1.0 signature generation and verification"
    license = "MIT"
    homepage = "http://liboauth.sourceforge.net/"
    url = "https://github.com/x42/liboauth"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # hash.c links libcrypto for HMAC-SHA1 / RSA-SHA1 and body hash
        self.requires("openssl/1.1.1w")

    def build_requirements(self):
        # git tag tarball has no generated configure; automake/libtool are
        # needed to bootstrap. Published in ohpcd (see abiword-plugin-*
        # precedents). autoconf/autoheader live in hnp/bin (build profile PATH).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # tool_requires binaries are injected via buildenv (ACLOCAL/AUTOMAKE/
        # LIBTOOLIZE env vars), not bare PATH — see abiword-plugin-docbook.
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries -> static (this library is not a system
        # name; keep shared option but default to static like the template)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # E007/OHOS: config.guess cannot recognize "HarmonyOS" (uname -s) and
        # its scratch writes are rejected on HMDFS ("dummy.c: Permission
        # denied"). Pass explicit --build/--host to skip the guess (same as
        # abiword-plugin-docbook).
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-linux")
            tc.configure_args.append("--host=aarch64-linux")
        # Point OpenSSL headers/libs at the conan dependency
        if "openssl" in self.dependencies:
            dep = self.dependencies["openssl"]
            incs = dep.cpp_info.includedirs
            libs = dep.cpp_info.libdirs
            if incs:
                tc.configure_args.append("CPPFLAGS={}".format(
                    " ".join("-I{}".format(i) for i in incs)))
            if libs:
                tc.configure_args.append("LDFLAGS={}".format(
                    " ".join("-L{}".format(i) for i in libs)))
        tc.generate()

    def _run_autogen(self):
        """Bootstrap configure from configure.ac (no pre-generated configure).

        Direct aclocal/autoconf/autoheader/automake chain: the tool_requires
        inject $ACLOCAL/$AUTOMAKE/$LIBTOOLIZE into the conanbuild env, and
        libtool.m4 is exported to source_folder/m4 (AC_CONFIG_MACRO_DIR).
        configure.ac uses AC_PROG_LIBTOOL, so ltmain.sh must be pulled from
        the libtool tool_requires before automake runs (same pattern as
        abiword-plugin-docbook).
        """
        self.output.info("Bootstrapping configure (aclocal/autoconf/autoheader/automake)...")
        self.run('"${ACLOCAL:-aclocal}" --force',
                 cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        self.run('"${AUTOCONF:-autoconf}"',
                 cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        self.run('"${AUTOHEADER:-autoheader}"',
                 cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        # ltmain.sh must be present before automake, otherwise automake fails
        # with "required file './ltmain.sh' not found" and no Makefile.in.
        _ltmain = os.path.join(self.source_folder, "ltmain.sh")
        if not os.path.exists(_ltmain):
            self.run(
                'lt="$LIBTOOLIZE"; '
                'if [ -n "$lt" ] && [ -f "$lt" ]; then '
                '  srcdir="$(cd "$(dirname "$(dirname "$lt")")" && pwd)"; '
                '  src="$srcdir/share/libtool/build-aux/ltmain.sh"; '
                '  [ -f "$src" ] && cp "$src" ltmain.sh && echo "  [ok] Copied ltmain.sh via LIBTOOLIZE env"; '
                'fi',
                cwd=self.source_folder,
                env="conanbuild",
                ignore_errors=True,
            )
            # fallback: tool_requires package_folder
            if not os.path.exists(_ltmain):
                try:
                    _lt_pkg = self.dependencies["libtool"].package_folder
                    if _lt_pkg:
                        _cand = os.path.join(_lt_pkg, "share", "libtool", "build-aux", "ltmain.sh")
                        if os.path.exists(_cand):
                            shutil.copy(_cand, _ltmain)
                            self.output.info("  [ok] Copied ltmain.sh from tool_requires libtool")
                except Exception:
                    pass
        rc = self.run('"${AUTOMAKE:-automake}" --add-missing --copy --foreign',
                      cwd=self.source_folder, env="conanbuild", ignore_errors=True)
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            raise ConanException("autogen failed: configure not generated")
        return rc

    def _fix_config_status_umask(self):
        """OHOS hmdfs: config.status tmp dir created under umask 077 (mode
        0700) is not writable by the build user on the setgid hmdfs mount,
        which aborts configure ("can't create ./confXXXXXX/subs1.awk:
        Permission denied"). Patch the generated configure to use umask 022
        (same fix as a52dec 0002-configure-umask-022.patch).
        """
        cfg = os.path.join(self.source_folder, "configure")
        with open(cfg, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if "(umask 077 && mktemp -d" not in text:
            raise ConanException("E114-family: umask 077 pattern not found in configure")
        text = text.replace("(umask 077 && mktemp -d", "(umask 022 && mktemp -d")
        text = text.replace("(umask 077 && mkdir", "(umask 022 && mkdir")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(cfg, 0o755)
        self.output.info("  [ok] patched configure: config.status tmp dir umask 077 -> 022")

    def build(self):
        self._run_autogen()
        self._fix_config_status_umask()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # E232: native OHOS (settings_build.os == "OHOS")源位置拒绝直接执行
        # configure 脚本（Permission denied exit 126，Conan 报 autotools.configure
        # traceback）。仅 native 构建用 /system/bin/sh 前缀执行 configure，
        # 其余平台（含交叉构建）保持 autotools.configure()。
        if str(self.settings_build.os) == "OHOS":
            configure = os.path.join(self.source_folder, "configure")
            args = autotools._configure_args
            if not isinstance(args, str):
                args = " ".join(args)
            self.run('/system/bin/sh "{0}" {1}'.format(configure, args),
                     cwd=self.build_folder)
        else:
            autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["oauth"]
        self.cpp_info.system_libs = ["m"]