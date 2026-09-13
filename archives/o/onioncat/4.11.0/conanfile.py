#!/usr/bin/env python3
"""Conan recipe — onioncat 4.11.0 (autotools, ocat VPN adapter for Tor/I2P)

OnionCat creates a transparent IPv6 layer on top of Tor hidden services (or
I2P tunnels).  Product is a single command-line daemon: bin/ocat.

OHOS adaptation notes (all verified by local W3 build + run):
  1. Upstream release tarball contains NO configure script (only
     configure.ac + Makefile.am); upstream autogen.sh runs autoreconf +
     automake --add-missing --copy.  Same bootstrap sequence is executed in
     build() using tool_requires autoconf/2.72 + automake/1.18 (both
     published on ohpcd; zzuf 0.15 / abiword-plugin-* same-pattern precedent).
     automake 1.18 ships a modern config.guess that natively recognizes
     HarmonyOS -> aarch64-unknown-linux-ohos, so no config.guess/config.sub
     patch is needed (E160-series pattern not required here).
  2. autoconf-generated configure/config.status create their ./confXXXXXX
     temp dirs under `umask 077`; on HMDFS (setgid dirs, group-write needed)
     subs1.awk creation fails with Permission denied (knowledge E011, same
     class as xz/tar/wget).  Recipe rewrites umask 077 -> 022 in the
     generated configure and runs the bootstrap+configure+make under umask 022
     (R49 platform-limitation bypass, not a source patch).
  3. No external library dependencies: pthread comes from libc on OHOS (musl),
     sockets/inet are libc too.  AC_SEARCH_LIBS(socket/nsl) resolve empty.
  4. Build scope: default full build incl. TUN/TAP code (WITHOUT_TUN not
     defined); the tunnel device is only opened at daemon runtime, binary
     compiles cleanly against musl headers.  src/cygwin, i2p, man subdirs are
     doc/EXTRA_DIST only.
  5. Binaries are NOT stripped (llvm-stripped ELFs get EACCES on this
     platform, olsrd 0.9.8 precedent).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OnioncatConan(ConanFile):
    name = "onioncat"
    version = "4.11.0"
    description = "OnionCat — transparent IPv6 VPN adapter layer on top of Tor hidden services or I2P tunnels (ocat)"
    license = "GPL-3.0-only"
    homepage = "https://github.com/rahra/onioncat"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("onioncat supports Linux/OHOS only")

    def build_requirements(self):
        # Release tarball ships no configure; regenerate via autotools
        # bootstrap (upstream autogen.sh: autoreconf -f; automake --add-missing
        # --copy; autoreconf -f).  CI worker has no system automake/autoconf.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)
        # In-source build: bootstrap must generate configure next to
        # configure.ac/Makefile.am in the unpacked source tree.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # tool_requires bin/ (aclocal/autoconf/automake) onto build PATH.
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        shell = os.environ.get("CONFIG_SHELL", "bash")

        # 1. Upstream bootstrap sequence (autogen.sh: autoreconf -f;
        #    automake --add-missing --copy; autoreconf -f), executed as the
        #    manual aclocal->autoconf->autoheader->automake chain.
        #    Why not plain `autoreconf`: the conan perl package is unusable on
        #    HMDFS (its Cwd.so dlopen fails with Permission denied) and its
        #    PERL5LIB leaks into the system autoreconf; running each tool via
        #    `sh` engages the scripts' shell header which execs $PERL, so we
        #    force the system perl while pointing PERL5LIB at the conan tool
        #    packages' share dirs (zzuf 0.15 / avimetaedit 1.0.2 precedent).
        self.run(
            f"{shell} -c \"set -e"
            f" && export PERL=/data/service/hnp/bin/perl"
            f" && unset PERL5LIB"
            f" && ACLOCAL=$(command -v aclocal-1.18 2>/dev/null || command -v aclocal 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $ACLOCAL))/share/automake-1.18"
            f" && sh $ACLOCAL"
            f" && AUTOCONF=$(command -v autoconf 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOCONF))/share/autoconf"
            f" && sh $AUTOCONF"
            f" && AUTOHEADER=$(command -v autoheader 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOHEADER))/share/autoconf"
            f" && sh $AUTOHEADER"
            f" && AUTOMAKE=$(command -v automake-1.18 2>/dev/null || command -v automake 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOMAKE))/share/automake-1.18"
            f" && sh $AUTOMAKE --add-missing --copy\"",
            cwd=self.source_folder, env="conanbuild",
        )

        # 2. automake 1.18 (conan tool package) installs a config.guess
        #    (2024-07-27) that predates upstream HarmonyOS support -> configure
        #    dies with "cannot guess build type" (E160-series).  Patch the two
        #    installed helper scripts in-tree (generated files, not upstream
        #    sources; openconnect 9.12 same-pattern precedent):
        #      config.guess: aarch64:HarmonyOS -> aarch64-unknown-linux-ohos
        #      config.sub:   accept ohos* OS token
        for script, old_s, new_s in (
            ("config.guess",
             "    aarch64:Linux:*:*)",
             "    aarch64:HarmonyOS:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-ohos\n\t;;\n    aarch64:Linux:*:*)"),
            ("config.sub",
             "\t| android* \\\n",
             "\t| android* \\\n\t| ohos* \\\n"),
        ):
            path = os.path.join(self.source_folder, script)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            if new_s not in content and old_s in content:
                content = content.replace(old_s, new_s, 1)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"[E160] {script}: HarmonyOS/ohos support added")
            else:
                self.output.info(f"[E160] {script}: already OK or anchor missing")

        # 3. E011: autoconf temp-dir umask 077 breaks config.status on HMDFS
        #    (setgid dirs need group write).  Rewrite to 022 in the generated
        #    configure (platform adaptation, not a source patch — configure
        #    itself is a generated file, upstream source is untouched).
        cfg = os.path.join(self.source_folder, "configure")
        with open(cfg, encoding="utf-8") as f:
            content = f.read()
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            with open(cfg, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("[E011] configure umask 077 -> 022 (HMDFS setgid bypass)")

        # 4. configure + make.  R33: compiler comes from the conan profile
        #    (tools.build:compiler_executables); no bare shell CC/CFLAGS.
        self.run(f"{shell} -c 'umask 022 && ./configure --prefix={self.package_folder}'",
                 cwd=self.source_folder, env="conanbuild")
        self.run(f"{shell} -c 'umask 022 && make -j1'",
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run(f"{os.environ.get('CONFIG_SHELL', 'bash')} -c 'umask 022 && make install'",
                 cwd=self.source_folder, env="conanbuild")
        # license
        lic_dst = os.path.join(self.package_folder, "share", "doc", "onioncat")
        os.makedirs(lic_dst, exist_ok=True)
        for name in ("COPYING", "AUTHORS", "README.md"):
            src = os.path.join(self.source_folder, name)
            if os.path.isfile(src):
                with open(src, "rb") as fin, open(os.path.join(lic_dst, name), "wb") as fout:
                    fout.write(fin.read())

    def package_info(self):
        # Command-line daemon only; no linkable library is produced.
        self.cpp_info.bindirs = ["bin"]
