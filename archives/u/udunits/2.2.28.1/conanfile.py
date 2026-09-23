#!/usr/bin/env python3
"""Conan recipe for UDUNITS-2 2.2.28.1 (udunits2).

Autotools project.  The release tarball has no generated configure, so the
recipe regenerates it.  The Conan perl package's XS modules cannot be
dlopen()ed on HMDFS; following the ding-libs 0.7.0 precedent, the bootstrap
uses the native OHOS perl (/data/service/hnp/bin/perl) with PERL5LIB limited
to automake's pure-perl share dir, and runs aclocal/autoconf/automake
explicitly instead of autoreconf.  expat is a hard configure dependency.
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class UdunitsConan(ConanFile):
    name = "udunits"
    version = "2.2.28.1"
    description = "Library for manipulating units of physical quantities (UDUNITS-2)"
    license = "LicenseRef-Unidata"
    homepage = "https://github.com/Unidata/UDUNITS-2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"udunits supports Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "udunits OHOS support is validated for armv8/AArch64"
            )

    def build_requirements(self):
        # The release tarball contains only configure.ac/Makefile.am; the
        # generated configure/Makefile.in are produced here (R6: no generated
        # files in patches).
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        # configure.ac: AC_SEARCH_LIBS([XML_StopParser], [expat]) hard dep.
        self.requires("expat/2.8.2.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--disable-dependency-tracking"])
        tc.generate()

    def _runtime_env(self):
        """Put the host dependencies' lib dirs on LD_LIBRARY_PATH so the
        configure-time conftest probes (which link -lexpat) can run on OHOS."""
        env = Environment()
        expat = self.dependencies["expat"]
        if expat is not None:
            libdir = os.path.join(expat.package_folder, "lib")
            if os.path.isdir(libdir):
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def _inject_ohos_aux(self):
        """Ensure the generated Autotools aux scripts recognize the OHOS
        system type (uname -s = HarmonyOS).  The Conan toolchain's
        config.guess/config.sub predate OHOS and make configure fail with
        "cannot guess build type" in the clean CI worker.  The injection
        mirrors the verified ding-libs 0.7.0 patches (0001/0002) and is
        idempotent: if the marker is already present nothing changes."""
        aux_dir = os.path.join(self.source_folder, "build-aux")
        guess_p = os.path.join(aux_dir, "config.guess")
        sub_p = os.path.join(aux_dir, "config.sub")

        if os.path.isfile(guess_p):
            with open(guess_p, "r", encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
            if "HarmonyOS" not in txt:
                # 1) LIBC detection: add __OHOS__ alongside __ANDROID__.
                old1 = "\t#if defined(__ANDROID__)\n\tLIBC=android\n"
                new1 = ("\t#if defined(__ANDROID__)\n\tLIBC=android\n"
                        "#elif defined(__OHOS__)\n\tLIBC=ohos\n")
                if old1 in txt:
                    txt = txt.replace(old1, new1, 1)
                # 2) System-type case: recognize *:HarmonyOS:*:*.
                anchor = ("case $UNAME_MACHINE:$UNAME_SYSTEM:"
                          "$UNAME_RELEASE:$UNAME_VERSION in\n")
                ohos_case = (
                    "case $UNAME_MACHINE:$UNAME_SYSTEM:"
                    "$UNAME_RELEASE:$UNAME_VERSION in\n"
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    i?86)          MACHINE=i686 ;;\n"
                    "\t    *)             MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                    "\t;;\n\n"
                )
                if anchor in txt:
                    txt = txt.replace(anchor, ohos_case, 1)
                with open(guess_p, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("  [ok] injected OHOS recognition into "
                                 "build-aux/config.guess")

        if os.path.isfile(sub_p):
            with open(sub_p, "r", encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
            if "linux-ohos" not in txt:
                # Accept the aarch64-unknown-linux-ohos tuple in config.sub.
                old2 = ("\t\t\tandroid-linux)\n"
                        "\t\t\t\tbasic_machine=$field1-unknown\n"
                        "\t\t\t\tbasic_os=linux-android\n")
                new2 = (old2 +
                        "\t\t\t\t;;\n"
                        "\t\t\tohos-linux)\n"
                        "\t\t\t\tbasic_machine=$field1-unknown\n"
                        "\t\t\t\tbasic_os=linux-ohos\n")
                if old2 in txt:
                    txt = txt.replace(old2, new2, 1)
                with open(sub_p, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("  [ok] injected OHOS recognition into "
                                 "build-aux/config.sub")

    def _bootstrap_prefix(self):
        """Conan perl XS modules cannot be dlopen()ed on HMDFS (Permission
        denied).  Use the native OHOS perl with PERL5LIB limited to
        automake's pure-perl share dir (ding-libs 0.7.0 precedent).  PWD is
        published so the automake/aclocal shell wrappers (which compute their
        --libdir via `cd "$(dirname "$0")" && pwd`) resolve the directory
        without a failing getcwd() on HMDFS."""
        automake = self.dependencies.build["automake"]
        share = ""
        if automake is not None:
            share = os.path.join(automake.package_folder, "share", "automake-1.18")
        return (f'PERL="/data/service/hnp/bin/perl" '
                f'PERL5LIB="{share}" PWD="{self.source_folder}"')

    def build(self):
        apply_conandata_patches(self)
        # The release tarball ships an old generated aclocal.m4 (produced by a
        # different Automake version); drop it so the chain below regenerates
        # everything with the toolchain Automake (avoids AM_INIT_AUTOMAKE
        # version-mismatch failures).
        for stale in ("aclocal.m4", "configure", "Makefile.in"):
            p = os.path.join(self.source_folder, stale)
            if os.path.exists(p):
                os.remove(p)
        bp = self._bootstrap_prefix()
        # Regenerate configure + Makefile.in from configure.ac/Makefile.am.
        # Run the autotools chain explicitly (not autoreconf) so the native
        # perl prefix is applied to every step.  configure.ac uses LT_INIT, so
        # libtoolize must run first to produce build-aux/ltmain.sh and the
        # aux files that automake --add-missing copies.
        self.run(f"{bp} libtoolize --copy --force",
                 cwd=self.source_folder, env="conanbuild")
        self.run(f"{bp} aclocal --force -I m4",
                 cwd=self.source_folder, env="conanbuild")
        self.run(f"{bp} autoconf --force",
                 cwd=self.source_folder, env="conanbuild")
        self.run(f"{bp} autoheader --force",
                 cwd=self.source_folder, env="conanbuild")
        self.run(f"{bp} automake --add-missing --copy --force-missing",
                 cwd=self.source_folder, env="conanbuild")

        # CI 干净环境使用 conan 工具链 automake 1.18 自带的 config.guess
        # （2024-07-27 版），其中没有 OHOS 识别 → configure 报
        # "cannot guess build type"。 本机通过是因为 PATH 中系统 automake
        # 优先复制了含 OHOS 识别的 config.guess。 参照 ding-libs 0.7.0
        # 的 0001-build-config.guess.patch，将 OHOS 识别注入生成的
        # build-aux/config.guess 与 config.sub（幂等：已注入则跳过）。
        self._inject_ohos_aux()

        # E129: HMDFS always sets the setgid bit on new directories; umask 077
        # creates drwx--S--- which blocks even the owner.  configure/config.status
        # create temp dirs with umask 077 — relax to 022.
        for gen in ("configure", "config.status"):
            p = os.path.join(self.source_folder, gen)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
                txt = txt.replace("umask 077", "umask 022")
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(txt)

        # HMDFS: after Conan creates the build tree the parent dirs are not
        # reachable via getcwd(); publish the logical PWD so configure's pwd
        # probe does not fail (adms / aribb24 / aircrack / ding-libs precedent).
        os.environ["PWD"] = self.build_folder

        autotools = Autotools(self)
        with self._runtime_env().vars(self).apply():
            autotools.configure()
        # MAKEINFO=true: CI workers have no texinfo; .info docs are not part
        # of the link interface.
        autotools.make(args=["-j1", "MAKEINFO=true"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true"])
        # Libtool archives carry build-time absolute libdir; not needed by
        # Conan consumers (cpp_info/pkg-config provide link metadata).
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        copy(
            self,
            "COPYRIGHT",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["udunits2"]
        self.cpp_info.bindirs = ["bin"]
        # udunits2 looks up its XML unit database via UDUNITS2_XML_PATH
        # (falling back to the compile-time default); export the packaged one
        # so consumers can run udunits2 without extra configuration.
        self.runenv_info.define_path(
            "UDUNITS2_XML_PATH",
            os.path.join(self.package_folder, "share", "udunits", "udunits2.xml"),
        )
