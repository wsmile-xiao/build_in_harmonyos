#!/usr/bin/env python3
"""Conan recipe — sfk 2.0.0.3 (Autotools, single CLI binary)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SfkConan(ConanFile):
    name = "sfk"
    version = "2.0.0.3"
    description = "Swiss File Knife: a multi function command line tool"
    license = "BSD-2-Clause"
    homepage = "http://stahlworks.com/dev/swiss-file-knife.html"
    url = "https://sourceforge.net/projects/swissfileknife/"
    topics = ("file-tool", "cli", "utility")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sfk supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def _patch_configure_mktemp(self):
        """Make config.status' throwaway dir writable on the HMFS volume.

        The shipped configure embeds autoconf's AS_TMPDIR block into the
        generated config.status (it is what fails at config.status line ~619):

            tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` && \
                  test -n "$tmp" && test -d "$tmp" ||
            { tmp=./conf$-$RANDOM; (umask 077 && mkdir "$tmp"); }

        On the setgid HMFS mount a 077-masked temp dir lands as drwx--S---,
        which the (non-owner-mapped) build uid cannot write into, so
        config.status aborts with:

            ./config.status: line NNN: ./confXXXXXXXX/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery

        before the first awk script is written. Relaxing the mask to 002 yields
        a drwxrws--x temp dir that stays writable across the non-owner uid
        mapping (DRAFT-inn-mktemp-umask022-hmdfs / DRAFT-10767 / DRAFT-libvoikko).
        Only the two 'umask 077' literals in the shipped configure are touched;
        everything else in the script is left byte-identical.
        """
        cfg = os.path.join(self.source_folder, "configure")
        with open(cfg, "r", encoding="utf-8", errors="replace") as f:
            txt = f.read()
        old = "umask 077"
        n = txt.count(old)
        if n != 2:
            self.output.warning(
                "configure: expected 2 'umask 077' AS_TMPDIR literals, "
                f"found {n}; skipping config.status mktemp workaround"
            )
            return
        txt = txt.replace(old, "umask 002")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(txt)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Out-of-tree build through the plain Autotools helper; keep the
        # dependency tracker on the lightweight ohos-aarch64 toolchain.
        tc.configure_args.append("--disable-dependency-tracking")
        # OHOS libc is musl-based: glibc's *_64 (LFS) entry points (fopen64,
        # fseeko64, ftello64, stat64, statvfs64 ...) only exist as aliases when
        # _LARGEFILE64_SOURCE is defined, and fseeko/ftello need a POSIX/GNU
        # feature macro. sfkpack.cpp/sfk*.cpp use these; define them here so the
        # OHOS musl build sees them (harmless on glibc). This complements
        # patches/0001-musl-posix-compat.patch (which removes glibc-internal
        # __dev_t / fpos_t.__pos that musl does not provide at all).
        tc.extra_cxxflags.extend(["-D_GNU_SOURCE", "-D_LARGEFILE64_SOURCE"])
        env = tc.environment()
        # The ohos-aarch64 profile [buildenv] injects CONFIG_SHELL/SHELL pointing
        # at /data/service/hnp/bin/bash, which returns ENOTSUP/EINVAL for getcwd()
        # on the HMFS build directories. Autoconf then runs every
        # config.guess/config.sub/config.status subprocess through that bash,
        # flooding the log with "getcwd: cannot access parent directories" and
        # risking probe/temp-dir resolution failures. Pin the autotools shell to
        # toybox /bin/sh (DRAFT-6487 / DRAFT-10767 / DRAFT-libvoikko).
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        tc.generate(env=env)

    def build(self):
        self._patch_configure_mktemp()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # sfk 2.0.0.3 ships no upstream test framework: Makefile.am declares
        # only bin_PROGRAMS = sfk, there is no TESTS/check_PROGRAMS target and
        # no test directory. The upstream audit is declared in
        # test_package/MANIFEST.yml (upstream_tests_exist: false); the
        # no_tests upstream marker and the consumer test result are emitted by
        # test_package/test.sh after it exercises the packaged binary.

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # HMFS may drop the exec bit (HMBS_CAP_CHMOD=0) from the installed
        # binary; best-effort restore so the packaged `sfk` stays runnable.
        sfk_bin = os.path.join(self.package_folder, "bin", "sfk")
        if os.path.isfile(sfk_bin):
            try:
                os.chmod(sfk_bin, 0o755)
            except OSError:
                pass
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            self.runenv_info.append_path("PATH", bin_dir)
            self.buildenv_info.append_path("PATH", bin_dir)
