#!/usr/bin/env python3
"""Conan recipe — yersinia 0.8.2 (Layer 2 attack tool, ncurses TUI).

Adaptation scope (HarmonyOS PC / OHOS aarch64):
- autotools build of the `yersinia` binary; gtk2 interface disabled
  (--disable-gtk; gtk+-2.0 is not adapted on OHOS);
- dependencies (all published on the ohpcd remote): libnet/1.2,
  libpcap/1.10.6, ncurses/6.6. The 2006-era configure hardcodes /usr
  search paths for all three — injected via its own knobs
  (--with-pcap-includes / --with-libnet-includes / --with-ncurses)
  plus CPPFLAGS/LDFLAGS;
- upstream ships NO test suite (no TESTS/check_PROGRAMS in any
  Makefile.am, N_static=0): consumer test in test_package covers the
  binary's observable no-args banner and the root-required path.

Known OHOS/platform pitfalls handled here:
- configure.in uses the pre-1.13 two-argument AM_INIT_AUTOMAKE form which
  automake 1.18 rejects -> patch 0001 rewrites it to the no-arg modern
  form, then build() runs `autoreconf -fi` (the shipped 2013 config.guess
  does not know OHOS; regenerating installs current config.guess/sub);
- E114: generated configure patched to drop `umask 077` (HMDFS setgid);
- E074: make -j1 (HMDFS jobserver fifo EPERM);
- the binary checks `getuid() != 0` and exits via clean_exit()=0 before
  touching any terminal — the consumer test asserts that path verbatim.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that may not exist; point env at PATH hits."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates an unwritable drwx--S--- temp dir. Remove the `umask 077`
    (and its now-orphaned parentheses) from the generated configure."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)



def _route_shell_off_hnp_bash(conanfile):
    """E386 (经验汇总 §12.38 / §12.70-1, psocksxx/1.1.1 先例): the ohos-aarch64
    profile pins SHELL/CONFIG_SHELL to /data/service/hnp/bin/bash, whose
    getcwd() fails inside HMDFS build dirs, so configure dies with
    "working directory cannot be determined". Rewrite every aggregated env
    script in the generators folder instead: a second
    save_script("conanbuild") would make the script source itself in an
    endless loop. Must run before the first self.run().
    """
    import glob
    for script in glob.glob(os.path.join(conanfile.generators_folder, "*.sh")):
        with open(script, "r", encoding="utf-8") as f:
            data = f.read()
        patched = data.replace("/data/service/hnp/bin/bash", "/bin/sh")
        if patched != data:
            with open(script, "w", encoding="utf-8") as f:
                f.write(patched)
    os.environ["CONFIG_SHELL"] = "/bin/sh"
    os.environ["SHELL"] = "/bin/sh"



def _ncurses_wide_shim(conanfile):
    """Expose conan's wide-char ncurses under the classic names and put the
    header dir on CPPFLAGS.

    conan ncurses/6.6 ships only libncursesw.a / libpanelw.a, while upstream's
    2006 probes hardcode -lncurses and `-lpanel $(CURSES_LIBS)`
    (src/Makefile.am:22); measured: "checking for panel.h... no",
    "checking for use_default_colors in -lncurses... no", then
    ncurses-interface.h: unknown type name 'PANEL'.  The header probe is a
    preprocessor test driven by `$CPP $CPPFLAGS`, so -I in CFLAGS is not
    enough -- CPPFLAGS must carry it.  Precedent: acedb/4.9.62 (alias
    symlinks), 4ti2/1.6.10 (CPPFLAGS/LDFLAGS via os.environ).
    """
    ncu = conanfile.dependencies["ncurses"]
    inc = os.path.join(ncu.package_folder, ncu.cpp_info.includedirs[0])
    libdir = os.path.join(ncu.package_folder, ncu.cpp_info.libdirs[0])
    shim = os.path.join(conanfile.build_folder, "ncurses-shim", "lib")
    os.makedirs(shim, exist_ok=True)
    for alias, real in (("libncurses.a", "libncursesw.a"),
                        ("libcurses.a", "libncursesw.a"),
                        ("libpanel.a", "libpanelw.a")):
        src = os.path.join(libdir, real)
        dst = os.path.join(shim, alias)
        if os.path.exists(src) and not os.path.exists(dst):
            os.symlink(src, dst)
    os.environ["CPPFLAGS"] = "-I" + inc + " " + os.environ.get("CPPFLAGS", "")
    os.environ["LDFLAGS"] = "-L" + shim + " -L" + libdir + " " \
        + os.environ.get("LDFLAGS", "")
class YersiniaConan(ConanFile):
    name = "yersinia"
    version = "0.8.2"
    description = "Yersinia — Layer 2 (VLAN/STP/CDP/DTP/...) attack and audit tool"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tomac/yersinia"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libnet/1.2")
        self.requires("libpcap/1.10.6")
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # The git archive's shipped configure predates OHOS support in
        # config.guess; autoreconf -fi regenerates with current autotools.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "yersinia is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        VirtualBuildEnv(self).generate()

        pcap = self.dependencies["libpcap"]
        libnet = self.dependencies["libnet"]
        ncu = self.dependencies["ncurses"]

        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS; pass the triplets explicitly.
        # build==host on purpose: these builds run on the target machine, and a
        # differing --build makes autoconf set cross_compiling=yes, which turns
        # upstream's AC_TRY_RUN BPF probe into a hard
        # "cannot run test program while cross compiling" failure (measured).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # gtk2 interface needs gtk+-2.0 via pkg-config: not adapted, disable
        tc.configure_args.append("--disable-gtk")
        # 2006-era configure searches /usr for libnet/libpcap headers; use
        # its own --with knobs to point at the conan packages
        tc.configure_args.append(
            "--with-pcap-includes="
            + os.path.join(pcap.package_folder, pcap.cpp_info.includedirs[0]))
        tc.configure_args.append(
            "--with-libnet-includes="
            + os.path.join(libnet.package_folder, libnet.cpp_info.includedirs[0]))
        # curses.m4 knob: CURSES_LIBS="-L<prefix>/lib -lncurses"; derive the
        # prefix from the package's first libdir
        ncu_prefix = os.path.join(ncu.package_folder, ncu.cpp_info.libdirs[0])
        if ncu_prefix.endswith("/lib"):
            ncu_prefix = ncu_prefix[:-len("/lib")]
        tc.configure_args.append("--with-ncurses=" + ncu_prefix)
        # belt and suspenders: make every dependency visible to the raw
        # AC_CHECK_* probes as well
        for dep in (pcap, libnet, ncu):
            for inc in [os.path.join(dep.package_folder, d)
                      for d in dep.cpp_info.includedirs]:
                tc.extra_cflags.append("-I" + inc)
            for lib in [os.path.join(dep.package_folder, d)
                      for d in dep.cpp_info.libdirs]:
                tc.extra_ldflags.append("-L" + lib)
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        _route_shell_off_hnp_bash(self)
        # regenerate configure from the patched configure.in (modern
        # config.guess/sub; the shipped 2013 ones don't know OHOS)
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        _ncurses_wide_shim(self)
        # Upstream headers carry tentative definitions (protocols.h:210,
        # interfaces.h:70, ...) which collide under clang's default
        # -fno-common. configure.in:17 assigns CFLAGS outright, so the flag
        # can only be added there -> see patches/0003-configure-in-fcommon.patch.
        # (tc.extra_cflags and os.environ["CFLAGS"] were both measured to be
        # discarded: grep -c fcommon conan-create.log == 0.)
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # R51: run the check target for real as well. Upstream registers no
        # tests at all (grep finds no TESTS/check_PROGRAMS anywhere, no test*/
        # dir, no RUNTEST scripts), so this executes an empty automake suite
        # and exits 0 - declared N_static=0 rather than a skipped step.
        autotools.make(target="check", args=["-j1"])
        # consumer coverage lives in test_package/test.sh

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
