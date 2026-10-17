#!/usr/bin/env python3
"""Conan recipe for libkcapi-tools 1.5.0 — kernel crypto API command line tools.

Same-source subpackage of libkcapi (precedent: libfreeaptx-tools,
libjwt-tools, babl-tools): ships only the four upstream user space tools
from the apps/ directory:

    kcapi-dgst    message digest helper (apps/kcapi-dgst.c)
    kcapi-enc     symmetric encryption/decryption helper (apps/kcapi-enc.c)
    kcapi-rng     random number generator helper (apps/kcapi-rng.c)
    kcapi-hasher  FIPS style checksum helper (apps/kcapi-hasher.c)

Upstream Makefile.am links every app against the in-tree libkcapi.la and
the conan toolchain builds that library statically, so each shipped
binary is self-contained (DT_NEEDED: libc.so only).  The library itself,
its public header and the pkg-config file stay owned by the libkcapi
package - no file has two owners; this package therefore declares no
requirements().

Note on runtime: all crypto operations go through the kernel AF_ALG
socket interface.  On OHOS the SELinux policy denies bind(AF_ALG) for
unprivileged processes (see libkcapi 1.5.0 notes: socket() succeeds,
bind() returns EPERM for hash/skcipher/rng/aead alike), so the tools
answer --version/-v but actual hashing or encryption fails at runtime.
This is a platform capability limitation, not a build defect; the
test_package exercises the real binaries through their version/help
contract which only calls the user space kcapi_versionstring() API.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibkcapiToolsConan(ConanFile):
    name = "libkcapi-tools"
    version = "1.5.0"
    description = (
        "Linux kernel crypto API command line tools: kcapi-dgst, "
        "kcapi-enc, kcapi-rng and kcapi-hasher"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/smuellerDD/libkcapi"
    url = "https://github.com/smuellerDD/libkcapi"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libkcapi-tools is supported only on Linux/OHOS"
            )

    def build_requirements(self):
        # Github tag archive ships no configure/aclocal.m4/Makefile.in, the
        # build() has to bootstrap; hnp/bin only carries the autoconf family,
        # so automake/libtool come in as tool_requires (both published in the
        # ohpcd registry, same tool_requires as the libkcapi 1.5.0 recipe).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _toolchain(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # CMSG_NXTHDR sign-compare noise on musl (libkcapi 1.5.0-r1 note);
            # --disable-werror keeps it a warning.
            "--disable-werror",
            # Tools package: the four apps only.  The test programs
            # (bin/kcapi, kcapi-enc-test-large, kcapi-convenience) and the
            # cryptoperf benchmark belong to the source-tree test suite and
            # are not part of the openEuler libkcapi-tools content either.
            "--disable-kcapi-test",
            "--disable-kcapi-speed",
            # Upstream Makefile.am links every app against libkcapi.la; with
            # a shared build libtool would link the .so and the tools would
            # carry a DT_NEEDED libkcapi.so.1 while this package ships no
            # library - force static so each tool is self-contained.
            "--disable-shared",
            "--enable-kcapi-hasher",
            "--enable-kcapi-rngapp",
            "--enable-kcapi-encapp",
            "--enable-kcapi-dgstapp",
            # configure AC_PATH_PROG finds openssl on the build host, which
            # turns on HAVE_OPENSSL and makes `make install` run the FIPS
            # CHECKSUM_CMD (openssl sha512 -r -hmac ...) over the staged
            # files - build machine behavior must never leak into the
            # package, so force the probe empty and skip that hook.
            "ac_cv_path_OPENSSL=",
        ])
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        return tc

    def generate(self):
        self._toolchain().generate()

    def _build_dep_package_folder(self, name):
        for dep in self.dependencies.build.values():
            if dep.ref.name == name:
                return dep.package_folder
        raise ConanException(f"tool_requires {name} not found")

    def _bootstrap_autotools(self):
        """Generate configure/Makefile.in (the tag archive ships neither, and
        the autoreconf chain has an autoconf.m4f macro conflict under OHOS
        HMDFS - precedent: libkcapi 1.5.0 / abiword-plugin-*).

        The bootstrap tools of the automake/libtool tool_requires are
        *scripts* (perl/sh) living in the conan cache.  On OHOS HMDFS a
        process whose ancestry passes through an HMDFS-resident python
        cannot execve() shebang scripts on the same mount (ELF binaries are
        unaffected; see notes.md), so every bootstrap step is invoked in
        interpreter-read style (perl/sh read the script instead of the
        kernel exec-ing it).  This is behavior-neutral on regular Linux CI.
        """
        src = self.source_folder
        am_pkg = self._build_dep_package_folder("automake")
        lt_pkg = self._build_dep_package_folder("libtool")
        am_lib = os.path.join(am_pkg, "share", "automake-1.18")

        # aclocal generates aclocal.m4 (source m4/ macros via ACLOCAL_PATH);
        # datadir/acdir flags replicate the package's own aclocal wrapper.
        self.run(
            'ACLOCAL_PATH="{m4}:$ACLOCAL_PATH" AUTOMAKE_LIBDIR="{lib}" '
            'PERL5LIB="{lib}" perl "{real}" --automake-acdir="{acdir}" '
            '--system-acdir="{sysac}" --force'.format(
                m4=os.path.join(src, "m4"), lib=am_lib,
                real=os.path.join(am_pkg, "bin", ".aclocal-real"),
                acdir=os.path.join(am_pkg, "share", "aclocal-1.18"),
                sysac=os.path.join(am_pkg, "share", "aclocal"),
            ),
            cwd=src, env="conanbuild",
        )
        # libtoolize (LT_INIT): add ltmain.sh before automake; the script is
        # read by /bin/sh so its $0-relative datadir lookup still works.
        self.run(
            "/bin/sh \"{}\" --copy --force --install".format(
                os.path.join(lt_pkg, "bin", "libtoolize")),
            cwd=src, env="conanbuild",
        )
        # autoconf generates configure (autoconf runs via perl itself)
        self.run("autoconf -o configure configure.ac",
                 cwd=src, env="conanbuild")
        if not os.path.exists(os.path.join(src, "configure")):
            raise ConanException("autoconf failed to generate configure")
        # Under HMDFS setgid directories mktemp -d always yields 0700
        # (umask is bypassed), so config.status writing subs1.awk into the
        # temp dir hits EPERM (DRAFT-6507, cln same type).  Replace with a
        # unique name plus an explicit umask 000 mkdir - same fix as the
        # libkcapi 1.5.0 recipe.
        cfg = os.path.join(src, "configure")
        with open(cfg, encoding="utf-8") as f:
            txt = f.read()
        old_tmp = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`'
        new_tmp = 'tmp=./conf$$-$RANDOM\n(umask 000 && mkdir "$tmp")\ntest -d "$tmp"'
        if old_tmp in txt:
            txt = txt.replace(old_tmp, new_tmp)
            with open(cfg, "w", encoding="utf-8") as f:
                f.write(txt)
            self.output.info("  [patched] configure: mktemp -d -> umask 000 mkdir")
        # automake adds Makefile.in and the aux scripts; perllib/libdir env
        # points at the package tree (Automake::Config hardcodes a broken
        # //share path in the conan package).
        self.run(
            'AUTOMAKE_LIBDIR="{lib}" PERL5LIB="{lib}" perl "{real}" '
            '--add-missing --copy --foreign'.format(
                lib=am_lib, real=os.path.join(am_pkg, "bin", ".automake-real")),
            cwd=src, env="conanbuild",
        )

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_autotools()
        args = " ".join(shlex.quote(a) for a in self._toolchain().configure_args)
        # /bin/sh READS the generated configure script - same interpreter as
        # its shebang, just invoked without execve() (HMDFS restriction, see
        # _bootstrap_autotools); config.status is re-run through $CONFIG_SHELL
        # from the profile buildenv as usual.  In-source build: basic_layout
        # leaves the configured tree in source_folder.
        self.run("/bin/sh configure " + args,
                 cwd=self.source_folder, env="conanbuild")
        # The hasher install-exec-hook links 14 hasher alias names into
        # pkglibexecdir with `ln -srf`.  HMDFS denies symlink() inside the
        # conan package cache (see notes.md), so rewrite the hook to plain
        # copies - the staged pkglibexec links are pruned by package() and
        # `cp` behaves identically on regular Linux CI.
        mkfile = os.path.join(self.source_folder, "Makefile")
        with open(mkfile, encoding="utf-8") as f:
            mk = f.read()
        if "$(LN) -srf " in mk:
            mk = mk.replace("$(LN) -srf ", "cp -f ")
            with open(mkfile, "w", encoding="utf-8") as f:
                f.write(mk)
            self.output.info(
                "  [patched] Makefile: install-exec-hook ln -srf -> cp -f "
                "(HMDFS symlink denial in conan cache)")
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run(
            'make install DESTDIR="{}"'.format(self.package_folder),
            cwd=self.source_folder, env="conanbuild",
        )

        # Tools-only package: the static lib, header, pkg-config file, the
        # test programs and the hasher pkglibexec symlink farm belong to the
        # libkcapi package or nowhere - prune everything but the four tools
        # and their man pages (same single-ownership rule as
        # libfreeaptx-tools patch 0001, done by whitelist here because the
        # hasher install-exec-hook always runs and drops symlinks into
        # pkglibexecdir).
        wanted_bin = {"kcapi-hasher", "kcapi-rng", "kcapi-enc", "kcapi-dgst"}
        wanted_man = {"kcapi-hasher.1", "kcapi-rng.1", "kcapi-enc.1", "kcapi-dgst.1"}
        bindir = os.path.join(self.package_folder, "bin")
        for entry in sorted(os.listdir(bindir)):
            if entry not in wanted_bin:
                os.remove(os.path.join(bindir, entry))
        man1 = os.path.join(self.package_folder, "share", "man", "man1")
        if os.path.isdir(man1):
            for entry in sorted(os.listdir(man1)):
                if entry not in wanted_man:
                    os.remove(os.path.join(man1, entry))
        for d in ("include", "lib", "libexec"):
            rmdir(self, os.path.join(self.package_folder, d))
        manroot = os.path.join(self.package_folder, "share", "man")
        if os.path.isdir(manroot):
            for entry in sorted(os.listdir(manroot)):
                if entry != "man1":
                    rmdir(self, os.path.join(manroot, entry))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))

        # Fail loudly if the tools did not make it (e.g. an --enable flag
        # got lost) instead of shipping an empty application package.
        for tool in sorted(wanted_bin):
            if not os.path.isfile(os.path.join(bindir, tool)):
                raise ConanException(f"{tool} was not installed")

    def package_info(self):
        # Application package: binaries only, nothing for consumers to link.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Let consumers / CI locate the entry points (precedent:
        # archives/l/libjwt-tools/3.3.3).
        self.conf_info.define("user.libkcapi-tools:bin",
                              os.path.join(self.package_folder, "bin"))
        self.conf_info.define("user.libkcapi-tools:exe",
                              os.path.join(self.package_folder, "bin",
                                           "kcapi-hasher"))
