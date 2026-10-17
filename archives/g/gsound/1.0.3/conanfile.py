#!/usr/bin/env python3
"""Conan recipe — gsound 1.0.3 (Meson).

GSound — a small GNOME library for playing system sounds, GObject wrapper
around libcanberra. Adapted to HarmonyOS PC (aarch64, musl, clang).

Build/downstream handling inherits the verified approaches of gssdp 1.6.6 /
gupnp 1.6.10 (same GLib meson stack), with one gsound-specific deviation:
  - static-only glib2 on ohpcd -> gsound does NOT link libsoup3, so unlike
    gssdp/gupnp it cannot lean on libsoup-3.0.so's GObject export table.
    Keep the static glib2 link list in the .pc Libs (only fix the broken
    prefix=): libgsound.so links the single glib copy directly; the
    single-copy doctrine is upheld by consumers not pulling a second
    GObject shared library;
  - never strip shared libraries (embedded .codesign hash breaks, dlopen
    Permission denied);
  - meson install rewrites DT_RUNPATH -> overwrite installed .so with the
    build-tree artifact.

gsound-specific:
  - introspection/vapi disabled (cross-compile, gobject-introspection not
    needed for a headless library package);
  - gtk_doc disabled (needs gi-docgen);
  - vala tools disabled (needs valac, not in toolchain);
  - depends only on glib2 + libcanberra (no libsoup3/gssdp/libxml2).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class GsoundConan(ConanFile):
    name = "gsound"
    version = "1.0.3"
    description = "GSound — small library for playing system sounds (GObject wrapper for libcanberra)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gsound"
    url = "https://download.gnome.org/sources/gsound/1.0/gsound-1.0.3.tar.xz"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "PkgConfigDeps"
    # 跳过 source->build 复制，避免 HMDFS 跨用户读权限失败
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gsound meson.build deps: gio-2.0, gobject-2.0 (from glib2), libcanberra.
        # No libsoup3/gssdp/libxml2 — gsound is a minimal wrapper.
        # ⚠️ zlib root-level override pins the PIC variant (1.3.1.1): the
        # published zlib/1.3.1 libz.a is not -fPIC and breaks when linked into
        # a shared .so (R_AARCH64 relocation error). Same rationale as
        # gssdp 1.6.6 / gupnp 1.6.10.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("glib2/2.88.0")
        self.requires("libcanberra/0.30")

    def build_requirements(self):
        # meson probes `ninja --version` during configure. The build profile
        # already prepends a static ninja on this host; the registry ninja
        # needs libc++_shared.so at load time and fails the probe in a clean
        # env, so we deliberately do NOT tool_require it. CI workers ship
        # their own system ninja.
        pass

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are
        # NOT on its PATH — meson probes them and aborts. Pin the real tools
        # by absolute PATH and drop the broken env values (same as
        # glib2/2.88.0, libsoup3/3.6.5-r1, gssdp/1.6.6).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name)
                 for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not in PATH: {', '.join(missing)}")

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # ⚠️ never strip shared libraries: the OHOS loader verifies the
        # embedded .codesign hash against the file content; strip rewrites the
        # .so and dlopen fails with Permission denied (libsoup3 evidence).
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # gsound meson options: introspection/vapi are gobject-introspection
        # (cross-compile disable), gtk_doc needs gi-docgen (disable), enable_vala
        # needs valac (not in toolchain — disable).
        for opt in ("introspection", "gtk_doc", "enable_vala"):
            tc.project_options[opt] = "false"

        # meson needs the real .pc files (gobject-2.0/gio-2.0) from the glib2
        # package — PkgConfigDeps only generates a single glib-2.0.pc (glib2's
        # pkg_config_name), and gsound's meson.build requests gobject-2.0/gio-2.0
        # as separate modules. Same approach as gssdp 1.6.6.
        extra_pc = []
        glib2 = self.dependencies.get("glib2")
        if glib2 and glib2.package_folder:
            glib_pkg = glib2.package_folder
            extra_pc.append(os.path.join(glib_pkg, "lib", "pkgconfig"))
            # The glib2 package .pc files were installed with --prefix=/ so their
            # Cflags/Libs resolve to /include, /lib (broken). Copy them and fix
            # prefix to the real package folder; prepend so meson prefers these.
            pc_fix_dir = os.path.join(self.build_folder, "glib2-pc-fix")
            os.makedirs(pc_fix_dir, exist_ok=True)
            for pc in os.listdir(os.path.join(glib_pkg, "lib", "pkgconfig")):
                if not pc.endswith(".pc"):
                    continue
                src = os.path.join(glib_pkg, "lib", "pkgconfig", pc)
                dst = os.path.join(pc_fix_dir, pc)
                with open(src, "r", encoding="utf-8") as fh:
                    text = fh.read()
                text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", text,
                              count=1, flags=re.M)
                # NOTE: gsound does NOT link libsoup3 (unlike gssdp/gupnp), so we
                # cannot rely on libsoup-3.0.so's GObject export table. Keep the
                # static glib2 link list in Libs so libgsound.so links glib
                # directly. The single-copy doctrine is maintained by ensuring
                # no other shared library in the consumer process brings a
                # separate GObject copy.
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(text)
            extra_pc.insert(0, pc_fix_dir)
            # glib2 package bin holds the meson gnome module tools
            # (glib-mkenums — gsound's gsound/meson.build uses gnome.mkenums()).
            # Pin them in the meson native file [binaries] section.
            glib_bin = os.path.join(glib_pkg, "bin")
            if os.path.isdir(glib_bin):
                self.buildenv_info.prepend_path("PATH", glib_bin)
                for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                             "glib-compile-resources", "glib-compile-schemas"):
                    tool_path = os.path.join(glib_bin, tool)
                    if os.path.isfile(tool_path):
                        tc.binaries[tool] = tool_path
        libcanberra_dep = self.dependencies.get("libcanberra")
        if libcanberra_dep and libcanberra_dep.package_folder:
            libcanberra_pc = os.path.join(libcanberra_dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(libcanberra_pc):
                extra_pc.append(libcanberra_pc)
        tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path] + extra_pc)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries are not "
                "runnable on the build host)")
        else:
            if hasattr(os, "uname") and os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    # gsound has no upstream tests; the consumer test_package
                    # is the real validation. Skip meson.test() here.
                    self.output.info("gsound has no upstream test suite")

                meson.test = _ohos_meson_test
            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        # meson installs headers flat to include/ (gsound.h, gsound-attr.h,
        # gsound-context.h) but consumers use #include <gsound/gsound.h>.
        # Move them to include/gsound/ to match the expected layout.
        inc_dir = os.path.join(self.package_folder, "include")
        inc_gsound = os.path.join(inc_dir, "gsound")
        os.makedirs(inc_gsound, exist_ok=True)
        for hdr in ("gsound.h", "gsound-attr.h", "gsound-context.h"):
            src = os.path.join(inc_dir, hdr)
            if os.path.exists(src):
                dst = os.path.join(inc_gsound, hdr)
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(src, dst)
        # ⚠️ meson install cleans DT_RUNPATH: overwrites bytes inside .dynstr
        # and drops the entry, invalidating the embedded .codesign hash →
        # dlopen Permission denied (libsoup3 evidence). Overwrite the installed
        # .so with the untouched build-tree artifact.
        if self.options.shared:
            _lib = "libgsound.so.0.0.2"
            _src = os.path.join(self.build_folder, "gsound", _lib)
            _dst = os.path.join(self.package_folder, "lib", _lib)
            if os.path.exists(_src):
                shutil.copy2(_src, _dst)
            # OHOS musl loader does not follow symlinks for DT_NEEDED.
            # libgsound.so.0.0.2 has SONAME libgsound.so.0, so the dynamic
            # linker looks for a file named exactly "libgsound.so.0".
            # Create hard copies for all three names.
            for _name in ("libgsound.so.0", "libgsound.so"):
                _link = os.path.join(self.package_folder, "lib", _name)
                if not os.path.exists(_link):
                    shutil.copy2(_dst, _link)

    def package_info(self):
        self.cpp_info.libs = ["gsound"]
        # gsound headers install to include/gsound/ (consumers use
        # #include <gsound/gsound.h>).
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # gsound public headers include glib/gio/gobject and libcanberra
        # headers; CMakeDeps generates empty data for TRANSITIVE deps
        # (conan 2.29), so expose their include dirs + libs here to let
        # consumers compile/link (same approach as gssdp 1.6.6).
        for depname in ("glib2", "libcanberra"):
            dep = self.dependencies.get(depname)
            if dep and dep.package_folder:
                self.cpp_info.includedirs.append(
                    os.path.join(dep.package_folder, "include"))
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                if depname == "glib2":
                    self.cpp_info.includedirs.append(
                        os.path.join(dep.package_folder, "include", "glib-2.0"))
                    self.cpp_info.includedirs.append(
                        os.path.join(dep.package_folder, "lib", "glib-2.0",
                                     "include"))
                self.cpp_info.libdirs.append(
                    os.path.join(dep.package_folder, "lib"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # PkgConfigDeps picks up pkg_config_name; CMakeDeps needs the cmake
        # names explicitly.
        self.cpp_info.set_property("pkg_config_name", "gsound")
        self.cpp_info.set_property("cmake_file_name", "gsound")
        self.cpp_info.set_property("cmake_target_name", "gsound::gsound")
