#!/usr/bin/env python3
"""Conan recipe for libvpd 2.2.11 (IBM VPD library, autotools, C + C++).

OHOS adaptations:
- requires sqlite3 (configure hard-requires it)
- OHOS clang toolchain has no libstdc++; the C++ runtime is libc++ linked
  implicitly by clang++, so the redundant `-lstdc++` in libvpd_cxx_la_LDFLAGS
  is removed via patches/0001-makefile-am-ohos-adapt.patch.
- The official tag tarball ships no generated `configure` (configure.ac +
  bootstrap.sh only), so build() runs the autotools bootstrap steps
  (aclocal / ltmain.sh / autoheader / automake --add-missing / autoconf)
  using the automake/libtool/autoconf tool_requires from the OHPC registry.
  libtoolize is intentionally bypassed: the ohpcd libtool/2.5.4 package ships
  a baked absolute pkgauxdir, so ltmain.sh is copied directly and aclocal
  picks up libtool.m4 through ACLOCAL_PATH (PERL5LIB is also required for the
  ohpcd automake/1.18 package to locate its Automake modules).
- configure is given explicit --build/--host so the 2024 config.guess shipped
  by automake --add-missing is never consulted (it does not know HarmonyOS);
  the config.sub shipped with automake 1.18 / libtool 2.5.4 accepts
  aarch64-linux-ohos.
- install-exec-hook (installs udev rules + creates /var/lib/lsvpd) is
  neutralised: OHOS does not use udev vpdupdate rules, and the hook depends on
  the coreutils `install` binary which is absent in the OHOS build env.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibvpdConan(ConanFile):
    name = "libvpd"
    version = "2.2.11"
    description = "IBM libvpd - Linux VPD (Vital Product Data) access library (C and C++ APIs)"
    license = "LGPL-2.1"
    homepage = "https://github.com/power-ras/libvpd"
    url = "https://github.com/power-ras/libvpd"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac hard-requires sqlite3 (AC_CHECK_HEADERS + AC_CHECK_LIB)
        self.requires("sqlite3/3.53.4")

    def build_requirements(self):
        # The tag tarball ships no generated configure; bootstrap needs these.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("autoconf/2.72")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Explicit triplets: automake's config.guess cannot detect HarmonyOS
        # (uname -s = "HarmonyOS"), so never let configure guess.
        tc.configure_args.append("--build=aarch64-linux-gnu")
        tc.configure_args.append("--host=aarch64-linux-ohos")
        # Upstream AM_CPPFLAGS uses the cwd-relative "-I./src/" which breaks in
        # conan's out-of-tree build (make runs from build-release while the
        # sources are copied one level up).  Bake absolute include dirs into
        # CPPFLAGS via the configure argument so they land in the generated
        # Makefile: the libvpd self-includes (<libvpd-2/*.hpp>) plus the
        # sqlite3 headers needed by the configure checks.
        cppflags = "-I" + os.path.join(self.source_folder, "src")
        sql3 = self.dependencies["sqlite3"]
        for inc in sql3.cpp_info.includedirs:
            cppflags += " -I" + os.path.join(sql3.package_folder, inc)
        tc.configure_args.append("CPPFLAGS=" + cppflags)
        tc.generate()
        # Inject dependency LDFLAGS etc. (sqlite3 lib paths).
        deps = AutotoolsDeps(self)
        deps.generate()
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)
        am = self.dependencies.build["automake"].package_folder
        lt = self.dependencies.build["libtool"].package_folder
        ac = self.dependencies.build["autoconf"].package_folder
        perl5lib = os.path.join(am, "share", "automake-1.18")
        # The ohpcd autoconf/2.72 package bakes a conan-perl shebang (and a
        # broken '//share/autoconf' default) into .autom4te-real, while the
        # automake/1.18 package hard-shebangs its scripts with the system perl
        # and the ohpcd perl/5.42.2 XS modules are ABI-incompatible with that
        # system perl.  To keep one coherent interpreter for the whole
        # bootstrap, install a small `autom4te` wrapper that runs the real
        # script under the system perl and points autom4te_perllibdir /
        # AC_MACRODIR at the autoconf package data dir (the env vars are the
        # package's official relocatability mechanism).
        wrp = os.path.join(self.build_folder, "autotools-bin")
        os.makedirs(wrp, exist_ok=True)
        # The ohpcd autoconf package also bakes the broken '//share/autoconf'
        # prefix into autom4te.cfg include dirs; write a relocated copy and
        # point AUTOM4TE_CFG at it.
        ac_cfg = os.path.join(wrp, "autom4te.cfg")
        with open(os.path.join(ac, "share", "autoconf", "autom4te.cfg")) as cfgsrc:
            cfg_txt = cfgsrc.read().replace("//share/autoconf",
                                            os.path.join(ac, "share", "autoconf"))
        with open(ac_cfg, "w") as cfgdst:
            cfgdst.write(cfg_txt)
        # Same for every conan-perl-shebang'd script in the autoconf package
        # (autom4te/autoconf/autoheader all hardcode the ohpcd perl): run the
        # real script under the system perl with the relocated data dirs.
        for tool in ("autom4te", "autoconf", "autoheader"):
            wrapper = os.path.join(wrp, tool)
            with open(wrapper, "w") as wf:
                wf.write("#!/bin/sh\n"
                         "export autom4te_perllibdir={s}\n"
                         "export AC_MACRODIR={s}\n"
                         "export AUTOM4TE_CFG={c}\n"
                         "exec {p} {r} \"$@\"\n".format(
                             s=os.path.join(ac, "share", "autoconf"),
                             c=ac_cfg,
                             p="/data/service/hnp/bin/perl",
                             r=os.path.join(ac, "bin", ".{t}-real".format(t=tool))))
            os.chmod(wrapper, 0o755)
        # With this wrapper on PATH, every perl helper resolves to the system
        # perl: aclocal/automake run via their system-perl shebang, autom4te
        # via our wrapper.  PERL5LIB is reduced to the automake module dir so
        # nothing from the ABI-incompatible conan perl module tree is loaded.
        # AUTOM4TE/AUTOCONF/AUTOHEADER pin the wrappers explicitly (aclocal
        # resolves autom4te through $AUTOM4TE and automake resolves autoconf
        # through $AUTOCONF first; the ohpcd autoconf bin->real chain would
        # otherwise win over the PATH lookup).
        sh = ("PATH={w}:/data/service/hnp/bin:$PATH "
              "AUTOM4TE={w}/autom4te AUTOCONF={w}/autoconf "
              "AUTOHEADER={w}/autoheader PERL5LIB={p}").format(
            w=wrp, p=perl5lib)
        env = Environment()
        env.define("ACLOCAL_PATH", os.path.join(lt, "share", "aclocal"))
        with env.vars(self).apply():
            # Bootstrap the autotools tree (equivalent of upstream bootstrap.sh
            # minus libtoolize, see module docstring).  Must run in the source
            # folder: that is where configure.ac / Makefile.am live; the conan
            # build folder only holds the out-of-tree build.
            self.run("{e} mkdir -p config m4".format(e=sh), cwd=self.source_folder)
            self.run("{e} aclocal".format(e=sh), cwd=self.source_folder)
            self.run("cp {lt}/share/libtool/build-aux/ltmain.sh config/".format(lt=lt), cwd=self.source_folder)
            self.run("{e} autoheader".format(e=sh), cwd=self.source_folder)
            self.run("{e} automake --add-missing --copy".format(e=sh), cwd=self.source_folder)
            self.run("{e} autoconf".format(e=sh), cwd=self.source_folder)
        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            # HMFS quirk: the autoconf-generated config.status creates its temp
            # dir with `umask 077 && mktemp -d`; HMFS normalises 0700 -> 0760
            # (group without exec bit), so the process (accessing via group)
            # cannot create files inside it and config.status aborts.  Patching
            # the generated script to use umask 002 fixes this on HMFS and is a
            # no-op on POSIX-correct filesystems.
            self.run("sed -i 's/umask 077/umask 002/g' config.status")
            self.run("./config.status")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Headers are installed to include/libvpd-2/ by the upstream makefiles.
        self.cpp_info.libs = ["vpd_cxx", "vpd"]
        self.cpp_info.requires = ["sqlite3::sqlite3"]
        self.cpp_info.set_property("cmake_file_name", "libvpd")
        self.cpp_info.set_property("cmake_target_name", "libvpd::libvpd")
