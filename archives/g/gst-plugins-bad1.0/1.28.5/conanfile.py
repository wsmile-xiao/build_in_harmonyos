#!/usr/bin/env python3
"""Conan recipe -- gst-plugins-bad1.0 1.28.5 (Meson).

GStreamer Bad Plugins 1.28.5: plugin libraries and GStreamer plugin .so
files for OpenHarmony PC (aarch64).

Version-follow-up adaptation of the CI-green gst-plugins-bad 1.28.3 recipe
(PR #4376). The 1.28.3 -> 1.28.5 delta is confined to plugin source
bugfixes (avtp/curl/dtls/webrtc/mxf/videoparsers/...); meson.build and
meson.options are byte-identical except the version string, so the proven
configuration transfers unchanged.

Key adaptation notes:
- gst-plugins-base is NOT a published conan package; it is built as a meson
  subproject from the official 1.28.5 tarball (same approach as the
  gst-libav and gst-plugins-bad 1.28.3 recipes). gstreamer core 1.28.3 from
  the conan registry satisfies the `>= 1.28.0` meson version gate
  (GStreamer stable-branch rule; verified by local meson configure probe).
- NLS disabled (no gettext on OHOS); a gettext compat stub library is linked
  in (glib2's libintl provides g_-prefixed variants only).
- glib2/gstreamer sub-package .pc files are generated in build() because
  conan's PkgConfigDeps only emits one .pc per package.
- Platform-specific feature disabling (not arbitrary trimming):
  gl (OHOS GL header conflicts), opensles (Android-specific), webp (static
  library symbol conflicts), orc (orc not in registry).
- AR/AS/STRIP/NM/RANLIB pinned by absolute path (CI worker env fix).
"""
import os
import pathlib
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GstPluginsBad10Conan(ConanFile):
    name = "gst-plugins-bad1.0"
    version = "1.28.5"
    description = "GStreamer Bad Plugins -- multimedia plugins with licensing concerns"
    license = "LGPL"
    homepage = "https://gstreamer.freedesktop.org/"

    package_type = "library"
    generators = ("PkgConfigDeps",)
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("glib2/2.88.0")
        # PIC static zlib: the gst-plugins-base subproject links zlib into
        # shared libraries (libgsttag etc.); plain zlib/1.3.1 archives are
        # non-PIC and fail with R_AARCH64 relocation errors. zlib/1.3.1.1 is
        # built with -fPIC (same override as the gst-libav recipe).
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["gst_plugins_bad"], strip_root=True)
        # Pre-provision gst-plugins-base as a meson subproject so that the
        # dependency(..., fallback: ['gst-plugins-base', ...]) lookups in
        # gst-plugins-bad's meson.build resolve to the local directory
        # instead of a wrap download.
        sub_dir = pathlib.Path(self.source_folder) / "subprojects" / "gst-plugins-base"
        sub_dir.mkdir(parents=True, exist_ok=True)
        get(self, **self.conan_data["sources"]["gst_plugins_base"],
            strip_root=True, destination=str(sub_dir))

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names
        # that are NOT on its PATH. meson probes these and aborts at
        # configure. Pin the real tools by ABSOLUTE PATH.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Standard build-system options (not feature trimming)
        tc.project_options["nls"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        # Platform-specific feature disabling (legitimate platform
        # incompatibilities, not feature trimming)
        tc.project_options["gl"] = "disabled"          # OHOS GL header conflicts
        tc.project_options["opensles"] = "disabled"    # Android-specific, not on OHOS
        tc.project_options["webp"] = "disabled"        # libwebp static symbol conflicts
        tc.project_options["orc"] = "disabled"         # orc not in registry
        # Suppress implicit-function-declaration/int-conversion warnings from
        # gettext-less builds (OHOS has no gettext)
        tc.c_args.append("-Wno-error=implicit-function-declaration")
        tc.c_args.append("-Wno-implicit-function-declaration")
        tc.c_args.append("-Wno-error=int-conversion")
        tc.c_args.append("-Wno-int-conversion")
        # gst-plugins-bad's vulkan meson.build does a raw
        # find_program('glib-mkenums') which resolves via PATH to HNP's
        # broken perl script (no /usr/bin/perl on OHOS). Pin the working
        # python3 implementation shipped in the glib2 conan package through
        # the native file [binaries] section (meson checks it before PATH).
        glib2_prefix = self._get_dep_prefix("glib2")
        if glib2_prefix:
            mkenums = os.path.join(glib2_prefix, "bin", "glib-mkenums")
            if os.path.isfile(mkenums):
                tc.binaries["glib-mkenums"] = mkenums
        tc.generate()

    # ── helpers ──

    def _get_dep_prefix(self, name):
        for dep in self.dependencies.values():
            if dep.ref.name == name:
                return str(dep.package_folder)
        return None

    def _create_glib_subpkg_pcs(self, gen_dir):
        """Wrapper .pc files for glib2 sub-packages (meson looks up
        glib-2.0/gobject-2.0/gio-2.0/..., conan only ships glib2.pc)."""
        prefix = self._get_dep_prefix("glib2")
        if not prefix:
            return
        libdir = "${prefix}/lib"
        inc = "${prefix}/include/glib-2.0"
        inc1 = "${prefix}/lib/glib-2.0/include"
        bindir = "${prefix}/bin"
        datadir = "${prefix}/share"

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
            # gio-unix-2.0 headers live in include/gio-unix-2.0/gio/ (the
            # unixfd plugin does #include <gio/gunixfdmessage.h>)
            extra = f' -I"${{prefix}}/include/gio-unix-2.0"' if "unix" in fn else ""
            (gen_dir / fn).write_text(
                f"prefix={prefix}\nlibdir={libdir}\nincludedir={inc}\nincludedir1={inc1}\n"
                f"bindir={bindir}\ndatadir={datadir}\n\n"
                f"giomoduledir=${{libdir}}/gio/modules\n\n"
                f"Name: {nm}\nDescription: GLib sub-package ({nm})\nVersion: 2.88.0\n"
                f"Requires: {', '.join(reqs)}\n{libs}"
                f'Cflags: -I"${{includedir}}" -I"${{includedir1}}"{extra}\n'
            )

    def _create_gstreamer_pcs(self, gen_dir):
        """Wrapper .pc files for gstreamer sub-packages (meson looks up
        gstreamer-1.0/gstreamer-base-1.0/..., conan only ships gstreamer.pc)."""
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

    def _create_gettext_compat(self, gen_dir):
        """Static stub library providing standard gettext symbols; glib2's
        libintl only exports g_-prefixed variants."""
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
        self.run(f'{cc} -c -fPIC -o "{gen_dir}/gettext_compat.o" "{gen_dir}/gettext_compat.c"')
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        self.run(f'{ar} rcs "{gen_dir}/libgettext_compat.a" "{gen_dir}/gettext_compat.o"')

    # ── build / package / package_info ──

    def build(self):
        apply_conandata_patches(self)

        gen_dir = pathlib.Path(self.generators_folder)

        # PkgConfigDeps has now generated .pc files; fix/extend them
        self._create_glib_subpkg_pcs(gen_dir)
        self._create_gstreamer_pcs(gen_dir)
        self._create_gettext_compat(gen_dir)

        # Options for the gst-plugins-base meson subproject: disable what
        # cannot build on OHOS / has no published conan dependency.
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

        # A previous failed/stale build may have left a configured meson tree
        # in the build folder; reconfigure instead of erroring out.
        reconfigure = "--reconfigure" if os.path.isdir(
            os.path.join(build_dir, "meson-info")) else ""

        cmd = (
            f'meson setup --native-file "{native_file}" --wrap-mode=default '
            f'-Dc_link_args="-L{gen_dir} -lgettext_compat" '
            f'{reconfigure} '
            f'"{build_dir}" "{source_dir}" --prefix=/ '
            + " ".join(spb_opts)
        )
        self.run(cmd)
        meson = Meson(self)
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._restore_pristine_binaries()

    def _restore_pristine_binaries(self):
        """meson install rewrites the DT_RUNPATH entries of installed
        libraries and tools (it blanks the build-tree rpath strings in
        .dynstr). OHOS verifies a per-file code signature (embedded by lld
        at link time) over the whole file content: any post-link byte
        change invalidates it and the loader rejects the file with EACCES
        "Permission denied" at load/dlopen time (same class of issue as
        knowledge entry E504). Overwrite the installed copies with the
        pristine build-tree artifacts so the ELF signatures stay valid.
        Runtime dependency resolution uses LD_LIBRARY_PATH (conanrun
        environment), not these build-tree rpaths."""
        build_dir = self.build_folder
        # Index real (non-symlink) build-tree files by basename
        index = {}
        for root, _, files in os.walk(build_dir):
            for f in files:
                p = os.path.join(root, f)
                if not os.path.islink(p) and os.path.isfile(p):
                    index.setdefault(f, p)
        restored = 0
        for sub in ("lib",
                    os.path.join("lib", "gstreamer-1.0"),
                    os.path.join("libexec", "gstreamer-1.0"),
                    "bin"):
            d = os.path.join(self.package_folder, sub)
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                dst = os.path.join(d, f)
                if os.path.islink(dst) or not os.path.isfile(dst):
                    continue
                src = index.get(f)
                if src and os.path.getsize(src) == os.path.getsize(dst):
                    shutil.copy2(src, dst)
                    restored += 1
                elif src:
                    # Same basename but different size: shipping the
                    # install-time file would mean a broken signature.
                    self.output.warn(
                        f"pristine artifact size mismatch for {f}: "
                        f"{src} vs {dst} -- install copy left in place")
                elif f.endswith(".so") or ".so." in f:
                    self.output.warn(
                        f"no build-tree counterpart found for {f} -- "
                        f"install copy left in place")
        self.output.info(
            f"Restored {restored} pristine build artifacts over meson "
            f"install output (rpath rewrite invalidates OHOS ELF signatures)")

    def package_info(self):
        self.cpp_info.libs = [
            "gstadaptivedemux-1.0",
            "gstanalytics-1.0",
            "gstbadaudio-1.0",
            "gstbasecamerabinsrc-1.0",
            "gstcodecparsers-1.0",
            "gstcodecs-1.0",
            "gstinsertbin-1.0",
            "gstisoff-1.0",
            "gstmpegts-1.0",
            "gstmse-1.0",
            "gstphotography-1.0",
            "gstplay-1.0",
            "gstplayer-1.0",
            "gstsctp-1.0",
            "gsttranscoder-1.0",
            "gsturidownloader-1.0",
            "gstwebrtc-1.0",
        ]
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
        # gst-plugins-base libraries ship inside this package (vendored
        # subproject build), so consumers only need gstreamer + glib2.
        self.cpp_info.requires = ["gstreamer::gstreamer", "glib2::glib2"]
