#!/usr/bin/env python3
"""Conan recipe -- gst-libav 1.28.3 (Meson).

gst-libav wraps FFmpeg's libav codec/format libraries as a GStreamer plugin.

Key adaptation challenges:
- gst-plugins-base is NOT a published conan package; built as meson subproject
- FFmpeg .pc files report project version, not library ABI version; fixed in build()
- glib2's libintl.a has g_-prefixed gettext; stub library provides standard names
- glib2/gstreamer sub-package .pc files generated in build() (after PkgConfigDeps)
- meson fallback (subproject) must be enabled via --wrap-mode=default
"""
import os
import re
import shutil
import pathlib

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GstLibavConan(ConanFile):
    name = "gst-libav"
    version = "1.28.3"
    description = "GStreamer plugin for FFmpeg/libav codecs"
    license = "LGPL"
    homepage = "https://gstreamer.freedesktop.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    generators = ("PkgConfigDeps",)
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("ffmpeg/7.1.5")
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["gst_libav"], strip_root=True)
        sub_dir = pathlib.Path(self.source_folder) / "subprojects" / "gst-plugins-base"
        sub_dir.mkdir(parents=True, exist_ok=True)
        get(self, **self.conan_data["sources"]["gst_plugins_base"],
            strip_root=True, destination=str(sub_dir))

    def generate(self):
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {n: shutil.which(n) for n in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [n for n, p in tools.items() if p is None]
        if missing:
            raise ConanInvalidConfiguration(f"Tools not found: {', '.join(missing)}")

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["tests"] = "disabled"
        tc.project_options["doc"] = "disabled"
        # c_args for implicit-function-declaration suppression (gettext stubs)
        tc.c_args.append("-Wno-error=implicit-function-declaration")
        tc.c_args.append("-Wno-implicit-function-declaration")
        tc.c_args.append("-Wno-error=int-conversion")
        tc.c_args.append("-Wno-int-conversion")
        tc.generate()

    # ── helpers ──

    def _get_dep_prefix(self, name):
        for dep in self.dependencies.values():
            if dep.ref.name == name:
                return str(dep.package_folder)
        return None

    def _create_glib_subpkg_pcs(self, gen_dir):
        prefix = self._get_dep_prefix("glib2")
        if not prefix:
            return
        libdir = f"${{prefix}}/lib"
        inc = f"${{prefix}}/include/glib-2.0"
        inc1 = f"${{prefix}}/lib/glib-2.0/include"
        bindir = f"${{prefix}}/bin"
        datadir = f"${{prefix}}/share"

        (gen_dir / "glib-2.0.pc").write_text(
            f"prefix={prefix}\nlibdir={libdir}\nincludedir={inc}\nincludedir1={inc1}\n"
            f"bindir={bindir}\ndatadir={datadir}\n\n"
            f"glib_genmarshal=${{bindir}}/glib-genmarshal\n"
            f"gobject_query=${{bindir}}/gobject-query\n"
            f"glib_mkenums=${{bindir}}/glib-mkenums\n\n"
            f"Name: GLib\nDescription: C Utility Library\nVersion: 2.88.0\n"
            f'Libs: -L"${{libdir}}" -lglib-2.0 -lgobject-2.0 -lgio-2.0 -lgmodule-2.0 -lgthread-2.0 -lffi -lintl -lm -lpthread -ldl -lrt\n'
            f'Cflags: -I"${{includedir}}" -I"${{includedir1}}"\n'
            f"Requires: pcre2 zlib\n"
        )
        subs = {
            "gobject-2.0.pc": ("GObject", "gobject-2.0", ["glib-2.0"]),
            "gio-2.0.pc": ("GIO", "gio-2.0", ["gobject-2.0"]),
            "gmodule-2.0.pc": ("GModule", "gmodule-2.0", ["glib-2.0"]),
            "gmodule-no-export-2.0.pc": ("GModule-no-export", "gmodule-2.0", ["glib-2.0"]),
            "gthread-2.0.pc": ("GThread", "gthread-2.0", ["glib-2.0"]),
            "gio-unix-2.0.pc": ("GIO-unix", None, ["gio-2.0"]),
        }
        for fn, (nm, lib, reqs) in subs.items():
            libs = f'Libs: -L"${{libdir}}" -l{lib}\n' if lib else ""
            extra = f' -I"${{prefix}}/include"' if "unix" in fn else ""
            (gen_dir / fn).write_text(
                f"prefix={prefix}\nlibdir={libdir}\nincludedir={inc}\nincludedir1={inc1}\n"
                f"bindir={bindir}\ndatadir={datadir}\n\ngiomoduledir=${{libdir}}/gio/modules\n\n"
                f"Name: {nm}\nDescription: GLib sub-package ({nm})\nVersion: 2.88.0\n"
                f"Requires: {', '.join(reqs)}\n{libs}"
                f'Cflags: -I"${{includedir}}" -I"${{includedir1}}"{extra}\n'
            )

    def _create_gstreamer_pcs(self, gen_dir):
        prefix = self._get_dep_prefix("gstreamer")
        if not prefix:
            return
        pkgs = {
            "gstreamer-1.0.pc": ("gstreamer-1.0", "-lgstreamer-1.0 -lm -ldl", "glib-2.0 gobject-2.0 gmodule-no-export-2.0"),
            "gstreamer-base-1.0.pc": ("gstreamer-base-1.0", "-lgstbase-1.0", "gstreamer-1.0"),
            "gstreamer-check-1.0.pc": ("gstreamer-check-1.0", "-lgstcheck-1.0", "gstreamer-1.0"),
            "gstreamer-net-1.0.pc": ("gstreamer-net-1.0", "-lgstnet-1.0", "gstreamer-1.0"),
            "gstreamer-controller-1.0.pc": ("gstreamer-controller-1.0", "-lgstcontroller-1.0", "gstreamer-1.0"),
        }
        for fn, (nm, libs, reqs) in pkgs.items():
            (gen_dir / fn).write_text(
                f"prefix={prefix}\nlibdir=${{prefix}}/lib\nincludedir=${{prefix}}/include/gstreamer-1.0\n"
                f"libexecdir=${{prefix}}/bin\nbindir=${{prefix}}/bin\ndatadir=${{prefix}}/share\n\n"
                f"Name: {nm}\nDescription: {nm}\nVersion: 1.28.3\nRequires: {reqs}\n"
                f"Libs: -L${{libdir}} {libs}\nCflags: -I${{includedir}}\n"
            )

    def _fix_ffmpeg_pc_versions(self, gen_dir):
        prefix = self._get_dep_prefix("ffmpeg")
        if not prefix:
            return
        incdir = f"{prefix}/include"
        pat = re.compile(r'^#define\s+LIB\w+_VERSION_(MAJOR|MINOR|MICRO)\s+(\d+)')
        files = {
            "libavcodec": ["libavcodec/version_major.h", "libavcodec/version.h"],
            "libavformat": ["libavformat/version_major.h", "libavformat/version.h"],
            "libavfilter": ["libavfilter/version_major.h", "libavfilter/version.h"],
            "libavutil": ["libavutil/version.h"],
            "libswresample": ["libswresample/version_major.h", "libswresample/version.h"],
            "libswscale": ["libswscale/version_major.h", "libswscale/version.h"],
        }
        for lib, paths in files.items():
            major = minor = micro = None
            for rel in paths:
                fp = os.path.join(incdir, rel)
                if not os.path.exists(fp):
                    continue
                with open(fp) as f:
                    for line in f:
                        m = pat.match(line.strip())
                        if m:
                            w, v = m.group(1), m.group(2)
                            if w == "MAJOR" and major is None: major = v
                            elif w == "MINOR" and minor is None: minor = v
                            elif w == "MICRO" and micro is None: micro = v
            if major:
                ver = f"{major}.{minor or 0}.{micro or 0}"
                pc = gen_dir / f"{lib}.pc"
                if pc.exists():
                    content = pc.read_text()
                    lines = [f"Version: {ver}" if l.startswith("Version:") else l for l in content.split("\n")]
                    pc.write_text("\n".join(lines))

    def _create_gettext_compat(self, gen_dir):
        stub = (
            '#include <stddef.h>\n'
            'const char *bindtextdomain(const char *d, const char *dir) {'
            ' extern const char *g_libintl_bindtextdomain(const char *, const char *);'
            ' return g_libintl_bindtextdomain(d, dir); }\n'
            'const char *bind_textdomain_codeset(const char *d, const char *c) {'
            ' extern const char *g_libintl_bind_textdomain_codeset(const char *, const char *);'
            ' return g_libintl_bind_textdomain_codeset(d, c); }\n'
            'const char *textdomain(const char *d) { return d; }\n'
            'const char *gettext(const char *m) { return m; }\n'
            'const char *ngettext(const char *s, const char *p, unsigned long n) { return n==1?s:p; }\n'
            'const char *dcgettext(const char *d, const char *m, int c) { (void)d;(void)c; return m; }\n'
            'const char *dcngettext(const char *d, const char *s, const char *p, unsigned long n, int c) {'
            ' (void)d;(void)c; return n==1?s:p; }\n'
        )
        (gen_dir / "gettext_compat.c").write_text(stub)
        cc = shutil.which("clang") or shutil.which("gcc") or "cc"
        os.system(f'{cc} -c -fPIC -o "{gen_dir}/gettext_compat.o" "{gen_dir}/gettext_compat.c"')
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        os.system(f'{ar} rcs "{gen_dir}/libgettext_compat.a" "{gen_dir}/gettext_compat.o"')

    # ── build / package / package_info ──

    def build(self):
        apply_conandata_patches(self)

        gen_dir = pathlib.Path(self.generators_folder)

        # PkgConfigDeps has now generated .pc files; fix/extend them
        self._create_glib_subpkg_pcs(gen_dir)
        self._create_gstreamer_pcs(gen_dir)
        self._fix_ffmpeg_pc_versions(gen_dir)
        self._create_gettext_compat(gen_dir)

        spb_opts = [
            "-Dgst-plugins-base:iso-codes=disabled",
            "-Dgst-plugins-base:orc=disabled", "-Dgst-plugins-base:orc-compiler=disabled",
            "-Dgst-plugins-base:gl=disabled", "-Dgst-plugins-base:examples=disabled",
            "-Dgst-plugins-base:tests=disabled", "-Dgst-plugins-base:doc=disabled",
            "-Dgst-plugins-base:introspection=disabled", "-Dgst-plugins-base:vorbis=disabled",
            "-Dgst-plugins-base:theora=disabled", "-Dgst-plugins-base:ogg=disabled",
            "-Dgst-plugins-base:x11=disabled", "-Dgst-plugins-base:xshm=disabled",
            "-Dgst-plugins-base:xvideo=disabled", "-Dgst-plugins-base:xi=disabled",
            "-Dgst-plugins-base:alsa=disabled", "-Dgst-plugins-base:pango=disabled",
            "-Dgst-plugins-base:cdparanoia=disabled", "-Dgst-plugins-base:libvisual=disabled",
        ]

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        build_dir = self.build_folder
        source_dir = self.source_folder

        cmd = (
            f'meson setup --native-file "{native_file}" --wrap-mode=default '
            f'-Dc_link_args="-L{gen_dir} -lgettext_compat" '
            f'"{build_dir}" "{source_dir}" --prefix=/ '
            + " ".join(spb_opts)
        )
        self.run(cmd)
        meson = Meson(self)
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["gstlibav"]
        self.cpp_info.libdirs = ["lib/gstreamer-1.0"]
        self.cpp_info.includedirs = []
        self.cpp_info.requires = ["gstreamer::gstreamer", "ffmpeg::ffmpeg"]
