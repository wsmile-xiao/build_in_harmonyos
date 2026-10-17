#!/usr/bin/env python3
"""Conan recipe for radlib - Rapid Application Development library (Mark Teel).

Autotools project (C). The official 2.12.0 release tarball (SourceForge,
the project's distribution site; the GitHub mirror tag only contains a
stray 2014 dbtest snapshot - see notes.md) carries a 1999-era configure
paired with a Debian libtool-2.4 ltmain.sh: configure generates a
syntactically broken libtool script on the OHOS toolchain, so the
autotools tree is regenerated before building. CI availability notes:
- CI workers ship hnp autoconf + a working perl but no automake, and the
  conan-packaged perl is unusable on OHOS (broken Cwd.so), so automake
  and libtool are bootstrapped from their official GNU release tarballs
  (conandata build_tools) into a private build-time prefix.
Upstream test assets: test/ ships 5 standalone test programs (sha,
multicast, msgRouter, database, sqlite) that are NOT registered in
automake (EXTRA_DIST only). The sha test is compiled against the built
library and executed for real inside build(); the other four need
interactive daemons or optional database backends and are documented as
per-case skips in notes.md/MANIFEST.yml. A consumer program in
test_package additionally covers the exported API (radCRC32/radCRC16 and
the SHA-1/SHA-256 FIPS vectors).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, replace_in_file, rm, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RadlibConan(ConanFile):
    name = "radlib"
    version = "2.12.0"
    description = "radlib rapid application development library (event-driven process framework, messaging, sockets) with radmrouted/raddebug tools"
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/radlib/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        # Required by the recipe-completeness gate even with an empty patch set.
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # automake + libtool release tarballs for the build-time autotools
        # bootstrap (see module docstring); official GNU releases.
        for name, meta in self.conan_data["build_tools"].items():
            get(self, **meta, destination=os.path.join("_tools", name),
                strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The configure macros (AC_PROG_LIBTOOL) need a canonical build type;
        # config.guess cannot recognize an OHOS host (E007). The bundled
        # (pre-regeneration) config.sub only accepts gnu-suffixed triplets,
        # so pass gnu-form triplets with host == build (native semantics;
        # runtime probes execute natively on the OHOS device/worker).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # mysql/postgresql/sqlite support stays off (upstream defaults);
        # base library only needs libc/libm (configure AC_CHECK_LIB).
        tc.generate()

    def build(self):
        # radqueue.c ships with CRLF line endings; normalize to LF first so
        # the source edits below stay line-exact (sources-only change).
        rq = os.path.join(self.source_folder, "src", "radqueue.c")
        with open(rq, "rb") as f:
            data = f.read()
        if b"\r\n" in data:
            with open(rq, "wb") as f:
                f.write(data.replace(b"\r\n", b"\n"))
        apply_conandata_patches(self)
        src = self.source_folder
        # Refresh the autotools machinery: obsolete macro (removed in
        # automake >= 1.13) and the deprecated two-argument form of
        # AM_INIT_AUTOMAKE must be modernized before autoreconf accepts
        # the project (sources-only changes, semantics preserved).
        replace_in_file(self, os.path.join(src, "configure.in"),
                        "AM_CONFIG_HEADER([config.h])",
                        "AC_CONFIG_HEADER([config.h])")
        replace_in_file(self, os.path.join(src, "configure.in"),
                        "AM_INIT_AUTOMAKE([radlib],[2.12.0])",
                        "AM_INIT_AUTOMAKE([foreign])")
        # radqueue.c uses open()/O_RDWR without <fcntl.h> (musl has no
        # transitive include; clang 15 errors on implicit declarations).
        replace_in_file(self, rq,
                        "#include <stdio.h>",
                        "#include <fcntl.h>\n#include <stdio.h>", 1)

        # Bootstrap automake/libtool from their GNU release tarballs into a
        # private prefix (see module docstring: workers lack host automake
        # and conan perl is broken on OHOS). Release tarballs configure and
        # install as plain perl/script packages (no compilation). Their
        # configure files get the same HMDFS shell/E386 treatment as the
        # main configure below.
        tools_prefix = os.path.join(self.build_folder, "_tools_prefix")
        for name in ("automake", "libtool"):
            tool_src = os.path.join(src, "_tools", name)
            self._patch_configure_hmdfs(tool_src)
            # --build skips config.guess, whose compiler probe cannot write
            # into an mktemp dir under HMDFS (E011 variant); gnu triplet is
            # accepted by the modern bundled config.sub.
            self.run('env -u PERL5LIB -u PERLLIB -u PERL5OPT -u CONFIG_SHELL -u SHELL '
                     'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh configure '
                     '--prefix="%s" --build=aarch64-unknown-linux-gnu'
                     % tools_prefix, cwd=tool_src, env="conanbuild")
            self.run('env -u PERL5LIB -u PERLLIB -u PERL5OPT -u CONFIG_SHELL -u SHELL '
                     'CONFIG_SHELL=/bin/sh SHELL=/bin/sh make install MAKEINFO=true',
                     cwd=tool_src, env="conanbuild")

        # Regenerate configure/Makefile.in/libtool with the bootstrapped
        # autotools. The conan-packaged perl fails on OHOS (Cwd.so
        # relocation error) and the host stack may lack aclocal, so prepend
        # the private prefix to PATH for this call only.
        self.run('env -u PERL5LIB -u PERLLIB -u PERL5OPT -u CONFIG_SHELL -u SHELL '
                 'PATH="%s/bin:$PATH" autoreconf -fi' % tools_prefix,
                 cwd=src, env="conanbuild")
        self._patch_configure_hmdfs(src)
        # conan's Autotools.configure() cannot pass env, and autoconf would
        # otherwise pick the hnp bash from PATH (profile buildenv order);
        # that bash's getcwd() fails under HMDFS build dirs (E386), so
        # config.status loses its cwd and emits the generated Makefiles
        # into a leftover conftest.dir. Pin the shell for configure (and
        # thus the generated config.status) to /bin/sh instead (AGENTS
        # 适配经验汇总 §12.38 first-choice shell routing).
        conf_args = ["--prefix=/",
                     "--bindir=${prefix}/bin", "--sbindir=${prefix}/sbin",
                     "--libdir=${prefix}/lib", "--includedir=${prefix}/include",
                     "--oldincludedir=${prefix}/include",
                     "--build=aarch64-unknown-linux-gnu",
                     "--host=aarch64-unknown-linux-gnu",
                     "--enable-static", "--disable-shared"]
        quoted = " ".join("'%s'" % a for a in conf_args)
        self.run('env CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "%s" %s'
                 % (os.path.join(src, "configure"), quoted),
                 cwd=self.build_folder, env="conanbuild")
        autotools = Autotools(self)
        autotools.make(args=["-j1"])
        # Upstream has no automake-registered tests (test/ is EXTRA_DIST),
        # so `make check` recurses with no test programs and passes as a
        # no-op; executed anyway as the canonical upstream test entry point.
        autotools.make(target="check")
        # Upstream test execution: test/ holds 5 standalone programs that
        # automake never registers. The sha test is self-contained and
        # offline-runnable: compile it against the built library and run
        # both modes for real; a nonzero exit or a malformed digest fails
        # the build. The other four programs need interactive daemons
        # (msgRouter) or optional database backends (database/sqlite) and
        # an endless RX/TX loop (multicast) - per-case ledger in notes.md
        # and test_package/MANIFEST.yml.
        cc = "clang"
        try:
            exe = self.conf.get("tools.build:compiler_executables")
            if isinstance(exe, dict) and exe.get("c"):
                cc = exe["c"]
        except Exception:
            pass
        liba = os.path.join(self.build_folder, "src", ".libs", "librad.a")
        inc = os.path.join(src, "h")
        tsrc = os.path.join(src, "test", "sha", "radsha.c")
        self.run('printf "radlib upstream sha test data 2026-09-19\\n" > sha_input.txt',
                 cwd=self.build_folder, env="conanbuild")
        self.run('"%s" -I"%s" -D_GNU_SOURCE "%s" "%s" -lm -o radsha_test'
                 % (cc, inc, tsrc, liba), cwd=self.build_folder, env="conanbuild")
        self.run('./radsha_test 256 sha_input.txt > sha256_out.txt 2>&1',
                 cwd=self.build_folder, env="conanbuild")
        with open(os.path.join(self.build_folder, "sha256_out.txt")) as f:
            out256 = f.read()
        if not re.search(r"[0-9a-f]{64}", out256):
            raise ConanException("upstream sha test: malformed SHA-256 digest: %s" % out256)
        self.run('./radsha_test 1 sha_input.txt > sha1_out.txt 2>&1',
                 cwd=self.build_folder, env="conanbuild")
        with open(os.path.join(self.build_folder, "sha1_out.txt")) as f:
            out1 = f.read()
        if not re.search(r"[0-9a-f]{40}", out1):
            raise ConanException("upstream sha test: malformed SHA-1 digest: %s" % out1)

    def _patch_configure_hmdfs(self, src):
        """HMDFS fixes applied at build time (mifluz/0.26.0 same pattern).

        - umask 077 temp dirs created by config.status are not writable on
          HMDFS (E011) -> drop the umask wrapper, keep mktemp -d.
        - ac_pwd=`pwd` and the `ls -di .` sanity check fail when the HMDFS
          FUSE layer rejects getcwd() (E386) -> fall back to $PWD.
        """
        path = os.path.join(src, "configure")
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        content = content.replace(
            "(umask 077 && mktemp -d \"./confXXXXXX\") 2>/dev/null",
            "(mktemp -d \"./confXXXXXX\") 2>/dev/null",
        )
        content = content.replace(
            "(umask 077 && mkdir \"$tmp\")",
            "mkdir \"$tmp\"",
        )
        content = content.replace(
            "ac_pwd=`pwd`",
            "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"",
        )
        content = content.replace(
            "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\" 2>/dev/null || ac_pwd=\"$PWD\"",
            "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"",
        )
        content = content.replace(
            "ac_pwd_ls_di=`cd \"$ac_pwd\" && ls -di .` ||",
            "ac_pwd_ls_di=`cd \"$ac_pwd\" && ls -di . 2>/dev/null` || ac_pwd_ls_di=\"$ac_pwd\" ||",
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # radlib's automake does not install the public headers in h/;
        # that directory IS the library API (radlist.h, radmsgLog.h,
        # radsha.h, ...), so ship it from the package step.
        copy(self, "*.h", src=os.path.join(self.source_folder, "h"),
             dst=os.path.join(self.package_folder, "include"))
        # Conan packages don't ship libtool archives.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["rad"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
