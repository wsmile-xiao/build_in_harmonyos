#!/usr/bin/env python3
"""Conan recipe — libdrawtext 0.6 (custom sh configure + Makefile.in)

Upstream build: `./configure` (plain shell) prepends a small header (PREFIX,
opt/dbg, name, ft2_cflags/ft2_libs) to ``Makefile.in`` producing ``Makefile``,
then plain ``make``. OHOS adaptation:

* One minimal bugfix patch (0001-glyphmap-image-export.patch): drawtext.h
  declares dtx_get_glyphmap_image but the implementation only ever existed
  as dtx_get_glyphmap_pixels — the patch adds a forwarding alias (identical
  signature/ownership/semantics) and declares dtx_get_glyphmap_pixels in
  the public header too, so the header↔library symbol contract holds.
* All remaining OHOS adaptation is make-variable overrides:

* OHOS has no desktop libGL/libGLU, and upstream ships an official
  ``#ifndef NO_OPENGL`` stub path in src/drawgl.c (dtx_target_opengl() becomes
  a warning no-op), so ``-DNO_OPENGL`` compiles the GL backend out. The full
  public API in drawtext.h is preserved; the software rasterizer backend
  (src/drawrast.c, dtx_target_raster) and the FreeType font machinery
  (src/font.c) remain fully functional.
* The generated Makefile resolves freetype2 via ``pkg-config`` at build time;
  we override CFLAGS/LDFLAGS wholesale (the freetype paths come from the Conan
  dependency), which makes the pkg-config backquotes irrelevant.

Links: freetype/2.14.3 (transitive headers, E348), -lpthread (USE_THREADS).
"""
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibdrawtextConan(ConanFile):
    name = "libdrawtext"
    version = "0.6"
    description = (
        "Simple library for anti-aliased text rendering in OpenGL, with a "
        "software rasterizer backend and FreeType font loading"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/jtsiomb/libdrawtext"
    url = "https://github.com/jtsiomb/libdrawtext"
    topics = ("text", "rendering", "opengl", "freetype", "fonts")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libdrawtext is only adapted for Linux/OHOS in this repo"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # drawtext.h itself is self-contained, but the built library links
        # libfreetype — declare it transitive so consumers resolve it.
        self.requires("freetype/2.14.3", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #

    def _tool(self, conf_key, env_keys, fallback):
        """Resolve a build tool: prefer the profile-advertised executable when
        it is a real file (the OHOS profile may point at a path that does not
        exist on this host), then the environment, then a bare name that PATH
        resolves."""
        candidate = None
        try:
            ce = self.conf.get("tools.build:compiler_executables", default=None)
            if ce:
                d = json.loads(ce) if isinstance(ce, str) else ce
                candidate = d.get(conf_key)
        except Exception:
            candidate = None
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        for k in env_keys:
            v = os.environ.get(k)
            if v and os.path.isfile(v) and os.access(v, os.X_OK):
                return v
            if v:
                return v
        return fallback

    def _freetype_dirs(self):
        dep = self.dependencies["freetype"]
        pf = getattr(dep, "package_folder", None) or ""
        inc = lib = None
        dirs = getattr(dep.cpp_info, "includedirs", None) or []
        if dirs:
            d = dirs[0]
            inc = d if (os.path.isabs(d) or not pf) else os.path.join(pf, d)
        elif pf and os.path.isdir(os.path.join(pf, "include")):
            inc = os.path.join(pf, "include")
        dirs = getattr(dep.cpp_info, "libdirs", None) or []
        if dirs:
            d = dirs[0]
            lib = d if (os.path.isabs(d) or not pf) else os.path.join(pf, d)
        elif pf and os.path.isdir(os.path.join(pf, "lib")):
            lib = os.path.join(pf, "lib")
        return inc, lib

    # ------------------------------------------------------------------ #

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        cc = self._tool("c", ("CC",), "clang")
        ar = self._tool(None, ("AR",), "llvm-ar")

        ft_inc, ft_lib = self._freetype_dirs()

        # Upstream CFLAGS end with: -I$(PREFIX)/include $(ft2_cflags)
        # -DUSE_THREADS, and LDFLAGS with: -L$(PREFIX)/lib $(ft2_libs)
        # $(libgl) -lpthread, where libgl = -lGL -lGLU (absent on OHOS).
        # We override both variables wholesale:
        #   * freetype include path points at the Conan package (its headers
        #     live in include/freetype2, not include/);
        #   * -DNO_OPENGL selects the upstream no-GL stub branch;
        #   * -lfreetype is linked explicitly from the Conan package.
        # The OHOS clang wrapper injects linker flags into compile steps, so
        # -Wno-unused-command-line-argument keeps -Wall from breaking.
        cflags = (
            "-O2 -g -fPIC -fcommon -Wall -Wno-unused-command-line-argument "
            "-DUSE_THREADS -DNO_OPENGL "
            "-I" + shlex.quote(os.path.join(src, "src"))
        )
        if ft_inc:
            cflags += " -I" + shlex.quote(ft_inc)
        ldflags = "-lpthread"
        if ft_lib:
            ldflags = "-L" + shlex.quote(ft_lib) + " -lfreetype " + ldflags

        # configure only bakes PREFIX and the freetype on/off choice into the
        # generated Makefile; CC/AR/CFLAGS/LDFLAGS are overridden on the make
        # command line below, so the script runs as-is with a private prefix.
        stage_prefix = os.path.join(self.build_folder, "stage")
        self.run(
            "cd {src} && ./configure --prefix={prefix} --enable-freetype".format(
                src=shlex.quote(src), prefix=shlex.quote(stage_prefix))
        )

        make_vars = [
            "CC=" + shlex.quote(cc),
            "AR=" + shlex.quote(ar),
            "CFLAGS=" + shlex.quote(cflags),
            "LDFLAGS=" + shlex.quote(ldflags),
        ]
        # E525: keep the build serial; the implicit .d includes are not
        # parallel-safe.
        self.run(
            "make -C {src} -j1 clean all ".format(src=shlex.quote(src))
            + " ".join(make_vars)
        )

    def package(self):
        # `make install` stages into DESTDIR+PREFIX with the soname chain
        # (libdrawtext.so -> .so.0 -> .so.0.5) created via `ln -s` inside the
        # staged lib dir.
        src = self.source_folder
        stage_prefix = os.path.join(self.build_folder, "stage")
        destdir = os.path.join(self.build_folder, "dest")
        self.run(
            "make -C {src} -j1 install ".format(src=shlex.quote(src))
            + " ".join([
                "DESTDIR=" + shlex.quote(destdir),
                "PREFIX=" + shlex.quote(stage_prefix),
            ])
        )
        stage = os.path.join(destdir, stage_prefix.lstrip(os.sep))
        copy(self, "drawtext.h",
             src=os.path.join(stage, "include"),
             dst=os.path.join(self.package_folder, "include"))
        patterns = ("*.so*", "*.a") if not self.options.shared else ("*.so*",)
        for pattern in patterns:
            copy(self, pattern,
                 src=os.path.join(stage, "lib"),
                 dst=os.path.join(self.package_folder, "lib"))
        # E492: materialize the SONAME chain libdrawtext.so / libdrawtext.so.0
        # as real copies of libdrawtext.so.0.5, so consumers do not depend on
        # dangling symlinks across package relocation.
        self._materialize_aliases(os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def _materialize_aliases(self, libdir):
        real = None
        for cand in sorted(os.listdir(libdir)):
            # libdrawtext.so.0.5 — two dots after the .so part
            if cand.startswith("libdrawtext.so.") and cand.count(".") == 3:
                real = cand
                break
        if not real:
            return
        real_path = os.path.join(libdir, real)
        for alias in ("libdrawtext.so.0", "libdrawtext.so"):
            dst = os.path.join(libdir, alias)
            if os.path.islink(dst) or os.path.lexists(dst):
                os.remove(dst)
            shutil.copyfile(real_path, dst)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["drawtext"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "libdrawtext")
        self.cpp_info.set_property("cmake_target_name", "libdrawtext::libdrawtext")
        self.cpp_info.set_property("pkg_config_name", "libdrawtext")
