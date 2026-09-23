#!/usr/bin/env python3
"""Conan recipe for cdemud 1.0.0 on HarmonyOS PC (aarch64, OHOS).

cdemud (cdemu-daemon) is the userspace daemon of the CDEmu optical drive
emulation suite. This is a compile/packaging-level port: runtime operation
needs the vhba kernel module and a D-Bus bus, neither of which exists on
HarmonyOS (see notes.md / README.md).

Key platform decisions (see notes.md for evidence):
  * All autotools dependency probes are fed through the GLIB_*/GOBJECT_*/
    GMODULE_*/DBUS_*/LIBDAEMON_*/LIBMIRAGE_* cache variables pointing at a
    build-private, dependency-.la-free directory (E236; dbus-glib 0.114
    precedent; the single hand-written libdaemon.la there is sanitized on
    purpose, see build()).
    PKG_CHECK_MODULES honors pre-set <GROUP>_CFLAGS/<GROUP>_LIBS and
    skips pkg-config, so no dbus-1.pc alias is needed either. Each group's
    LIBS value closes its own -Wl,--start-group/--end-group over the full
    static closure so the final executable link is order-independent.
  * glib-genmarshal (glib package) and dbus-binding-tool (dbus-glib
    package) are consumed from the dependency bindirs through PATH.
  * --disable-alsa: ALSA backend disabled; the built-in null audio
    backend is used (OHOS device has no audio nodes in /dev/snd).
  * 2007-era autotools: config.guess/config.sub OHOS triplet patches,
    configure umask 077 -> 022 (HMDFS self-write rejection) and ACLOCAL/
    AUTOMAKE/AUTOCONF neutralization follow the dbus-glib/libdaemon
    precedents. src/main.c g_type_init() is guarded with
    #if !GLIB_CHECK_VERSION(2,36,0): the call is deprecated since
    glib 2.36 (GOBJECT_DEPRECATED_IN_2_36) but still declared and
    linkable in glib 2.88, so the guard is kept only to avoid the
    deprecation warning (precautionary, not functionally required).
  * The packaged cdemud ELF is self-signed for OHOS exec (opus-tools 0.2
    precedent).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdemudConan(ConanFile):
    name = "cdemud"
    version = "1.0.0"
    description = (
        "CDEmu daemon: userspace part of the CDEmu optical drive "
        "emulation suite (D-Bus service controlling vhba devices)."
    )
    license = "GPL-2.0-or-later"
    homepage = "https://cdemu.sourceforge.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.0")
        self.requires("dbus/1.14.10")
        self.requires("dbus-glib/0.114")
        self.requires("libdaemon/0.14")
        self.requires("libmirage/1.0.0")
        # Direct static link inputs of the dependency archives below
        # (same as the dbus-glib 0.114 recipe); all published.
        self.requires("libsndfile/1.2.2")
        self.requires("pcre2/10.45")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @property
    def _la_free_dir(self):
        return os.path.join(self.build_folder, "dependency-archives")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # ALSA optional backend off; built-in null audio backend remains.
        tc.configure_args.append("--disable-alsa")
        tc.generate()

        glib = self.dependencies["glib"].package_folder
        dbus = self.dependencies["dbus"].package_folder
        dbus_glib = self.dependencies["dbus-glib"].package_folder
        libdaemon = self.dependencies["libdaemon"].package_folder
        libmirage = self.dependencies["libmirage"].package_folder
        sndfile = self.dependencies["libsndfile"].package_folder
        expat = self.dependencies["expat"].package_folder
        la = self._la_free_dir

        glib_cflags = (
            f"-I{os.path.join(glib, 'include', 'glib-2.0')} "
            f"-I{os.path.join(glib, 'lib', 'glib-2.0', 'include')}")
        glib_closure = (
            "-lglib-2.0 -lintl -lffi -lpcre2-8 -lpcre2-posix -lz")
        dbus_cflags = (
            f"-I{os.path.join(dbus, 'include')} "
            f"-I{os.path.join(dbus, 'include', 'dbus-1.0')} "
            f"-I{os.path.join(dbus_glib, 'include')} "
            f"-I{os.path.join(dbus_glib, 'include', 'dbus-1.0')}")

        env = Environment()
        env.append("CPPFLAGS",
                   f"-I{os.path.join(glib, 'include')} {glib_cflags} "
                   f"{dbus_cflags} "
                   f"-I{os.path.join(libdaemon, 'include')} "
                   f"-I{os.path.join(libmirage, 'include')} "
                   f"-I{os.path.join(libmirage, 'include', 'libmirage-1.0')} "
                   f"-I{os.path.join(sndfile, 'include')}")
        # Keep the link face independent of any machine's /usr/local
        # residue: the published libdaemon.la freezes its build machine's
        # dependency_libs (-L<builder>/usr/local/lib) and libdir='//lib';
        # if libtool resolves -ldaemon through such a .la it injects
        # -L/usr/local/lib ahead of the archive dir, and -lintl then
        # silently resolves to that machine's own libintl.a, which lacks
        # the g_libintl_* symbols that glib's static libglib-2.0.a needs
        # (official server CI failure). Pin the exact archives onto the
        # link line, resolved at generate time from the dependency
        # packages (never hardcoded cache paths).
        env.append("LDFLAGS",
                   f"-L{la} "
                   f"{os.path.join(libdaemon, 'lib', 'libdaemon.a')} "
                   f"{os.path.join(glib, 'lib', 'libintl.a')}")
        env.define("glib_CFLAGS", glib_cflags)
        env.define("glib_LIBS",
                   f"-L{la} -Wl,--start-group {glib_closure} -Wl,--end-group")
        env.define("gobject_CFLAGS", glib_cflags)
        env.define("gobject_LIBS",
                   f"-L{la} -Wl,--start-group -lgobject-2.0 {glib_closure} "
                   f"-Wl,--end-group")
        env.define("gmodule_CFLAGS", glib_cflags)
        env.define("gmodule_LIBS",
                   f"-L{la} -Wl,--start-group -lgmodule-2.0 {glib_closure} "
                   f"-Wl,--end-group")
        # PKG_CHECK_MODULES(dbus, dbus-1 >= 0.60 dbus-glib-1 >= 0.61):
        # one group covering both modules.
        env.define("dbus_CFLAGS", dbus_cflags)
        env.define("dbus_LIBS",
                   f"-L{la} -Wl,--start-group -ldbus-glib-1 -ldbus-1 "
                   f"-lgio-2.0 -lgobject-2.0 -lgthread-2.0 -lgmodule-2.0 "
                   f"{glib_closure} -Wl,--end-group")
        env.define("libdaemon_CFLAGS",
                   f"-I{os.path.join(libdaemon, 'include')}")
        env.define("libdaemon_LIBS",
                   f"-L{la} -Wl,--start-group -ldaemon -Wl,--end-group")
        env.define("libmirage_CFLAGS",
                   f"-I{os.path.join(libmirage, 'include')} "
                   f"-I{os.path.join(libmirage, 'include', 'libmirage-1.0')}")
        env.define("libmirage_LIBS",
                   f"-L{la} -Wl,--start-group -lmirage -lsndfile "
                   f"-lgobject-2.0 -lgmodule-2.0 {glib_closure} -lm "
                   f"-Wl,--end-group")
        # Build-time code generators consumed by the shipped Makefile rules.
        env.append_path("PATH", [
            os.path.join(glib, "bin"),
            os.path.join(dbus_glib, "bin"),
        ])
        # dbus-binding-tool is a prebuilt OHOS ELF with DT_NEEDED
        # libexpat.so (expat ships only a shared object on OHOS); its own
        # package rpath points into its now-relocated build tree, so the
        # expat libdir must be on the loader path while make runs it.
        env.append_path("LD_LIBRARY_PATH", os.path.join(expat, "lib"))
        # HMDFS timestamp granularity can falsely trigger autotools
        # re-maintenance rules (am--refresh); dbus-glib precedent.
        if str(self.settings.os) == "OHOS":
            env.define("ACLOCAL", "true")
            env.define("AUTOMAKE", "true")
            env.define("AUTOCONF", "true")
        env.vars(self, scope="build").save_script("cdemud-deps")

    def build(self):
        apply_conandata_patches(self)

        # E236: copy only the dependency static archives (plus expat's
        # shared object, the only one shipped by expat on OHOS) into a
        # build-private directory that contains no .la metadata.
        # Never mutate the conan cache.
        la = self._la_free_dir
        for dep in ("glib", "dbus", "dbus-glib", "libdaemon", "libmirage",
                    "libsndfile", "pcre2", "zlib"):
            libdir = os.path.join(self.dependencies[dep].package_folder, "lib")
            copy(self, "*.a", src=libdir, dst=la, keep_path=False)
        copy(self, "libexpat.so*",
             src=os.path.join(self.dependencies["expat"].package_folder, "lib"),
             dst=la, keep_path=False)
        # The '*.a' copy above never carries .la metadata, but the
        # published libdaemon artifact ships a defective libdaemon.la that
        # libtool could still pick up through its own fallback search
        # dirs. Write a sanitized .la into our archive dir (the first -L
        # on the link line) so libtool always resolves -ldaemon to the
        # clean copy: dependency_libs emptied, libdir pinned here.
        with open(os.path.join(la, "libdaemon.la"), "w") as f:
            f.write("\n".join([
                "# libdaemon.la - a libtool library file",
                "# Generated by ltmain.sh (GNU libtool) 2.2.6",
                "# Sanitized by the cdemud recipe (line 2 must keep the",
                "# ltmain.sh signature or libtool rejects the archive):",
                "# dependency_libs emptied, libdir pinned to this dir; the",
                "# published artifact's .la freezes build-machine paths and",
                "# preempts any defective .la found later in libtool's",
                "# fallback search path.",
                "dlname=''",
                "library_names=''",
                "old_library='libdaemon.a'",
                "inherited_linker_flags=''",
                "dependency_libs=''",
                "weak_library_names=''",
                "current=5",
                "age=5",
                "revision=0",
                "installed=yes",
                "shouldnotlink=no",
                "dlopen=''",
                "dlpreopen=''",
                f"libdir='{la}'",
                "",
            ]))
        self.output.info(f"dependency archives: {sorted(os.listdir(la))}")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    @staticmethod
    def _ohos_tool(name):
        path = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
        if not os.path.isfile(path):
            raise ConanException(f"Required OHOS tool is missing: {name}")
        return path

    def _sign_ohos_elf(self, path):
        readelf = self._ohos_tool("llvm-readelf")
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        sections = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        codesign_count = sections.count(".codesign")
        if codesign_count == 1:
            self.output.info(f"Preserving existing .codesign section: {path}")
            return
        if codesign_count != 0:
            raise ConanException(f"ELF has invalid .codesign count: {path}")
        clean = path + ".codesign-clean"
        signed = path + ".cdemud-signed"
        for generated in (clean, signed):
            if os.path.exists(generated):
                os.remove(generated)
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path, clean],
                check=True,
                timeout=30,
            )
            subprocess.run(
                [signer, "sign", "-inFile", clean, "-outFile", signed,
                 "-selfSign", "1"],
                check=True,
                timeout=60,
            )
            sections = subprocess.run(
                [readelf, "-SW", signed],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException(
                    f"Signed ELF has invalid .codesign count: {path}")
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(signed, path)
        finally:
            for generated in (clean, signed):
                if os.path.exists(generated):
                    os.remove(generated)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # E236: remove generated .la metadata from the final package.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS" and can_run(self):
            path = os.path.join(self.package_folder, "bin", "cdemud")
            if os.path.isfile(path):
                self._sign_ohos_elf(path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
