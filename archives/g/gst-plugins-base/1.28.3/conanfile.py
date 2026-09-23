#!/usr/bin/env python3
"""Conan recipe -- gst-plugins-base 1.28.3 (Meson).

GStreamer base plugins: a set of well-maintained GStreamer plugins and
libraries for the GStreamer multimedia framework. This recipe builds the
base plugin libraries (app, audio, video, pbutils, etc.) and all available
plugins for OpenHarmony PC (aarch64).

Adaptation notes:
- Patch 0001 fixes Python script execution on HMDFS (meson-pkg-config-file-fixup,
  extract-release-date-from-doap-file)
- NLS disabled (no gettext on OHOS); _() macro stubbed via c_args
- All introspection, tests, examples, docs, tools, benchmarks disabled
- Enabled: ogg, vorbis, opus, alsa, orc, x11, xshm, xvideo, xi, drm, iso-codes
  (all dependencies published in the ohpcd registry)
- Disabled with reasons (dependency ecosystem gaps, see notes.md):
  * pango: registry pango requires 'glib/2.84.0.1' while this recipe and
    gstreamer use 'glib2/2.88.0' — mixing both glib packages in one graph
    duplicates headers/symbols; needs ecosystem-level glib unification first
  * gl: no GL API library (gl/glesv2/opengl) published in the registry,
    only an EGL wrapper (egl/1.0.5) exists
  * theora/libvisual/tremor/cdparanoia: dependencies not published in registry
  * x11 family disabled options removed: x11, xshm, xvideo, xi now enabled
"""
import os
import shutil
import pathlib

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GstPluginsBaseConan(ConanFile):
    name = "gst-plugins-base"
    version = "1.28.3"
    description = "GStreamer base plugins and libraries"
    license = "LGPL"
    homepage = "https://gstreamer.freedesktop.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    generators = ("PkgConfigDeps",)

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("glib2/2.88.0")
        self.requires("orc/0.4.42")
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        self.requires("opus/1.5.2.1")
        self.requires("alsa-lib/1.2.16.1")
        # X11 video sinks (ximagesink / xvimagesink) + DRM dumb allocator
        # NOTE: pinned to libx11/6.4.0 + libxext/6.4.0 to match the versions
        # required by libxv/libxi in the registry (the 1.8.13 line of libx11
        # is not referenced by any X11 extension library package)
        self.requires("libx11/6.4.0")
        self.requires("libxext/6.4.0")
        self.requires("libxv/1.0.13")
        # libxi/6.1.0 (not 1.8.3): pulls libxfixes with transitive_headers —
        # XInput2.h #includes <X11/extensions/Xfixes.h>, which 1.8.3 lacks
        self.requires("libxi/6.1.0")
        self.requires("libdrm/2.4.133")
        # Language name lookup for gst-tag (iso_639-2 domains)
        self.requires("iso-codes/4.20.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

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
        # Fix: lld linker on CI workers fails to load libxml2.so.16
        # The OHOS SDK's lld binary needs libxml2.so.16 from the SDK's lib dir
        # but LD_LIBRARY_PATH doesn't include it by default
        sdk_base = "/data/service/hnp/ohos-sdk.org"
        if os.path.isdir(sdk_base):
            for entry in os.listdir(sdk_base):
                candidate = os.path.join(sdk_base, entry, "ohos", "native", "llvm", "lib")
                if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                    existing = os.environ.get("LD_LIBRARY_PATH", "")
                    os.environ["LD_LIBRARY_PATH"] = f"{candidate}:{existing}" if existing else candidate
                    break
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["nls"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["tools"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        # Enabled features (dependencies available in registry)
        tc.project_options["orc"] = "enabled"
        tc.project_options["orc-compiler"] = "disabled"
        tc.project_options["ogg"] = "enabled"
        tc.project_options["vorbis"] = "enabled"
        tc.project_options["opus"] = "enabled"
        tc.project_options["alsa"] = "enabled"
        # X11 video sinks (ximagesink, xvimagesink) + DRM dumb allocator
        tc.project_options["x11"] = "enabled"
        tc.project_options["xshm"] = "enabled"
        tc.project_options["xvideo"] = "enabled"
        tc.project_options["xi"] = "enabled"
        tc.project_options["drm"] = "enabled"
        # Language names for gst-tag
        tc.project_options["iso-codes"] = "enabled"
        # Disabled features (dependency ecosystem gaps, see notes.md)
        tc.project_options["pango"] = "disabled"
        tc.project_options["theora"] = "disabled"
        tc.project_options["gl"] = "disabled"
        tc.project_options["cdparanoia"] = "disabled"
        tc.project_options["libvisual"] = "disabled"
        tc.project_options["tremor"] = "disabled"
        tc.project_options["qt5"] = "disabled"
        tc.project_options["glib_assert"] = "false"
        tc.project_options["glib_checks"] = "false"
        tc.project_options["glib_debug"] = "disabled"
        # Stub gettext/ngettext when NLS is disabled (OHOS has no gettext)
        tc.c_args.append("-Wno-error=implicit-function-declaration")
        tc.c_args.append("-Wno-error=int-conversion")
        tc.c_args.append("-Wno-int-conversion")
        tc.c_args.append("-Wno-implicit-function-declaration")
        tc.c_args.append("-Dgettext(x)=(x)")
        tc.c_args.append("-Dngettext(s,p,n)=((n)==1?(s):(p))")
        tc.generate()

        # PkgConfigDeps generates .pc files for dependencies, but meson
        # expects specific pkg-config names that may not match the conan
        # package names. Create wrapper .pc files for all mismatches.
        gen_dir = pathlib.Path(self.generators_folder)
        self._create_glib2_pcs(gen_dir)
        self._create_gstreamer_pcs(gen_dir)
        self._create_dep_pc_wrappers(gen_dir)
        # iso-codes: PkgConfigDeps would emit a bare iso-codes.pc without the
        # 'domains'/'prefix' variables that gst-libs/gst/tag requires; the
        # package's own share/pkgconfig/iso-codes.pc hardcodes prefix=/ from
        # its build. Overwrite with a wrapper pointing at the package folder.
        iso_prefix = self._get_dep_folder("iso-codes")
        if iso_prefix:
            (gen_dir / "iso-codes.pc").write_text(
                f"""prefix={iso_prefix}
domains=iso_15924 iso_3166-1 iso_3166-2 iso_3166-3 iso_4217 iso_639-2 iso_639-3 iso_639-5

Name: iso-codes
Description: ISO country, language, script, currency codes, and translations
Version: 4.20.1
"""
            )

    # --- Helper: find a dependency's package folder ---
    def _get_dep_folder(self, name):
        for dep in self.dependencies.values():
            if dep.ref.name == name:
                return str(dep.package_folder)
        return None

    # --- glib2 sub-package .pc files (same pattern as gstreamer recipe) ---
    def _create_glib2_pcs(self, gen_dir):
        prefix = self._get_dep_folder("glib2")
        if not prefix:
            return
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/glib-2.0"
        incdir1 = f"{prefix}/lib/glib-2.0/include"
        bindir = f"{prefix}/bin"
        datadir = f"{prefix}/share"

        glib_pc = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/glib-2.0
includedir1=${{prefix}}/lib/glib-2.0/include
bindir=${{prefix}}/bin
datadir=${{prefix}}/share

glib_genmarshal=${{bindir}}/glib-genmarshal
gobject_query=${{bindir}}/gobject-query
glib_mkenums=${{bindir}}/glib-mkenums
glib_valgrind_suppressions=${{datadir}}/glib-2.0/valgrind/glib.supp

Name: GLib
Description: C Utility Library
Version: 2.88.0
Libs: -L"${{libdir}}" -lglib-2.0 -lgobject-2.0 -lgio-2.0 -lgmodule-2.0 -lgthread-2.0 -lffi -lintl -lm -lpthread -ldl -lrt
Cflags: -I"${{includedir}}" -I"${{includedir1}}"
Requires: pcre2 zlib
"""
        (gen_dir / "glib-2.0.pc").write_text(glib_pc)

        subpkgs = {
            "gobject-2.0.pc": ("GObject", "gobject-2.0", ["glib-2.0"], False),
            "gio-2.0.pc": ("GIO", "gio-2.0", ["gobject-2.0"], True),
            "gmodule-2.0.pc": ("GModule", "gmodule-2.0", ["glib-2.0"], False),
            "gmodule-no-export-2.0.pc": ("GModule-no-export", "gmodule-2.0", ["glib-2.0"], False),
            "gthread-2.0.pc": ("GThread", "gthread-2.0", ["glib-2.0"], False),
            "gio-unix-2.0.pc": ("GIO-unix", None, ["gio-2.0"], False),
        }
        for fname, (name, lib, requires, is_gio) in subpkgs.items():
            req_str = ", ".join(requires)
            libs_line = f'Libs: -L"${{libdir}}" -l{lib}' if lib else ""
            gio_vars = "giomoduledir=${libdir}/gio/modules\n" if is_gio else ""
            pc = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/glib-2.0
includedir1=${{prefix}}/lib/glib-2.0/include
{gio_vars}
Name: {name}
Description: GLib sub-package ({name})
Version: 2.88.0
Requires: {req_str}
{libs_line}
Cflags: -I"${{includedir}}" -I"${{includedir1}}"
"""
            (gen_dir / fname).write_text(pc)

    # --- gstreamer sub-package .pc files ---
    def _create_gstreamer_pcs(self, gen_dir):
        prefix = self._get_dep_folder("gstreamer")
        if not prefix:
            return
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/gstreamer-1.0"

        gst_pkgs = {
            "gstreamer-1.0.pc": ("GStreamer", "gstreamer-1.0", ["glib-2.0", "gobject-2.0", "gmodule-2.0"]),
            "gstreamer-base-1.0.pc": ("GStreamer Base", "gstbase-1.0", ["gstreamer-1.0"]),
            "gstreamer-controller-1.0.pc": ("GStreamer Controller", "gstcontroller-1.0", ["gstreamer-1.0"]),
            "gstreamer-net-1.0.pc": ("GStreamer Net", "gstnet-1.0", ["gstreamer-1.0", "gobject-2.0", "gio-2.0"]),
            "gstreamer-check-1.0.pc": ("GStreamer Check", "gstcheck-1.0", ["gstreamer-1.0"]),
        }
        for fname, (name, lib, requires) in gst_pkgs.items():
            req_str = ", ".join(requires) if requires else ""
            req_line = f"Requires: {req_str}" if requires else ""
            pc = f"""prefix={prefix}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include/gstreamer-1.0

Name: {name}
Description: GStreamer sub-package ({name})
Version: 1.28.3
{req_line}
Libs: -L"${{libdir}}" -l{lib}
Cflags: -I"${{includedir}}"
"""
            (gen_dir / fname).write_text(pc)

    # --- Other dependency .pc file wrappers ---
    def _create_dep_pc_wrappers(self, gen_dir):
        # (conan_pkg_name, pc_name, lib_name, inc_subdirs, requires, version)
        # inc_subdirs: list of include subdirs relative to the package folder
        wrappers = [
            ("orc", "orc-0.4.pc", "orc-0.4", ["include/orc-0.4"], "", "0.4.42"),
            ("libogg", "ogg.pc", "ogg", ["include"], "", "1.3.6"),
            ("libvorbis", "vorbis.pc", "vorbis", ["include"], "ogg", "1.3.7"),
            ("libvorbis", "vorbisenc.pc", "vorbisenc", ["include"], "vorbis", "1.3.7"),
            ("alsa-lib", "alsa.pc", "asound", ["include"], "", "1.2.16.1"),
            # libdrm: no pkg_config_name on the conan package; upstream
            # libdrm.pc links only -ldrm and covers both include layouts
            # (xf86drm.h in include/, drm_fourcc.h in include/libdrm/)
            ("libdrm", "libdrm.pc", "drm", ["include", "include/libdrm"], "", "2.4.133"),
        ]
        # Group by conan package to get the prefix once
        pkg_prefixes = {}
        for conan_pkg, pc_name, lib, inc_subdirs, requires, version in wrappers:
            if conan_pkg not in pkg_prefixes:
                pkg_prefixes[conan_pkg] = self._get_dep_folder(conan_pkg)
            prefix = pkg_prefixes[conan_pkg]
            if not prefix:
                continue
            req_line = f"Requires: {requires}" if requires else ""
            cflags = " ".join(f'-I"{prefix}/{sub}"' for sub in inc_subdirs)
            pc = f"""prefix={prefix}
libdir=${{prefix}}/lib

Name: {pc_name.replace('.pc', '')}
Description: Conan wrapper for {conan_pkg}
Version: {version}
{req_line}
Libs: -L"${{libdir}}" -l{lib}
Cflags: {cflags}
"""
            (gen_dir / pc_name).write_text(pc)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = [
            "gstallocators-1.0",
            "gstapp-1.0",
            "gstaudio-1.0",
            "gstfft-1.0",
            "gstpbutils-1.0",
            "gstriff-1.0",
            "gstrtp-1.0",
            "gstrtsp-1.0",
            "gstsdp-1.0",
            "gsttag-1.0",
            "gstvideo-1.0",
        ]
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
        self.cpp_info.requires = [
            "gstreamer::gstreamer",
            "glib2::glib2",
            "orc::orc",
            "libogg::libogg",
            "libvorbis::libvorbis",
            "opus::opus",
            "alsa-lib::alsa-lib",
            "libx11::libx11",
            "libxext::libxext",
            "libxv::libxv",
            "libxi::libxi",
            "libdrm::libdrm",
            "iso-codes::iso-codes",
        ]

