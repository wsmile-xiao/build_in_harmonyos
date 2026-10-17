#!/usr/bin/env python3
"""Conan recipe — validns 8.00.11.0 (Autotools, application).

validns is a high-performance DNS/DNSSEC zone file validator.
Version mapping: platform 8.00.11.0 = Debian/Ubuntu 8.0+really0.11.0
= upstream DNS-OARC validns v0.11.0 (see conandata.yml for the anchor).

Build contract: configure -> make -> `make check` (upstream test target:
TAP suite t/test.pl via perl Test::Harness + three C self-test programs
test64 / test32hex / testcompose, see src/Makefile.am).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ValidnsConan(ConanFile):
    name = "validns"
    version = "8.00.11.0"
    description = "High-performance DNS/DNSSEC zone file validator (upstream v0.11.0)"
    license = "BSD-2-Clause"
    homepage = "https://codeberg.org/DNS-OARC/validns"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Hard upstream deps (configure.ac): AC_CHECK_LIB(Judy) +
        # PKG_CHECK_MODULES(libssl, libcrypto); pthread comes from libc.
        self.requires("judy/1.0.5")
        self.requires("openssl/3.5.6")

    def build_requirements(self):
        # configure uses PKG_CHECK_MODULES; CI workers have no system
        # pkg-config -> provide the pkgconf tool (R36: published).
        self.tool_requires("pkgconf/3.0.5")
        # NOTE: deliberately NO perl tool_requires — conan's perl package is
        # an OHOS cross build whose Cwd.so cannot be dlopen'd on the same
        # arch build machine (E-entry, see notes.md). `make check` uses the
        # system perl, present on devices (~/.harmonybrew/bin/perl) and CI
        # workers (/data/service/hnp/bin/perl), core Test::Harness included.

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)
        # Test-only perl module for t/test.pl (Test::Command::Simple), kept
        # outside the packaged artifact; equivalent of Debian's
        # libtest-command-simple-perl <!nocheck> build dependency.
        get(self, **self.conan_data["sources"][1], strip_root=True,
            destination="test-perl")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Upstream configure queries pkg-config modules `libssl`/`libcrypto`
        # (system-installed OpenSSL .pc names); Conan's openssl package is
        # registered as `openssl`, so the query cannot match by name. Use the
        # <MODULE>_CFLAGS/_LIBS overrides PKG_CHECK_MODULES honours before
        # consulting pkg-config, built from the dependency's cpp_info (no
        # hardcoded paths).
        ssl = self.dependencies["openssl"]
        cflags = " ".join("-I{}".format(d) for d in ssl.cpp_info.includedirs)
        libs = " ".join(["-L{}".format(d) for d in ssl.cpp_info.libdirs]
                        + ["-l{}".format(l) for l in ssl.cpp_info.libs])
        env = Environment()
        env.define("libssl_CFLAGS", cflags)
        env.define("libssl_LIBS", libs)
        env.define("libcrypto_CFLAGS", cflags)
        env.define("libcrypto_LIBS", libs)
        base_env = tc.environment()
        base_env.compose_env(env)
        tc.generate(env=base_env)
        AutotoolsDeps(self).generate()    # -I/-L/-l for judy and openssl
        VirtualBuildEnv(self).generate()  # puts pkgconf tool on PATH for configure

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_for_ohos()
        self._fix_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream official test suite (same SHA contract as the build).
        self._run_upstream_tests(autotools)

    def _fix_configure_umask(self):
        """HMDFS: temp dirs created via `umask 077 && mktemp -d ./confXXXXXX`
        land as drwx--S--- and writing into them fails with
        `./config.status: ... subs1.awk: Permission denied` /
        `config.status: error: could not setup config files machinery`.
        Neutralise the umask in the shipped configure before it runs (same
        workaround as the rest of this repo's autotools recipes); the
        generated config.status inherits the relaxed umask. Idempotent."""
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "umask 077" in content:
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(content.replace("umask 077", "umask 022"))
                self.output.info("relaxed configure umask 077 -> 022 for HMDFS")

    def _perl_lib(self):
        # strip_root=True already removed the dist directory, so the module
        # tree lands directly at test-perl/lib/Test/Command/Simple.pm.
        return os.path.join(self.source_folder, "test-perl", "lib")

    def _run_upstream_tests(self, autotools):
        if not shutil.which("perl"):
            # Honest skip with a visible marker: keep the C self-tests, and
            # declare the TAP suite NOT_RUN (tool absent), never a fake PASS.
            self.output.warning(
                "perl not found on PATH: upstream TAP suite t/test.pl NOT_RUN; "
                "running the three C self-test programs only")
            src_build = os.path.join(self.build_folder, "src")
            for prog in ("test64", "test32hex", "testcompose"):
                self.run("./{}".format(prog), cwd=src_build, env="conanbuild")
            return
        env = Environment()
        env.define("PERL5LIB", self._perl_lib())
        with env.vars(self).apply():
            autotools.make(target="check", args=["-j1"])

    def _patch_config_for_ohos(self):
        """Teach the shipped config.guess/config.sub the *-linux-ohos triplet.

        The tarball is bootstrapped (no autoreconf needed), but its
        config.guess does not know `uname -s` == HarmonyOS and its 2024-era
        config.sub rejects OS `ohos`. Insert an early HarmonyOS branch in
        config.guess and three minimal branches in config.sub (idempotent).
        """
        src = self.source_folder
        cg = os.path.join(src, "config.guess")
        if os.path.isfile(cg) and "OHOS-PC adaptation" not in open(cg).read():
            with open(cg) as f:
                content = f.read()
            marker = ("case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:"
                      "$UNAME_VERSION in")
            patch_txt = (
                "# ---- OHOS-PC adaptation: identify HarmonyOS/OHOS early ----\n"
                "case \"$UNAME_SYSTEM\" in\n"
                "  HarmonyOS|OHOS|OpenHarmony)\n"
                "    case \"$UNAME_MACHINE\" in\n"
                "      aarch64|arm64) echo \"aarch64-unknown-linux-ohos\"; exit 0 ;;\n"
                "      armv7*) echo \"arm-unknown-linux-ohos-eabi\"; exit 0 ;;\n"
                "      *) echo \"$UNAME_MACHINE-unknown-linux-ohos\"; exit 0 ;;\n"
                "    esac ;;\n"
                "esac\n"
                "# ---- end OHOS-PC adaptation ----\n"
            )
            if marker in content:
                content = content.replace(marker, patch_txt + marker, 1)
                with open(cg, "w") as f:
                    f.write(content)
                self.output.info("patched config.guess for OHOS")
        cs = os.path.join(src, "config.sub")
        if os.path.isfile(cs) and "linux-ohos" not in open(cs).read():
            with open(cs) as f:
                content = f.read()
            changed = False
            # 1) split kernel/os for the ohos variant before the generic
            #    `*-*` dash split runs.
            a1 = "case $basic_os in\n\tgnu/linux*)"
            p1 = ("case $basic_os in\n\tlinux-ohos*)\n"
                  "\t\tkernel=linux\n\t\tos=ohos\n\t\t;;\n"
                  "\tgnu/linux*)")
            if a1 in content:
                content = content.replace(a1, p1, 1)
                changed = True
            # 2) accept `ohos` as a valid OS in the final validation list.
            a2 = "\t     | fiwix* )"
            p2 = "\t     | fiwix* | ohos* )"
            if a2 in content:
                content = content.replace(a2, p2, 1)
                changed = True
            # 3) accept the linux-ohos kernel/OS combination.
            a3 = "\t\t   | linux-musl* | linux-relibc* | linux-uclibc* )"
            p3 = "\t\t   | linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )"
            if a3 in content:
                content = content.replace(a3, p3, 1)
                changed = True
            if changed:
                with open(cs, "w") as f:
                    f.write(content)
                self.output.info("patched config.sub for OHOS")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI tool: binary at <pkg>/bin/validns; no headers or libs shipped
        # (judy/openssl are statically linked into the executable, R26).
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
