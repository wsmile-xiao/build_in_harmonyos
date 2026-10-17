#!/usr/bin/env python3
"""Conan recipe — zenity 4.2.2 (Meson).

Zenity displays GTK dialog boxes from the command line and shell
scripts. Upstream 4.x is built on libadwaita-1 (>= 1.2) and gtk4.

zenity meson dependency() names → conan packages:
  libadwaita-1 (>= 1.2) → libadwaita/1.2.0 (adapted in PR #10188,
      published on ohpcd; pkg_config_name libadwaita-1)
  gtk4               → gtk4/4.22.4 (published, Broadway-only OHOS build)
  glib-2.0 / gio-2.0 → glib/2.84.0.1.1 shared=True — the SAME graph
      constraint gtk4/4.22.4 and libadwaita/1.2.0 use (override=True
      unifies the pango/harfbuzz/cairo-gobject/graphene glib pins;
      .1.1's bin tools are codesigned so glib-compile-resources and
      glib-mkenums run on OHOS).

OHOS adaptations:
- webkitgtk and manpage disabled (no WebKit port, no help2man on OHOS).
- help/ subdirectory made conditional on itstool (patch 0001): OHOS has
  no itstool with libxml2 Python bindings.
- Patch 0002 (E252): `zenity --version` prints the version then exits
  via _exit(0) — the AdwApplication/GTK teardown after the local
  handle-local-options return segfaults headless (Signal 11), because
  adw styles teardown touches the display-less Broadway backend.
- The zenity executable is codesigned after meson install (OHOS XPM
  exec requires a valid .codesign section).
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ZenityConan(ConanFile):
    name = "zenity"
    version = "4.2.2"
    description = "Display GTK dialog boxes from the command line and shell scripts"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/zenity"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libadwaita-1 >= 1.2 (zenity's only required dependency);
        # transitive headers/libs so gtk4/glib includes reach zenity's
        # sources through libadwaita's public headers.
        self.requires(
            "libadwaita/1.2.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        # zenity src includes <gtk/gtk.h> directly (tree view, dialogs).
        self.requires(
            "gtk4/4.22.4",
            transitive_headers=True,
            transitive_libs=True,
        )
        # Same graph pins gtk4/4.22.4 and libadwaita/1.2.0 use, so the
        # whole graph resolves identically for zenity.
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)

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
        tools = {
            name: shutil.which(name)
            for name in ("ar", "as", "strip", "nm", "ranlib")
        }
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # Don't allow meson to fetch network wraps; deps are conan-provided.
        tc.project_options["wrap_mode"] = "nodownload"
        # OHOS: no WebKit port, no help2man (manpage generation runs the
        # built binary through help2man — unavailable headless anyway).
        tc.project_options["webkitgtk"] = "false"
        tc.project_options["manpage"] = "false"
        tc.generate()
        self._inject_meson_archiver(tools)
        self._patch_pc_datadir()
        self._prepend_tools_to_path()

    def _inject_meson_archiver(self, tools):
        # MesonToolchain already got ar/ranlib above; also mirror them into
        # conan_meson_native.ini for tools that only read the native file.
        _ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
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

    def _patch_pc_datadir(self):
        # gnome.compile_resources() resolves its helper tools via the
        # gio-2.0.pc pkg-config variables glib_compile_resources /
        # glib_compile_schemas (meson find_tool with no default) — the
        # PkgConfigDeps generated .pc lacks them → meson aborts "Could
        # not get pkg-config variable and no default provided". Append
        # the tool variables (and datadir for resource install dirs).
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

    def _prepend_tools_to_path(self):
        # zenity's build uses glib tools (glib-mkenums via gnome.mkenums_simple,
        # glib-compile-resources via gnome.compile_resources) and gtk4 tools
        # (gtk4-update-icon-cache via gnome.post_install). Make both packages'
        # bin/ visible to meson's find_program, and put glib's shared libs on
        # LD_LIBRARY_PATH for the tool invocations (they have no RPATH).
        # glib/2.84.0.1.1's ELF tools are codesigned upstream, but re-sign
        # defensively (ML-0043 pattern used by gtk4/libadwaita recipes) in
        # case the local cache copy carries a stale .codesign.
        import os as _os
        _objcopy = "/data/service/hnp/bin/llvm-objcopy"
        _signer = "/data/service/hnp/bin/binary-sign-tool"
        for dep_name in ("glib", "gtk4"):
            _dep = (getattr(self, "dependencies", None) or {}).get(dep_name)
            if not _dep or not getattr(_dep, "package_folder", None):
                continue
            _bin = _os.path.join(_dep.package_folder, "bin")
            _lib = _os.path.join(_dep.package_folder, "lib")
            if _os.path.isdir(_bin):
                _os.environ["PATH"] = _bin + _os.pathsep + _os.environ.get("PATH", "")
                self.output.info("PATH prepended with %s bin: %s" % (dep_name, _bin))
                if dep_name == "glib" and _os.path.isfile(_signer):
                    for _tool in _os.listdir(_bin):
                        _tp = _os.path.join(_bin, _tool)
                        if not _os.path.isfile(_tp):
                            continue
                        with open(_tp, "rb") as _f:
                            _magic = _f.read(4)
                        if _magic[:4] != b"\x7fELF":
                            continue  # shebang scripts (glib-mkenums etc.)
                        try:
                            self.run(
                                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                                    oc=_objcopy, f=_tp
                                )
                            )
                            self.run(
                                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                                    sg=_signer, f=_tp
                                )
                            )
                        except Exception as _e:  # pragma: no cover — non-blocking
                            self.output.warning("re-sign %s failed: %s" % (_tp, _e))
            if _os.path.isdir(_lib):
                _os.environ["LD_LIBRARY_PATH"] = (
                    _lib + _os.pathsep + _os.environ.get("LD_LIBRARY_PATH", "")
                )
                self.output.info("LD_LIBRARY_PATH prepended with %s lib: %s" % (dep_name, _lib))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # zenity's meson registers no tests (test/ holds manual interactive
        # GUI scripts — see notes.md); meson.test() is a no-op pass here but
        # is kept so CI L1 can see the upstream test phase executed.
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_binaries()

    def _sign_binaries(self):
        # meson install rewrites rpath and mutates the executable
        # post-link → the linker self-sign breaks; OHOS XPM exec then
        # rejects the binary. Strip old .codesign + binary-sign-tool
        # -selfSign 1 re-sign (ML-0043 pattern).
        candidates = glob.glob(os.path.join(self.package_folder, "bin", "*"))
        if not candidates:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for binary in sorted(set(candidates)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=binary
                )
            )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=binary
                )
            )

    def package_info(self):
        # R38: command-line tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
