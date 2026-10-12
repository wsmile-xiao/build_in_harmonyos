#!/usr/bin/env python3
"""Conan recipe — osm-gps 1.2.0

HarmonyOS PC (aarch64 / OHOS) adaptation of osm-gps-map 1.2.0
(https://github.com/nzjrs/osm-gps-map): a GTK3 / GObject "moving map"
widget for OpenStreetMap tiles.

Upstream ships an Autotools + libtool build that produces the shared
library libosmgpsmap-1.0.so, the pkg-config file osmgpsmap-1.0.pc and the
public headers under include/osmgpsmap-1.0/ (osm-gps-map.h, ...). It also
ships GObject-Introspection (--enable-introspection) and gtk-doc
(--enable-gtk-doc) machinery that is NOT portable to a headless OHOS build
and is disabled here.

Build approach (proven for Autotools on this platform — see abiword-plugin-*
and libgal adaptations):
  * PkgConfigDeps generates the dependency .pc files (glib-2.0, gtk+-3.0,
    cairo, libsoup-2.4, gthread-2.0, plus their transitive closures) into
    the generators folder; PKG_CONFIG_PATH is injected so configure's
    PKG_CHECK_MODULES finds them.
  * AutotoolsToolchain provides the OHOS clang toolchain + flags.
  * HMDFS TMPDIR hardening (E114): configure's config.status writes temp
    subdirs into the build dir which the OHOS security framework blocks;
    a fixed writable TMPDIR is provided and the ac_tmp template is patched.
  * Only `make -C src` is run (the library); packaging globs the produced
    .so + generated .pc + public headers instead of `make install` (which
    would also try to install examples/docs and fight DESTDIR on a
    non-root worker).
"""

import os
import re
import glob
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class OsmGpsConan(ConanFile):
    name = "osm-gps"
    version = "1.2.0"
    description = (
        "osm-gps-map: a Gtk+ widget for displaying raster map data "
        "(OpenStreetMap tiles) with pan/zoom/track/OSD support"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/nzjrs/osm-gps-map"
    url = "https://github.com/nzjrs/osm-gps-map"
    topics = ("map", "gtk", "openstreetmap", "widget", "gobject")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        # Pure C/GObject library: keep the C++ toolchain options out of the
        # package_id and avoid building a static archive by default.
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
        if self.options.shared:
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported by osm-gps"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Direct dependencies declared by configure.ac PKG_CHECK_MODULES:
        #   glib-2.0 >= 2.16, gtk+-3.0 >= 3.0, cairo >= 1.8, libsoup-2.4,
        #   gthread-2.0 (gthread is part of glib).
        # glib is NOT pinned here: gtk/3.24.43 constrains glib to a specific
        # version (2.84.x), and cairo/libsoup must agree — letting the graph
        # resolve glib transitively avoids version conflicts. PkgConfigDeps
        # still emits glib-2.0.pc (and gdk-pixbuf-2.0 / pango etc. via gtk).
        self.requires("gtk/3.24.43")
        self.requires("cairo/1.18.4")
        self.requires("libsoup/2.74.3")
        # OHOS zlib version clash (glib2/2.88.0 wants zlib/1.3.1 while the
        # rest of the GTK3 stack ships binaries built against zlib/1.3.1.1).
        # Unify on 1.3.1.1 so the published binaries are reused instead of
        # forcing a from-source rebuild (same fix as abiword-plugin-*).
        self.requires("zlib/1.3.1.1", override=True)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # PkgConfigDeps: emit dependency .pc files so configure's
        # PKG_CHECK_MODULES(glib/gtk/cairo/soup/gthread) resolves.
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                # Headless OHOS build: skip introspection + documentation.
                "--disable-introspection",
                "--disable-gtk-doc",
                # Library flavour.
                "--enable-shared",
                "--disable-static",
                # config.guess cannot classify the OHOS uname; pin the
                # triplet explicitly (aarch64-linux is known to config.sub).
                "--build=aarch64-linux",
                "--host=aarch64-linux",
            ]
        )
        # Inject PKG_CONFIG_PATH so the generated .pc files are found.
        # `VAR=VALUE` passed to ./configure is exported into its test
        # environment (same trick as the abiword-plugin-* adaptations).
        tc.configure_args.append(
            "PKG_CONFIG_PATH={}".format(self.generators_folder)
        )
        # OHOS aarch64 links with lld (no GNU ld shipped).
        tc.ldflags.append("-fuse-ld=lld")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os == "OHOS":
            self._patch_hmdfs_tmp(self.source_folder)

        autotools = Autotools(self)
        # Build only the library (src/); examples/docs need extra tooling
        # and are irrelevant for packaging the widget library.
        autotools.configure()
        autotools.make(target="-C src")

    # ------------------------------------------------------------------
    # HMDFS TMPDIR hardening (E114)
    # ------------------------------------------------------------------
    @staticmethod
    def _patch_hmdfs_tmp(source_folder):
        """Provide a fixed writable TMPDIR and patch configure's ac_tmp.

        The OHOS security framework blocks configure's config.status from
        creating temp subdirs inside the build tree, which makes the C
        compiler conftests fail ("C compiler cannot create executables").
        We (a) point TMPDIR at a writable volume and (b) rewrite the
        `ac_tmp=$tmp` template to that directory, removing the cleanup trap
        that would delete it between runs.
        """
        import tempfile

        fixed_tmp = os.path.join(
            tempfile.gettempdir(), "osm-gps-ac-tmp"
        )
        os.makedirs(fixed_tmp, exist_ok=True)
        os.environ["TMPDIR"] = fixed_tmp

        cfg = os.path.join(source_folder, "configure")
        if not os.path.exists(cfg):
            return
        with open(cfg, "r", encoding="utf-8") as _f:
            text = _f.read()

        if "ac_tmp=$tmp" in text:
            text = text.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
            old_trap = (
                '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } '
                "&& exit $exit_status"
            )
            if old_trap in text:
                text = text.replace(old_trap, "exit $exit_status")
            with open(cfg, "w", encoding="utf-8") as _f:
                _f.write(text)
            os.chmod(cfg, 0o755)

    # ------------------------------------------------------------------
    # Packaging (glob + copy, no `make install`)
    # ------------------------------------------------------------------
    def package(self):
        self._package_lib()
        self._package_pc()
        self._package_headers()

    def _package_lib(self):
        src_libs = glob.glob(
            os.path.join(self.build_folder, "src", ".libs", "libosmgpsmap-1.0.so*")
        )
        if not src_libs:
            raise ConanException(
                "libosmgpsmap-1.0.so not found in build_folder/src/.libs; "
                "build may have failed or used a different output layout"
            )
        dst = os.path.join(self.package_folder, "lib")
        os.makedirs(dst, exist_ok=True)
        # Find the real shared object (the one with an ELF SONAME).
        real = None
        for path in src_libs:
            if os.path.islink(path):
                continue
            # Prefer the fully-versioned file (libosmgpsmap-1.0.so.0.0.0).
            if re.search(r"\.so\.\d+\.\d+\.\d+$", path):
                real = path
                break
        if real is None:
            # Fall back to any non-link file.
            for path in src_libs:
                if not os.path.islink(path):
                    real = path
                    break
        if real is None:
            raise ConanException("could not locate real libosmgpsmap-1.0.so")

        base = "libosmgpsmap-1.0.so"
        real_name = os.path.basename(real)
        copy(self, real_name, os.path.dirname(real), dst)

        # Establish the SONAME link (what the runtime loader NEEDEDs, e.g.
        # libosmgpsmap-1.0.so.1) derived from the real ELF's SONAME header.
        # The linker name (.so) then points at the SONAME link, exactly as
        # libtool would lay it out. Without the SONAME link a consumer built
        # with -losmgpsmap-1.0 fails at runtime with
        # "Error loading shared library libosmgpsmap-1.0.so.1".
        soname = self._read_soname(os.path.join(dst, real_name))
        if soname:
            self._install_link(dst, real_name, soname)
            self._install_link(dst, soname, base)
        else:
            # Fallback if no SONAME was readable: major-version + linker name.
            self._install_link(dst, real_name, base + ".1")
            self._install_link(dst, real_name, base)
        self.output.info(
            "PACKAGE_LAYOUT_LIB={} soname={}".format(real_name, soname or "(n/a)")
        )

    def _read_soname(self, path):
        """Best-effort extraction of the ELF SONAME via readelf/llvm-readelf.

        Returns the soname string (e.g. "libosmgpsmap-1.0.so.1") or None.
        The toolchain readelf lives in the OHOS bin dirs which may not be on
        PATH for the packaging step, so a few well-known locations are tried.
        """
        import subprocess

        candidates = ["llvm-readelf", "readelf"]
        extra_dirs = ["/data/service/hnp/bin", "/system/bin"]
        for tool in candidates:
            exe = shutil.which(tool)
            if exe is None:
                for d in extra_dirs:
                    cand = os.path.join(d, tool)
                    if os.path.exists(cand):
                        exe = cand
                        break
            if exe is None:
                continue
            try:
                out = subprocess.check_output(
                    [exe, "-d", path], text=True, stderr=subprocess.DEVNULL
                )
            except (OSError, subprocess.SubprocessError):
                continue
            m = re.search(r"Library soname:\s*\[([^\]]+)\]", out)
            if m:
                return m.group(1)
        return None

    def _install_link(self, dst_dir, real_name, link_name):
        """Create link_name -> real_name, falling back link->hardlink->copy.

        HMDFS rejects symlink creation, so we try symlink first, then
        hardlink, then a plain copy (the SONAME lives inside the ELF, so a
        copy remains a valid shared library).
        """
        target = os.path.join(dst_dir, link_name)
        if os.path.lexists(target):
            os.unlink(target)
        try:
            os.symlink(real_name, target)
        except OSError:
            try:
                os.link(os.path.join(dst_dir, real_name), target)
            except OSError:
                shutil.copy(os.path.join(dst_dir, real_name), target)

    def _package_pc(self):
        pc_src = os.path.join(self.build_folder, "osmgpsmap-1.0.pc")
        dst_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, "osmgpsmap-1.0.pc")
        if not os.path.exists(pc_src):
            # Fallback: regenerate from the .pc.in template.
            self._generate_pc_from_template(dst)
            return
        with open(pc_src, "r", encoding="utf-8") as _f:
            text = _f.read()
        # Make prefix relocatable so the package works wherever it lands.
        text = re.sub(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            text,
            flags=re.M,
        )
        with open(dst, "w", encoding="utf-8") as _f:
            _f.write(text)
        self.output.info("PACKAGE_LAYOUT_PC=lib/pkgconfig/osmgpsmap-1.0.pc")

    def _generate_pc_from_template(self, dst):
        pc_in = os.path.join(self.source_folder, "osmgpsmap-1.0.pc.in")
        if not os.path.exists(pc_in):
            raise ConanException("osmgpsmap-1.0.pc.in not found for fallback")
        with open(pc_in, "r", encoding="utf-8") as _f:
            text = _f.read()
        subs = {
            "@prefix@": "${pcfiledir}/../..",
            "@exec_prefix@": "${prefix}",
            "@libdir@": "${prefix}/lib",
            "@includedir@": "${prefix}/include",
            "@PACKAGE_NAME@": "osm-gps-map",
            "@PACKAGE_VERSION@": self.version,
        }
        for k, v in subs.items():
            text = text.replace(k, v)
        with open(dst, "w", encoding="utf-8") as _f:
            _f.write(text)
        self.output.info("PACKAGE_LAYOUT_PC=lib/pkgconfig/osmgpsmap-1.0.pc (from .in)")

    def _package_headers(self):
        src_inc = os.path.join(self.source_folder, "src")
        dst = os.path.join(self.package_folder, "include", "osmgpsmap-1.0")
        os.makedirs(dst, exist_ok=True)
        count = 0
        for header in glob.glob(os.path.join(src_inc, "osm-gps-map*.h")):
            copy(self, os.path.basename(header), src_inc, dst)
            count += 1
        if count == 0:
            raise ConanException("no osm-gps-map*.h public headers found")
        self.output.info("PACKAGE_LAYOUT_HEADERS={} headers".format(count))

    def package_info(self):
        self.cpp_info.libs = ["osmgpsmap-1.0"]
        self.cpp_info.includedirs = ["include/osmgpsmap-1.0"]
        self.cpp_info.set_property("pkg_config_name", "osmgpsmap-1.0")
        self.cpp_info.set_property("cmake_file_name", "osmgpsmap")
        self.cpp_info.set_property("cmake_target_name", "osmgpsmap::osmgpsmap")
