#!/usr/bin/env python3
"""Conan recipe — gdk-pixbuf 2.44.6.1.1 (meson).

Adaptation-fix revision of the 2.44.6 recipe (R37): registry already hosts
gdk-pixbuf/2.44.6 (published 2026-08-04, revision dd84a01a, libtiff-enabled)
and gdk-pixbuf/2.44.6.1 (published 2026-08-22, revision fa6c6d19, still
libtiff-enabled); this recipe disables tiff and uses the glib/libpng/libjpeg-turbo
dep set, so the version suffix is bumped again to 2.44.6.1.1 (cnb.cool cannot
host two revisions of the same version). Source stays the official 2.44.6 tarball.

GTK+ image loading library. Built with meson against conan glib/libpng/libjpeg-turbo.

OHOS adaptations:
  - The OHOS sysroot libintl.h is an empty stub; glib/2.84.0.1 ships a real
    libintl.h (in the glib package include dir) that redirects gettext/ngettext/
    bindtextdomain to its g_libintl_* proxy symbols exported by the glib
    package's libintl.so. gdk-pixbuf links that libintl.so via -lintl injected
    into the generated glib pc files.
  - loaders.cache custom_target and thumbnailer custom_target are disabled /
    replaced (patches/0001, 0002, 0003) so configure/build work without executing
    freshly built host binaries.
  - gio_sniffing/tiff/man/tests are disabled to avoid shared-mime-info / libtiff
    / rst2man / test-only dependencies.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GdkpixbufConan(ConanFile):
    name = "gdk-pixbuf"
    version = "2.44.6.1.1"
    description = "GTK+ image loading library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gdk-pixbuf"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libpng/1.6.58", transitive_headers=True, transitive_libs=True)
        self.requires("libjpeg-turbo/3.2.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as e:
            if not mirror_url:
                raise
            self.output.warning(f"Primary source failed ({e}), trying mirror")
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

    def _stage_glib_tool(self, name):
        """Copy a glib helper tool (python script) into the build dir so meson's
        gnome.genmarshal/gnome.mkenums can find it via a patched .pc variable."""
        source = os.path.join(self.dependencies["glib"].package_folder, "bin", name)
        tools_dir = os.path.join(self.build_folder, ".glib-tools")
        os.makedirs(tools_dir, exist_ok=True)
        target = os.path.join(tools_dir, name)
        if os.path.isfile(source) and not os.path.isfile(target):
            shutil.copy2(source, target)
            os.chmod(target, 0o755)
        return target

    def _patch_glib_pkg_config_variables(self):
        """PkgConfigDeps emits glib-2.0.pc/gobject-2.0.pc without the *_tool
        variables meson's gnome module reads (glib_genmarshal / glib_mkenums).
        Inject them pointing at the staged copies, and add -lintl to the Libs
        lines (glib's proxy-libintl exports the gettext symbols)."""
        import re
        variables = {
            "glib_genmarshal": self._stage_glib_tool("glib-genmarshal"),
            "glib_mkenums": self._stage_glib_tool("glib-mkenums"),
        }
        for pc_name in ("glib-2.0", "gobject-2.0"):
            glib_pc = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(glib_pc):
                continue
            with open(glib_pc, encoding="utf-8") as handle:
                content = handle.read()
            for variable, value in variables.items():
                if value and not os.path.isfile(value):
                    continue
                if re.search(rf"^{re.escape(variable)}=", content, flags=re.M):
                    content = re.sub(
                        rf"^{re.escape(variable)}=.*$", f"{variable}={value}", content, flags=re.M
                    )
                else:
                    content = f"{variable}={value}\n" + content
            if re.search(r"^Libs:.*-lintl", content, flags=re.M):
                content = content
            elif re.search(r"^Libs:", content, flags=re.M):
                content = re.sub(r"^Libs:.*$", lambda m: m.group(0) + " -lintl", content, count=1, flags=re.M)
            with open(glib_pc, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _write_gmodule_no_export_pc(self):
        """gdk-pixbuf's meson.build does dependency('gmodule-no-export-2.0').
        PkgConfigDeps only emits gmodule-2.0.pc from the glib recipe components,
        so synthesize the no-export .pc pointing at the glib package."""
        glib = self.dependencies["glib"]
        libdir = os.path.join(glib.package_folder, "lib")
        includedir = os.path.join(glib.package_folder, "include")
        content = (
            f"prefix={glib.package_folder}\n"
            f"libdir={libdir}\n"
            f"includedir={includedir}\n"
            "\n"
            "gmodule_supported=true\n"
            "\n"
            "Name: GModule (no export)\n"
            "Description: Dynamic module loader for GLib (no symbol export)\n"
            "Version: 2.84.0\n"
            "Requires: glib-2.0\n"
            f"Libs: -L${{libdir}} -lgmodule-2.0 -pthread\n"
            f"Cflags: -I${{includedir}}/glib-2.0 -I${{libdir}}/glib-2.0/include\n"
        )
        pc_path = os.path.join(self.generators_folder, "gmodule-no-export-2.0.pc")
        with open(pc_path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _inject_glib_bin_path(self):
        """meson.build calls find_program('glib-compile-resources') at configure
        time; make glib's bin/ (with glib-compile-resources) reachable."""
        bin_dir = os.path.join(self.dependencies["glib"].package_folder, "bin")
        if os.path.isdir(bin_dir):
            self.buildenv_info.prepend_path("PATH", bin_dir)

    def _inject_ar_ranlib(self):
        # MesonToolchain omits ar/ranlib; meson then cannot find llvm-ar/llvm-ranlib.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        ranlib = rlc
                        break
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar)
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib)
                content = content.replace("[binaries]\n", insertion, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _inject_pkg_config(self):
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if pkg_config and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\npkg-config =" not in content and "\npkgconfig =" not in content and "[binaries]" in content:
                content = content.replace(
                    "[binaries]\n", "[binaries]\npkg-config = '{}'\n".format(pkg_config), 1
                )
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._patch_glib_pkg_config_variables()
        self._write_gmodule_no_export_pc()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nofallback"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["gio_sniffing"] = False
        tc.project_options["tiff"] = "disabled"
        tc.project_options["tests"] = False
        tc.project_options["man"] = False
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        self._inject_ar_ranlib()
        self._inject_pkg_config()
        self._inject_glib_bin_path()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_elf_files()

    def _sign_elf_files(self):
        """Re-sign ELF files after meson install.

        meson install rewrites the RPATH (dynstr), which invalidates the
        toolchain's link-time .codesign; the loader then rejects the .so
        (EPERM). Re-apply a codesign with binary-sign-tool.
        NOTE: must run with env=None — the conanbuild env's LD_LIBRARY_PATH
        breaks the (Java-based) sign tool and produces an invalid signature."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        targets = []
        for top in ("bin", "lib"):
            base = os.path.join(self.package_folder, top)
            if not os.path.isdir(base):
                continue
            for root, _dirs, files in os.walk(base):
                for fname in files:
                    if fname.startswith("lib") and (fname.endswith(".so") or ".so." in fname):
                        targets.append(os.path.join(root, fname))
                    elif top == "bin":
                        targets.append(os.path.join(root, fname))
        for f in targets:
            if os.path.islink(f):
                continue
            try:
                if open(f, "rb").read(4) != b"\x7fELF":
                    continue
            except Exception:
                continue
            if os.path.isfile(objcopy):
                self.run('{oc} --remove-section .codesign "{f}"'.format(oc=objcopy, f=f),
                         env=None, quiet=True, ignore_errors=True)
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f),
                     env=None)

    def package_info(self):
        self.cpp_info.libs = ["gdk_pixbuf-2.0"]
        self.cpp_info.includedirs = ["include/gdk-pixbuf-2.0"]
        self.cpp_info.set_property("cmake_file_name", "gdk-pixbuf-2.0")
        self.cpp_info.set_property("cmake_target_name", "gdk-pixbuf-2.0::gdk-pixbuf-2.0")
        self.cpp_info.set_property("pkg_config_name", "gdk-pixbuf-2.0")
        # gdk-pixbuf.h includes glib headers; keep them visible to consumers.
        self.cpp_info.requires = [
            "glib::glib-2.0", "glib::gobject-2.0", "glib::gmodule-2.0", "glib::gio-2.0",
            "libpng::libpng", "libjpeg-turbo::libjpeg-turbo",
        ]
