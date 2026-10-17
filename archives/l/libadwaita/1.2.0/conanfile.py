#!/usr/bin/env python3
"""Conan recipe — libadwaita 1.2.0 (Meson).

libadwaita is the GNOME Adwaita theme widget library built on GTK4.
On HarmonyOS PC (aarch64) it is a pure library (no binaries), built
against the published ohpcd gtk4/4.22.4 (Broadway backend) + glib
chain. Meson build; introspection/vapi/gtk_doc/examples are disabled
for the OHOS cross build; upstream tests are compiled with -Dtests=true.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibadwaitaConan(ConanFile):
    name = "libadwaita"
    version = "1.2.0"
    description = "libadwaita — GNOME Adwaita theme widgets for GTK4 (OHOS adaptation)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libadwaita"

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

    def build_requirements(self):
        # libadwaita's src/stylesheet/meson.build needs sassc to compile
        # base.scss → base.css (only when base.css is absent from the source
        # tree, which is the case for git-archive tarballs). On OHOS there is
        # no git subproject clone (meson would try `git clone
        # github.com/lazka/sassc.git` and fail), so provide the published
        # ohpcd sassc/3.6.2 as a build-time tool → meson find_program('sassc')
        # succeeds and the subproject branch is skipped.
        if self._conanfile_requires_sassc():
            self.tool_requires("sassc/3.6.2")

    def _conanfile_requires_sassc(self):
        return True

    def requirements(self):
        # libadwaita 1.2.0 meson dependency() names → conan packages:
        #   gtk4 (>= 4.5.0)   → gtk4/4.22.4 (transitive headers/libs so the
        #       consumer-facing headers' gtk4 includes resolve)
        #   glib-2.0/gio-2.0  → glib/2.84.0.1.1 shared=True — the SAME graph
        #       constraint gtk4/4.22.4 uses (override=True unifies the
        #       pango/harfbuzz/cairo-gobject/graphene glib pins; .1.1's
        #       bin tools are codesigned so glib-compile-resources etc. run
        #       on OHOS — the plain 2.84.0.1 package ships a broken
        #       (unsigned) tool binary: "Operation not permitted").
        #       harfbuzz is then built from source by --build=missing
        #       (identical to CI build_and_test.sh policy).
        #   fribidi           → fribidi/1.0.16 (transitive)
        self.requires("gtk4/4.22.4", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        # gtk4 recipe pins the whole graph onto one zlib/fontconfig revision;
        # propagate the same pins so this graph resolves identically.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("fribidi/1.0.16", transitive_headers=True, transitive_libs=True)

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
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # OHOS: disable introspection/vapi/gtk_doc/examples (no GI/Vala/display
        # on the cross target); keep tests enabled for the upstream suite.
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["examples"] = "false"
        tc.project_options["tests"] = "true"
        tc.generate()
        self._inject_meson_archiver()
        self._patch_pc_datadir()
        self._prepend_glib_bin_to_path()
        self._fix_fribidi_pc()

    def _fix_fribidi_pc(self):
        # fribidi.h lives in include/fribidi/ (meson dependency('fribidi')
        # compiles adw-bidi.c with `#include <fribidi.h>`); the PkgConfigDeps
        # generated fribidi.pc only carries -I${includedir} — same issue gtk4
        # fixed. Append the subdir include to Cflags.
        _pc = os.path.join(self.generators_folder, "fribidi.pc")
        if not os.path.isfile(_pc):
            return
        with open(_pc, encoding="utf-8") as _f:
            _txt = _f.read()
        if "-I${includedir}/fribidi" in _txt:
            return
        if "Cflags:" in _txt:
            _txt = _txt.replace("Cflags:", "Cflags: -I${includedir}/fribidi", 1)
        else:
            _txt += "Cflags: -I${includedir}/fribidi\n"
        with open(_pc, "w", encoding="utf-8") as _f:
            _f.write(_txt)
        self.output.info("fribidi.pc: appended -I${includedir}/fribidi to Cflags")

    def _prepend_glib_bin_to_path(self):
        # glib/2.84.0.1.1 shared: the glib package's bin tools
        # (glib-compile-resources / glib-compile-schemas / glib-mkenums / …)
        # are OHOS aarch64 ELF executables whose linker-time .codesign is
        # stale — OHOS XPM exec rejects them with "Operation not permitted"
        # (ninja FAILED [code=126]). Re-sign them in-place (same ML-0043
        # pattern as gtk4) so gnome.compile_resources can run. They also have
        # no RPATH, so glib's own shared libs must be on LD_LIBRARY_PATH at
        # exec time ("Error loading shared library libgio-2.0.so.0").
        import os as _os
        _g = (getattr(self, "dependencies", None) or {}).get("glib")
        if not _g or not getattr(_g, "package_folder", None):
            return
        _gbin = _os.path.join(_g.package_folder, "bin")
        _glib = _os.path.join(_g.package_folder, "lib")
        if _os.path.isdir(_gbin):
            _os.environ["PATH"] = _gbin + _os.pathsep + _os.environ.get("PATH", "")
            self.output.info("PATH prepended with glib bin: %s" % _gbin)
        _os.environ["LD_LIBRARY_PATH"] = _glib + _os.pathsep + _os.environ.get("LD_LIBRARY_PATH", "")
        self.output.info("LD_LIBRARY_PATH prepended with glib lib: %s" % _glib)
        _objcopy = "/data/service/hnp/bin/llvm-objcopy"
        _signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (_os.path.isdir(_gbin) and _os.path.isfile(_signer)):
            return
        for _tool in _os.listdir(_gbin):
            _tp = _os.path.join(_gbin, _tool)
            if not _os.path.isfile(_tp):
                continue
            with open(_tp, "rb") as _f:
                _magic = _f.read(4)
            if _magic[:4] != b"\x7fELF":
                continue  # shebang scripts (gdbus-codegen etc.) — leave alone
            try:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=_objcopy, f=_tp))
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=_signer, f=_tp))
                self.output.info("re-signed glib bin tool: %s" % _tp)
            except Exception as _e:  # pragma: no cover — non-blocking
                self.output.warning("re-sign %s failed: %s" % (_tp, _e))

    def _patch_pc_datadir(self):
        # gnome.compile_resources() resolves its helper tools via the
        # gio-2.0.pc pkg-config variables glib_compile_resources /
        # glib_compile_schemas / gio_querymodules / gdbus_codegen (meson
        # find_tool with no default) — the PkgConfigDeps generated .pc lacks
        # them → meson aborts "Could not get pkg-config variable and no
        # default provided for <PkgConfigDependency gio-2.0>". Append the
        # tool variables (and datadir for resource install dirs) to the
        # generated .pc files.
        _tool_vars = {
            "gio-2.0.pc": [
                "glib_compile_resources=${prefix}/bin/glib-compile-resources",
                "glib_compile_schemas=${prefix}/bin/glib-compile-schemas",
                "gio_querymodules=${prefix}/bin/gio-querymodules",
                "gdbus_codegen=${prefix}/bin/gdbus-codegen",
            ],
            "glib-2.0.pc": [
                "glib_genmarshal=${prefix}/bin/glib-genmarshal",
                "glib_mkenums=${prefix}/bin/glib-mkenums",
            ],
        }
        for _pc, _vars in _tool_vars.items():
            _f = os.path.join(self.generators_folder, _pc)
            if not os.path.isfile(_f):
                continue
            with open(_f, encoding="utf-8") as _fh:
                _txt = _fh.read()
            _extra = []
            if "datadir=" not in _txt:
                _extra.append("datadir=${prefix}/share")
            for _v in _vars:
                _vn = _v.split("=", 1)[0]
                if _vn not in _txt:
                    _extra.append(_v)
            if not _extra:
                continue
            # insert variables right after the prefix/libdir line block
            _lines = _txt.splitlines(keepends=True)
            _ins = []
            for _ln in _lines:
                _ins.append(_ln)
                if _ln.startswith(("prefix=", "libdir=", "bindir=")) and _extra:
                    for _v in list(_extra):
                        _ins.append(_v + "\n")
                    _extra = []
            _txt = "".join(_ins)
            with open(_f, "w", encoding="utf-8") as _fh:
                _fh.write(_txt)
            self.output.info("%s: appended tool/datadir vars" % _pc)

    def _inject_meson_archiver(self):
        # MesonToolchain doesn't write ar/ranlib into the native file from
        # tools.build:compiler_executables; meson then probes bare llvm-ar /
        # ar / gar (not on PATH on OHOS — clang toolchain is in
        # /data/service/hnp/bin) → configure aborts with "No such file or
        # directory: 'llvm-ar'". Pin the real archiver by ABSOLUTE PATH.
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
        self.output.info("injected ar/ranlib into conan_meson_native.ini")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

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
        # libadwaita public headers live under include/libadwaita-1
        # (meson package_api_name = libadwaita-1); library is libadwaita-1.so.
        self.cpp_info.includedirs = ["include/libadwaita-1"]
        self.cpp_info.libs = ["adwaita-1"]
        self.cpp_info.set_property("cmake_file_name", "libadwaita")
        self.cpp_info.set_property("cmake_target_name", "libadwaita::libadwaita")
        self.cpp_info.set_property("pkg_config_name", "libadwaita-1")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
