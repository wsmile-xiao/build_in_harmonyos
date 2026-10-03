#!/usr/bin/env python3
"""Conan recipe for mednaffe, a GTK+ 3 front-end for the Mednafen emulator."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MednaffeConan(ConanFile):
    name = "mednaffe"
    version = "0.9.3"
    description = "GTK+ 3 front-end (GUI) for the Mednafen multi-system emulator"
    license = "GPL-3.0-only"
    homepage = "https://github.com/AmatCoder/mednaffe"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.38", transitive_headers=True, transitive_libs=True)

    def export_sources(self):
        # Zero patches upstream; keep the hook so the patch channel is explicit.
        copy(self, "patches/*", self.recipe_folder,
             os.path.join(self.export_sources_folder, "patches"))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS is not recognised by the config.guess shipped in the tarball.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # 1) Copy every graph package's shipped .pc into the generators folder
        #    with prefix= rewritten to the real absolute package folder (the
        #    conan-center gtk/glib/pango packages ship prefix=-empty .pc files
        #    whose --cflags expand to -I//include and break real compiles).
        import glob as _glob
        import re as _re
        for req, dep in self.dependencies.items():
            pf = getattr(dep, "package_folder", None)
            if not pf:
                continue
            for sub in ("lib/pkgconfig", "share/pkgconfig"):
                for pcfile in _glob.glob(os.path.join(pf, sub, "*.pc")):
                    txt = open(pcfile, encoding="utf-8", errors="ignore").read()
                    real = os.path.dirname(os.path.dirname(os.path.dirname(pcfile)))
                    txt = _re.sub(r"(?m)^prefix=.*$", "prefix=" + real, txt, count=1)
                    open(os.path.join(self.generators_folder,
                                      os.path.basename(pcfile)), "w",
                         encoding="utf-8").write(txt)
        pcs = set()
        no_pc = []
        for req, dep in self.dependencies.items():
            pf = getattr(dep, "package_folder", None)
            if not pf:
                continue
            found = False
            for sub in ("lib/pkgconfig", "share/pkgconfig"):
                d = os.path.join(pf, sub)
                if os.path.isdir(d):
                    pcs.add(d)
                    found = True
            if not found:
                no_pc.append(dep)
        pcs.add(self.generators_folder)
        tc.configure_args.append("PKG_CONFIG_PATH=" + self.generators_folder + ":" + ":".join(sorted(pcs)))
        tc.generate()

        # 2) AFTER tc.generate(): synthesize .pc files for packages that the
        #    graph bundles statically but whose .pc Requires: names must still
        #    resolve.  Written after the toolchain generate() so conan does
        #    not wipe them.

        # 3) gobject-2.0.pc Requires: libffi, but ffi is statically linked into
        #    the conan glib package (no libffi package in the graph at all).
        #    Empty-Libs libffi.pc resolves the Requires; runtime needs nothing
        #    (gobject NEEDED = libglib + libc, first-hand readelf).
        glib = None
        try:
            glib = self.dependencies["glib"]
        except Exception:
            glib = None
        if glib is not None:
            gpf = glib.package_folder or ""
            with open(os.path.join(self.generators_folder, "libffi.pc"), "w") as f:
                f.write("prefix=" + gpf + chr(10)
                        + "Name: libffi" + chr(10)
                        + "Description: synth (ffi statically linked in conan glib)" + chr(10)
                        + "Version: 3.4.6" + chr(10)
                        + "Cflags: " + chr(10))
            # glib-2.0.pc Requires: libpcre2-8, but pcre2 is statically bundled
            # into the glib package (glib NEEDED = libintl + libc only, first-hand
            # readelf) and no libpcre2-8.pc is shipped -> empty-Libs synth.
            with open(os.path.join(self.generators_folder, "libpcre2-8.pc"), "w") as f:
                f.write("prefix=" + gpf + chr(10)
                        + "Name: libpcre2-8" + chr(10)
                        + "Description: synth (pcre2 statically bundled in conan glib)" + chr(10)
                        + "Version: 10.42" + chr(10)
                        + "Cflags: " + chr(10))
        tiff = None
        try:
            tiff = self.dependencies["libtiff"]
        except Exception:
            tiff = None
        if tiff is not None:
            tpf = tiff.package_folder or ""
            with open(os.path.join(self.generators_folder, "liblzma.pc"), "w") as f:
                f.write("prefix=" + tpf + chr(10)
                        + "Name: liblzma" + chr(10)
                        + "Description: synth (lzma statically bundled in conan libtiff)" + chr(10)
                        + "Version: 5.6.2" + chr(10)
                        + "Cflags: " + chr(10))

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        src = self.source_folder
        # Scratch space must be machine-neutral: CI clean workers have no
        # /storage/... tree, so keep it under this package's private build
        # folder (R49: work dirs as build_folder children).
        tmp_root = os.path.join(self.build_folder, "tmproot")
        _csdir = os.path.join(self.build_folder, "csdir")
        os.makedirs(tmp_root, exist_ok=True)
        os.makedirs(_csdir, exist_ok=True)
        # E386/E232: profile CONFIG_SHELL = hnp bash 5.3 with broken getcwd()
        # on HarmonyOS mounts; re-assert /bin/sh inline at exec time.
        # E011 + HMDFS: config.status's mktemp branch creates 0700 dirs that
        # deny file creation on this mount family (a52dec 0002 precedent), and
        # configure executes the just-generated config.status with the ORIGINAL
        # embedded 077 line.  Split into two phases: --no-create; patch the
        # generated config.status; run it.
        conf = os.path.join(src, "configure")
        cstat = os.path.join(src, "config.status")
        bad = '(umask 077 && mktemp -d -q "$TMPDIR/csXXXXXX")'
        good = '(umask 022 && mktemp -d "$TMPDIR/csXXXXXX")'
        t = open(conf, encoding="utf-8", errors="ignore").read()
        if bad in t:
            t = t.replace(bad, good)
            open(conf, "w", encoding="utf-8").write(t)
        self.run('umask 022; export TMPDIR="%s"; CONFIG_SHELL=/bin/sh SHELL=/bin/sh "%s" %s --no-create'
                 % (tmp_root, conf, autotools._configure_args),
                 cwd=src, env="conanbuild")
        if os.path.exists(cstat):
            t = open(cstat, encoding="utf-8", errors="ignore").read()
            if bad in t:
                t = t.replace(bad, good)
            t = t.replace('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                          'tmp=' + _csdir + ' &&')
            open(cstat, "w", encoding="utf-8").write(t)
            self.run('umask 022; export TMPDIR="%s"; CONFIG_SHELL=/bin/sh /bin/sh "%s"'
                     % (tmp_root, cstat), cwd=src, env="conanbuild")
        self.run('make -C "%s" -j1' % src, env="conanbuild")

    def package(self):
        src = self.source_folder
        self.run('make -C "%s" install DESTDIR="%s"' % (src, self.package_folder),
                 env="conanbuild")
        import glob
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
