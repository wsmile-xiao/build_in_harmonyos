#!/usr/bin/env python3
"""Conan recipe — gtk4 4.22.4 (Meson).

GTK4 is the GNOME 4 UI toolkit. On HarmonyOS PC (aarch64) there is no
window system (no X11, no Wayland, no EGL), so GTK4 is built with only
the Broadway backend (HTML5/Web rendering) and Vulkan/media/print/intro-
spect disabled. See notes.md for the platform adaptations and patch history.

Adapted to HarmonyOS PC (aarch64). See notes.md for the platform notes.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class Gtk4Conan(ConanFile):
    name = "gtk4"
    version = "4.22.4"
    description = "GTK4 — GNOME 4 UI toolkit (Broadway backend, OHOS adaptation)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gtk"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gtk4 meson dependency() names → conan package names:
        #   glib-2.0 / gobject-2.0 / gio-2.0 / gmodule-2.0 → glib/2.84.0.1
        #       (pkg-config glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0; glib recipe
        #       declares all as components. Pango/harfbuzz/cairo chain pulls
        #       glib/2.84.0.1 → zlib/1.3.1.1; gtk4 MUST align to same glib
        #       (NOT glib2/2.88.0, which is a separate conan package pulling
        #       zlib/1.3.1 and triggering a zlib version conflict in the graph).
        #   pango / pangocairo → pango/1.56.4 (pkg-config pango, pangocairo;
        #       gtk4 4.22.4 meson requires pango >= 1.56, so 1.50.14.1 is NOT
        #       accepted — R1 first-error fix upgraded to 1.56.4, which ohpcd
        #       publishes for OHOS armv8 Release clang15 libc++ cppstd17)
        #   cairo → cairo/1.18.4 (pkg-config cairo)
        #   cairo-gobject → cairo-gobject/1.18.4 (pkg-config cairo-gobject;
        #       R10/R11 fix: gtk4 gdk/gdkdmabuftexturebuilder.c etc. genuinely
        #       use CAIRO_GOBJECT_TYPE_REGION/RECTANGLE_INT macros, so a
        #       forwarded cairo-gobject.pc alone is NOT enough — the real
        #       cairo-gobject package (glib=enabled, ships cairo-gobject.h +
        #       libcairo-gobject) is required. cairo/1.18.4 disables glib,
        #       hence no cairo-gobject.h in the cairo package.)
        #   harfbuzz (with glib integration) → harfbuzz/14.2.0.1
        #       (pango/1.50.14.1 pins harfbuzz/14.2.0.1; using 14.2.0 triggers
        #       a version conflict. harfbuzz/14.2.0.1 pulls glib/2.84.0.1 with
        #       shared=False on OHOS, so gtk4 must request the same static
        #       glib option to avoid an options conflict in the graph.)
        #   gdk-pixbuf-2.0 → gdk-pixbuf/2.44.6 (pkg-config gdk-pixbuf-2.0)
        #   graphene-1.0 / graphene-gobject-1.0 → graphene/1.10.8
        #       (R3 fix: MUST be a normal require, NOT override=True — conan
        #       treats override as "version-pin only, not a direct dependency",
        #       so graphene never entered the graph and no graphene-1.0.pc was
        #       generated, meson aborted at dependency('graphene-gobject-1.0').
        #       graphene recipe requires glib2/2.88.0 → zlib/1.3.1; zlib override
        #       below forces the whole graph onto zlib/1.3.1.1 to avoid the R1
        #       zlib version conflict resurfacing.)
        #   fribidi → fribidi/1.0.16 (pkg-config fribidi)
        #   epoxy → libepoxy/1.5.10 (pkg-config epoxy; gtk4 meson uses 'epoxy')
        # Versions pinned to the published/ohpcd consumable recipe versions.
        # glib/2.84.0.1.1 shared=True is the FIXED hard constraint for this
        # round (r85/r86). The glib/2.84.0.1.1 recipe supports shared and its
        # default is shared=True; on OHOS the .so is re-signed by the recipe's
        # _sign_shared_libs so HarmonyOS dlopen works. override=True unifies
        # pango/harfbuzz/cairo-gobject/graphene's glib version pins onto
        # 2.84.0.1.1 and forces the shared option graph-wide. NO glib/2.88.0
        # and NO glib2/2.88.0 anywhere in the graph.
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        # R3 fix: pin the whole graph to one zlib. graphene/1.10.8 requires
        # glib2/2.88.0 → zlib/1.3.1, while the pango/harfbuzz/glib chain pulls
        # zlib/1.3.1.1; without this override the graph re-resolves both and
        # conan aborts with the R1 zlib version conflict again.
        self.requires("zlib/1.3.1.1", override=True)
        # R12 fix: pango/1.56.4 pulls fontconfig/2.18.1 (no force), while
        # cairo-gobject/1.18.4 + cairo/1.18.4 require fontconfig/2.18.1.1 —
        # conan aborts with a fontconfig version conflict. Pin the whole
        # graph to 2.18.1.1 (the cairo/cairo-gobject revision, same as the
        # archived pango/1.50.14.1 recipe's force=True choice).
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("pango/1.56.4", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("cairo-gobject/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("harfbuzz/14.2.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6", transitive_headers=True, transitive_libs=True)
        self.requires("graphene/1.10.8", transitive_headers=True, transitive_libs=True)
        self.requires("fribidi/1.0.16", transitive_headers=True, transitive_libs=True)
        self.requires("libepoxy/1.5.10", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # MesonToolchain doesn't write ar/ranlib into the native file from
        # tools.build:compiler_executables; meson then probes bare llvm-ar
        # (not on PATH on OHOS — clang toolchain is in /data/service/hnp/bin).
        # Pin the real tools by ABSOLUTE PATH and drop broken env values.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        # Generate .pc files for the conan deps so meson's dependency() probes
        # find them via pkg-config (PkgConfigDeps honors cpp_info pkg_config_name).
        PkgConfigDeps(self).generate()
        # gtk4 meson dependency() probes names that the conan deps do NOT
        # directly expose as pkg_config_name — forward them from the .pc files
        # that DID get generated:
        #   graphene-gobject-1.0 → backed by graphene-1.0.pc
        #     (graphene recipe only declares pkg_config_name=graphene-1.0;
        #     its gobject component is NOT a separate pkg_config_name)
        # NOTE: cairo-gobject is now a REAL dependency (cairo-gobject/1.18.4,
        #     R10/R11 fix), so cairo-gobject.pc comes from the package itself —
        #     no forwarding needed. glib/2.84.0.1 declares gobject-2.0/gio-2.0/
        #     gmodule-2.0 components, so PkgConfigDeps generates those .pc —
        #     no forwarding needed for glib either.
        #   pangocairo / pangoft2 → backed by pango.pc
        #     (pango/1.56.4 recipe only declares pkg_config_name=pango with libs
        #     pango-1.0/pangocairo-1.0/pangoft2-1.0; it declares NO separate
        #     pangocairo/pangoft2 components, so PkgConfigDeps generates no
        #     pangocairo.pc/pangoft2.pc. gtk4 meson probes dependency('pangocairo')
        #     (required) and dependency('pangoft2'); without these forwards
        #     meson configure aborts with "Subproject pango is buildable: NO".)
        # NOTE: glib/2.84.0.1 recipe DOES declare gobject-2.0/gio-2.0/gmodule-2.0
        # as separate components with their own pkg_config_name, so PkgConfigDeps
        # already generates those .pc files — NO forwarding needed for glib.
        self._forward_pc(
            "graphene-1.0",
            "graphene-gobject-1.0",
            requires="graphene-1.0",
            extra_lines=[
                "graphene_has_sse2=0",
                "graphene_has_gcc=0",
                "graphene_has_neon=1",
                "graphene_has_scalar=1",
            ],
        )
        self._forward_pc("pango", "pangocairo", requires="pango")
        self._forward_pc("pango", "pangoft2", requires="pango")
        tc = MesonToolchain(self)
        self._tc = tc
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Don't allow meson to fetch network wraps; deps are all conan-provided.
        tc.project_options["wrap_mode"] = "nodownload"
        # OHOS has no window system / EGL / Vulkan / media / print / colord.
        tc.project_options["wayland-backend"] = "false"
        tc.project_options["x11-backend"] = "false"
        tc.project_options["broadway-backend"] = "true"
        tc.project_options["vulkan"] = "disabled"
        tc.project_options["media-gstreamer"] = "disabled"
        tc.project_options["print-cups"] = "disabled"
        tc.project_options["print-cpdb"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["build-tests"] = "false"
        tc.project_options["build-testsuite"] = "false"
        tc.project_options["build-demos"] = "false"
        tc.project_options["build-examples"] = "false"
        tc.project_options["man-pages"] = "false"
        tc.project_options["documentation"] = "false"
        tc.project_options["colord"] = "disabled"
        tc.project_options["tracker"] = "disabled"
        tc.project_options["sysprof"] = "disabled"
        tc.project_options["cloudproviders"] = "disabled"
        tc.project_options["accesskit"] = "disabled"
        tc.project_options["f16c"] = "disabled"
        tc.project_options["screenshots"] = "false"
        # gdbus-codegen 必须在 tc.generate() 之前注入 binaries（native file 才生效）
        self._prepend_glib_bin_to_path()
        tc.generate()
        self._inject_meson_archiver()
        self._fix_glib_pcs()
        self._fix_fribidi_pc()
        self._fix_cairo_gobject_pc()

    def _fix_cairo_gobject_pc(self):
        # R15/R3 fix: gtk4's gdkdmabuftexturebuilder.c includes <cairo-gobject.h>
        # which does `#if CAIRO_HAS_GOBJECT_FUNCTIONS ... #else #error`. The
        # cairo-gobject PACKAGE ships the REAL header (with CAIRO_GOBJECT_TYPE_*
        # macros), but the header first #include <cairo.h>, and on OHOS the cairo
        # include dir (cairo/1.18.4, glib=disabled → cairo-features.h without
        # CAIRO_HAS_GOBJECT_FUNCTIONS) is earlier on the include path, so the
        # macro is undefined and the stub #error branch is taken. Inject
        # -DCAIRO_HAS_GOBJECT_FUNCTIONS=1 into cairo-gobject.pc Cflags so the
        # real gobject branch (CAIRO_GOBJECT_TYPE_REGION etc.) is used.
        pc = os.path.join(self.generators_folder, "cairo-gobject.pc")
        if not os.path.isfile(pc):
            return
        with open(pc, encoding="utf-8") as _f:
            text = _f.read()
        if "CAIRO_HAS_GOBJECT_FUNCTIONS=1" in text:
            return
        if "Cflags:" in text:
            text = text.replace(
                "Cflags:", "Cflags: -DCAIRO_HAS_GOBJECT_FUNCTIONS=1", 1
            )
        else:
            text += "Cflags: -DCAIRO_HAS_GOBJECT_FUNCTIONS=1\n"
        with open(pc, "w", encoding="utf-8") as _f:
            _f.write(text)
        self.output.info("cairo-gobject.pc: appended -DCAIRO_HAS_GOBJECT_FUNCTIONS=1 to Cflags")

    def _fix_fribidi_pc(self):
        # R9 fix: fribidi's public headers live in include/fribidi/ (gtk4's
        # gdk/gdk.c does #include <fribidi.h>), but PkgConfigDeps generates
        # fribidi.pc with only -I${includedir} (no -I${includedir}/fribidi),
        # so the compile fails "fribidi.h file not found". Append the
        # subdir include to Cflags (mirrors upstream fribidi.pc).
        pc = os.path.join(self.generators_folder, "fribidi.pc")
        if not os.path.isfile(pc):
            return
        with open(pc, encoding="utf-8") as _f:
            text = _f.read()
        if "include/fribidi" in text:
            return
        if "Cflags:" in text:
            text = text.replace(
                "Cflags:", "Cflags: -I${includedir}/fribidi", 1
            )
        else:
            text += "Cflags: -I${includedir}/fribidi\n"
        with open(pc, "w", encoding="utf-8") as _f:
            _f.write(text)
        self.output.info("fribidi.pc: appended -I${includedir}/fribidi to Cflags")

    def _prepend_glib_bin_to_path(self):
        # R7/R8 fix: /data/service/hnp/bin/gdbus-codegen is a broken symlink —
        # its target's shebang is #!/usr/bin/python3 but OHOS has no
        # /usr/bin/python3 (python3 lives in /storage/Users/currentUser/
        # usr/local/bin). gtk4's atspi build uses find_program('gdbus-codegen');
        # a bare PATH prepend is insufficient because conan's profile buildenv
        # re-prepends /data/service/hnp/bin (the broken entry) on top. The
        # reliable fix is to pin the WORKING gdbus-codegen into the meson
        # native file [binaries] section — find_program() consults native/cross
        # files before PATH. The glib conan package ships a working
        # gdbus-codegen (#!/usr/bin/env python3). Only touches the child build
        # environment, not glib.
        import os as _os
        if not getattr(self, "dependencies", None):
            return
        _g = self.dependencies.get("glib")
        if not _g or not getattr(_g, "package_folder", None):
            return
        _gbin = _os.path.join(_g.package_folder, "bin")
        _gdbus = _os.path.join(_gbin, "gdbus-codegen")
        if _os.path.isfile(_gdbus):
            self._tc.binaries["gdbus-codegen"] = _gdbus
            self.output.info("native file: gdbus-codegen -> %s" % _gdbus)
        if _os.path.isdir(_gbin):
            _os.environ["PATH"] = _gbin + _os.pathsep + _os.environ.get("PATH", "")
            self.output.info("PATH prepended with glib bin: %s" % _gbin)
        # R85/R86 fix (glib/2.84.0.1.1 shared): the glib package's bin tools
        # (glib-compile-resources / glib-compile-schemas / glib-mkenums / …)
        # are OHOS aarch64 ELF executables whose linker-time .codesign is
        # stale — OHOS XPM exec rejects them with "Operation not permitted"
        # (ninja FAILED [code=126] at gdk/gdkresources.c/h). Re-sign them
        # in-place (same ML-0043 recipe pattern used for .so post-install) so
        # gnome.compile_resources / compile_schemas can run. They also have no
        # RPATH, so glib's own shared libs must be on LD_LIBRARY_PATH at exec
        # time ("Error loading shared library libgio-2.0.so.0" otherwise).
        _objcopy = "/data/service/hnp/bin/llvm-objcopy"
        _signer = "/data/service/hnp/bin/binary-sign-tool"
        _glib = _os.path.join(_g.package_folder, "lib")
        _os.environ["LD_LIBRARY_PATH"] = _glib + _os.pathsep + _os.environ.get("LD_LIBRARY_PATH", "")
        self.output.info("LD_LIBRARY_PATH prepended with glib lib: %s" % _glib)
        for _tool in _os.listdir(_gbin):
            _tp = _os.path.join(_gbin, _tool)
            if not _os.path.isfile(_tp):
                continue
            with open(_tp, "rb") as _f:
                _magic = _f.read(4)
            if _magic[:4] != b"\x7fELF":
                continue  # e.g. gdbus-codegen shebang script — leave alone
            try:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=_objcopy, f=_tp))
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=_signer, f=_tp))
                self.output.info("re-signed glib bin tool: %s" % _tp)
            except Exception as _e:  # pragma: no cover — non-blocking
                self.output.warning("re-sign %s failed: %s" % (_tp, _e))

    def _fix_glib_pcs(self):
        # Conan PkgConfigDeps 生成的 glib-2.0.pc/gio-2.0.pc 不带工具变量。
        # gtk4 的 gnome.mkenums（gtk/css）读 glib_mkenums；gnome.compile_resources
        # （gdk/meson.build）读 glib_compile_resources（经 gio-2.0.pc）。
        # 缺失时报 "Could not get pkg-config variable and no default provided"。
        # 按 glib 包内真实 .pc（glibd11a5a8e754a2/p/lib/pkgconfig）补全变量。
        inject = {
            "glib-2.0.pc": {
                "glib_mkenums": "${bindir}/glib-mkenums",
                "glib_genmarshal": "${bindir}/glib-genmarshal",
                "gobject_query": "${bindir}/gobject-query",
            },
            "gio-2.0.pc": {
                "glib_compile_resources": "${bindir}/glib-compile-resources",
                "glib_compile_schemas": "${bindir}/glib-compile-schemas",
                "gdbus_codegen": "${bindir}/gdbus-codegen",
            },
        }
        for pc_name, vars_map in inject.items():
            pc = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc):
                self.output.warning("fix %s: file not generated, skip" % pc_name)
                continue
            with open(pc, encoding="utf-8") as _f:
                text = _f.read()
            if all(k + "=" in text for k in vars_map):
                continue
            lines = text.splitlines(True)
            out = []
            for line in lines:
                out.append(line)
                if line.startswith("bindir="):
                    for k, v in vars_map.items():
                        if k + "=" not in text:
                            out.append("%s=%s\n" % (k, v))
            with open(pc, "w", encoding="utf-8") as _f:
                _f.write("".join(out))
            self.output.info("%s: injected %d tool variables" % (pc_name, len(vars_map)))
        # R15 fix: glib/2.88.0 R21 的 gio-2.0 组件 includedirs 只含
        # include/glib-2.0 与 lib/glib-2.0/include，缺 include/gio-unix-2.0
        # （glib/2.84.0.1 的 gio-2.0 includedirs 含 include/gio-unix-2.0）。
        # gtk4 broadway backend（gdk/broadway/broadwayd.c、gdkbroadway-server.c）
        # include <gio/gunixfdmessage.h>（位于 include/gio-unix-2.0/gio/），
        # 缺该路径 → fatal error: 'gio/gunixfdmessage.h' file not found。
        # 在 gio-2.0.pc 的 Cflags 追加 -I${prefix}/include/gio-unix-2.0。
        pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if os.path.isfile(pc):
            with open(pc, encoding="utf-8") as _f:
                text = _f.read()
            if "gio-unix-2.0" not in text:
                if "Cflags:" in text:
                    text = text.replace(
                        "Cflags:",
                        "Cflags: -I${prefix}/include/gio-unix-2.0", 1
                    )
                else:
                    text += "Cflags: -I${prefix}/include/gio-unix-2.0\n"
                with open(pc, "w", encoding="utf-8") as _f:
                    _f.write(text)
                self.output.info("gio-2.0.pc: appended -I${prefix}/include/gio-unix-2.0 to Cflags")
        # R15/R4 fix: gtk4's glib-2.0.pc Cflags only carries
        # include/glib-2.0 + lib/glib-2.0/include (missing the package-root
        # `include` dir). gtk/gtkplacesviewrow.c uses dngettext() from the
        # proxy-libintl stub header <libintl.h> which lives in the package-root
        # include/; without -I${prefix}/include the declaration is unreachable
        # → "call to undeclared function 'dngettext'". Append the root include.
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(pc):
            with open(pc, encoding="utf-8") as _f:
                text = _f.read()
            if "-I${prefix}/include " not in text and "\nCflags:" in text:
                if "Cflags:" in text and "-I${prefix}/include " not in text:
                    text = text.replace(
                        "Cflags:",
                        "Cflags: -I${prefix}/include ", 1
                    )
                    with open(pc, "w", encoding="utf-8") as _f:
                        _f.write(text)
                    self.output.info("glib-2.0.pc: appended -I${prefix}/include to Cflags")

    def _forward_pc(self, src_name, dst_name, requires=None, extra_lines=None):
        # Forward a dependency .pc (src_name.pc) under an alternate name
        # (dst_name.pc) so meson dependency(dst_name) probes hit it. Inherits
        # Version/Cflags/Libs from src; adds a Requires line if given.
        src = os.path.join(self.generators_folder, "%s.pc" % src_name)
        if not os.path.isfile(src):
            self.output.warning(
                "forward %s: source %s.pc not generated, skip"
                % (dst_name, src_name)
            )
            return
        dst = os.path.join(self.generators_folder, "%s.pc" % dst_name)
        if os.path.isfile(dst):
            return
        with open(src, encoding="utf-8") as _f:
            body = _f.read()
        # Replace the Name: line with the forwarded name; keep Version/Cflags/Libs.
        import re as _re
        body = _re.sub(r"^Name: .*$", "Name: %s" % dst_name, body, count=1, flags=_re.M)
        if requires and "Requires:" not in body:
            body += "Requires: %s\n" % requires
        elif requires:
            body = _re.sub(
                r"^Requires: .*$",
                "Requires: %s, %s" % (requires, _re.search(r"^Requires: (.*)$", body, flags=_re.M).group(1)),
                body,
                count=1,
                flags=_re.M,
            )
        # Append pkg-config variables required by the consuming meson project.
        # gtk4 meson.build reads graphene_has_sse2/graphene_has_gcc via
        # get_variable(pkgconfig:) — values must match the graphene package's
        # actual SIMD configuration (OHOS armv8: sse2=0, gcc=0, neon=1, scalar=1).
        if extra_lines:
            body += "\n%s\n" % "\n".join(extra_lines)
        with open(dst, "w", encoding="utf-8") as _f:
            _f.write(body)
        self.output.info(
            "forwarded pkg-config: %s.pc -> %s.pc (Version inherited)" % (src_name, dst_name)
        )

    def _inject_meson_archiver(self):
        # belt-and-suspenders: also write ar/ranlib into conan_meson_native.ini
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            if _bindir:
                _cand = os.path.join(_bindir, "llvm-ar")
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(_bindir, "llvm-ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (_ar and os.path.isfile(_nf)):
            return
        with open(_nf, encoding="utf-8") as _f:
            _c = _f.read()
        if "\nar =" in _c or "[binaries]" not in _c:
            return
        _ins = "[binaries]\nar = '%s'\n" % _ar
        if _rl:
            _ins += "ranlib = '%s'\n" % _rl
        with open(_nf, "w", encoding="utf-8") as _f:
            _f.write(_c.replace("[binaries]\n", _ins, 1))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # gtk4 meson build-tests=false → no upstream meson test suite to run.
        # cross_building OHOS binaries are not runnable on the build host.

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # meson install rewrites rpath and mutates .so post-link → the linker
        # self-sign breaks; OHOS XPM dlopen then reports Permission denied.
        # Strip old .codesign + binary-sign-tool -selfSign 1 re-sign (ML-0043).
        import glob as _glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = _glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += _glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        # gtk4 public headers live under include/gtk-4.0 (meson install prefix).
        self.cpp_info.includedirs = ["include/gtk-4.0"]
        self.cpp_info.libs = ["gtk-4"]
        self.cpp_info.set_property("cmake_file_name", "gtk4")
        self.cpp_info.set_property("cmake_target_name", "gtk4::gtk4")
        self.cpp_info.set_property("pkg_config_name", "gtk4")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
