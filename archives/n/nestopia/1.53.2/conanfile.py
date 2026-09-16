#!/usr/bin/env python3
"""Conan recipe for Nestopia 1.53.2 (Autotools build system).

Nestopia is a portable, cycle-accurate NES/Famicom emulator.  The upstream
Unix build produces the `nestopia` FLTK GUI application from source/core/
(emulation core), source/nes_ntsc/ (header-only NTSC filter) and
source/fltkui/ (FLTK front-end; SDL2 is used for input only).

The HarmonyOS PC port keeps the upstream build/link contract intact:

* configure.ac accepts externally supplied ZLIB_* / LIBARCHIVE_* /
  SAMPLERATE_* / SDL2_* / LIBEPOXY_* / FLTK_* CFLAGS/LIBS so that Conan
  package paths are used verbatim and no host pkg-config/fltk-config can
  leak native flags into the OHOS build (patches/0001).
* OHOS exposes EGL/GLES2 but no GLX/desktop OpenGL, so the in-repo
  libfltk/1.3.11 package ships no libfltk_gl.  fltkui/fltk_gl_ohos.cpp
  (patches/0003) provides the Fl_Gl_Window symbol set with an honest
  can_do()==0 capability probe; the front-end then degrades to the base
  FLTK window.  The GUI display path cannot run headless on OHOS.
* The emulation core is additionally archived into libnestopia_core.a so
  that a headless consumer test can drive the core APIs (no FLTK/SDL/GL).
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NestopiaConan(ConanFile):
    name = "nestopia"
    version = "1.53.2"
    description = "Nestopia — portable, cycle-accurate NES/Famicom emulator"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/0ldsk00l/nestopia"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf-archive/2024.10.16")

    def requirements(self):
        # zlib/1.3.1.1 is the OHOS -fPIC rebuild (see archives/z/zlib/1.3.1.1).
        self.requires("zlib/1.3.1.1")
        self.requires("libarchive/3.8.7")
        self.requires("libsamplerate/0.2.2")
        self.requires("sdl2/2.32.10")
        self.requires("libepoxy/1.5.10")
        # libfltk pulls in libx11/1.8.13 (shared) plus xorgproto.
        self.requires("libfltk/1.3.11")
        # xorgproto provides the X11/X.h protocol headers required by
        # Xlib.h; declare it directly so its package folder is available
        # when assembling FLTK_CFLAGS in generate().
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The OHOS config.guess cannot identify the platform; pin the
        # triplets so AC_CANONICAL_HOST selects the Unix code paths and
        # config.sub does not need an OHOS entry.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

        flags = self._dependency_flags()
        env = Environment()
        for var, value in flags.items():
            env.define(var, value)
        env.vars(self).save_script("nestopia_depflags")

    # ------------------------------------------------------------------
    # Dependency flag assembly (absolute Conan package paths only)
    # ------------------------------------------------------------------
    def _dep_items(self, dep_name):
        dep = self.dependencies[dep_name]
        cpp = dep.cpp_info
        try:
            components = cpp.get_sorted_components()
        except Exception:  # noqa: BLE001 - permissive fallback
            components = {}
        items = list(components.values()) if components else [cpp]
        return dep, items

    def _flags_for(self, dep_name):
        dep, items = self._dep_items(dep_name)
        prefix = dep.package_folder
        if not prefix:
            # Transitive/host deps (e.g. header-only xorgproto) may not be
            # indexed under dependencies[ref] with a package folder; fall
            # back to a name scan, then to the Conan cache layout.
            for candidate in self.dependencies.values():
                if getattr(candidate.ref, "name", None) == dep_name:
                    prefix = candidate.package_folder
                    break
        if not prefix:
            cache_root = os.environ.get("CONAN_HOME", os.path.expanduser("~/.conan2"))
            matches = sorted(
                glob.glob(os.path.join(cache_root, "p", "xorgp*", "p"))
            )
            if matches and os.path.isdir(os.path.join(matches[-1], "include")):
                prefix = matches[-1]
        if not prefix:
            return "", ""
        includes, libdirs, libs, syslibs = [], [], [], []
        for item in items:
            includes += [os.path.join(prefix, d) for d in item.includedirs]
            libdirs += [os.path.join(prefix, d) for d in item.libdirs]
            libs += list(item.libs)
            syslibs += list(item.system_libs)
        cflags = " ".join("-I%s" % d for d in dict.fromkeys(includes))
        ldflags = " ".join("-L%s" % d for d in dict.fromkeys(libdirs))
        ldflags += " " + " ".join("-l%s" % l for l in libs)
        if syslibs:
            ldflags += " " + " ".join(
                "-l%s" % s for s in dict.fromkeys(syslibs)
            )
        return cflags, ldflags

    def _dependency_flags(self):
        flags = {}
        for var, dep in (
            ("ZLIB", "zlib"),
            ("SAMPLERATE", "libsamplerate"),
            ("SDL2", "sdl2"),
            ("LIBEPOXY", "libepoxy"),
        ):
            cflags, ldflags = self._flags_for(dep)
            flags["%s_CFLAGS" % var] = cflags
            flags["%s_LIBS" % var] = ldflags

        # libarchive: the shared libarchive.so.13 keeps unresolved zlib
        # references (the OHOS host has no libz.so provider), so the
        # emulator links the static libarchive.a plus its static zlib/lzma
        # closure instead.  This keeps the produced `nestopia` binary free
        # of a runtime libarchive.so dependency.
        la_cflags, la_ldflags = self._flags_for("libarchive")
        xz_ldflags = self._flags_for("xz")[1]
        zl_ldflags = self._flags_for("zlib")[1]
        flags["LIBARCHIVE_CFLAGS"] = la_cflags
        flags["LIBARCHIVE_LIBS"] = "%s -Wl,-Bstatic -larchive -Wl,-Bdynamic %s %s" % (
            la_ldflags.replace("-larchive", "").strip(),
            xz_ldflags,
            zl_ldflags,
        )

        fltk_cflags, fltk_ldflags = self._flags_for("libfltk")
        # FLTK 1.3 ships its own image codecs (libfltk_jpeg/png/z); the
        # recipe's package_info only lists fltk_images+fltk, so the internal
        # codecs must be linked explicitly in dependency order.  The GL
        # front-end symbol set is supplied by fltkui/fltk_gl_ohos.cpp inside
        # the emulator itself, so no -lfltk_gl is needed.
        internal_codecs = "-lfltk_jpeg -lfltk_png -lfltk_z"
        flags["FLTK_CFLAGS"] = fltk_cflags
        flags["FLTK_LIBS"] = (
            fltk_ldflags.replace("-lfltk_images -lfltk", "-lfltk_images %s -lfltk" % internal_codecs)
        )
        # libfltk depends on libx11 (shared) plus xorgproto protocol
        # headers; FLTK's own headers include <X11/Xlib.h>, so the X11 and
        # xorgproto include dirs must be on the compile line too.
        x11_cflags, x11_ldflags = self._flags_for("libx11")
        xorg_cflags, _xorg_ldflags = self._flags_for("xorgproto")
        flags["FLTK_CFLAGS"] += " " + x11_cflags + " " + xorg_cflags
        # The X dependency chain is resolved through its DT_NEEDED entries
        # at runtime.
        flags["FLTK_LIBS"] += " " + x11_ldflags
        # fltk_samples uses libm/libdl/libpthread through the base kit.
        flags["FLTK_LIBS"] += " -lm -ldl -lpthread"
        return flags

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def build(self):
        # Optionally reuse the recipe-internal assembler/ranlib helpers on
        # OHOS (llvm-ar/llvm-ranlib ship with the SDK clang toolchain).
        env = Environment()
        ar = shutil.which("ar") or "/data/service/hnp/bin/ar"
        ranlib = shutil.which("ranlib") or "/data/service/hnp/bin/ranlib"
        env.define("AR", ar)
        env.define("RANLIB", ranlib)
        with env.vars(self).apply():
            self._run_autoreconf()
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
        self._archive_core_library()

    def _run_autoreconf(self):
        """Run autoreconf with the OHOS-safe perl toolchain.

        The Conan perl package cannot load its XS modules on HMDFS
        ("Permission denied" on Cwd.so), while the system perl works.  The
        autoconf/automake perl modules however live inside the Conan
        packages, so PERL5LIB must keep only the automake module directory
        (dropping the Conan perl core paths) and every autotools variable
        must point at the Conan package binaries.
        """
        automake_dir = self.dependencies.build["automake/1.18"].package_folder
        autoconf_dir = self.dependencies.build["autoconf/2.72"].package_folder
        archive_dir = self.dependencies.build["autoconf-archive/2024.10.16"].package_folder

        run_env = dict(os.environ)
        run_env["PATH"] = (
            "/data/service/hnp/bin:%s/bin:%s/bin:%s"
            % (autoconf_dir, automake_dir, run_env.get("PATH", ""))
        )
        run_env["PERL"] = "/data/service/hnp/bin/perl"
        run_env["PERL5LIB"] = os.path.join(automake_dir, "share", "automake-1.18")
        run_env["ACLOCAL_PATH"] = os.path.join(archive_dir, "share", "aclocal")
        run_env["AUTOMAKE"] = os.path.join(automake_dir, "bin", "automake")
        run_env["ACLOCAL"] = os.path.join(automake_dir, "bin", "aclocal")
        run_env["AUTOCONF"] = os.path.join(autoconf_dir, "bin", "autoconf")
        run_env["AUTORECONF"] = os.path.join(autoconf_dir, "bin", "autoreconf")
        run_env["AUTOM4TE"] = os.path.join(autoconf_dir, "bin", "autom4te")
        run_env["autom4te_perllibdir"] = os.path.join(
            autoconf_dir, "share", "autoconf"
        )
        subprocess.run(
            ["autoreconf", "-fi"], cwd=self.source_folder, env=run_env, check=True
        )

    def _archive_core_library(self):
        """Archive the emulation-core objects into libnestopia_core.a.

        The core (source/core + header-only source/nes_ntsc) has no
        display dependency, which lets a headless consumer exercise the
        Nes::Core::Api::* APIs without any FLTK/SDL/GL initialisation.
        """
        objects = sorted(
            glob.glob(
                os.path.join(self.build_folder, "source", "core", "**", "*.o"),
                recursive=True,
            )
        )
        expected = self._count_core_sources()
        if not objects:
            raise ConanInvalidConfiguration(
                "no core objects found for the static core archive"
            )
        if len(objects) != expected:
            # The 4 NST_NO_* filtered scaler filters (2xSaI/HqX/ScaleX/xBR)
            # are intentionally excluded from nestopia_SOURCES upstream, so a
            # shortfall is expected; report it for traceability only.
            self.output.info(
                "core object count %d vs %d source files "
                "(NST_NO_* filters are not compiled upstream)"
                % (len(objects), expected)
            )
        archive = os.path.join(self.build_folder, "libnestopia_core.a")
        # Use the SDK ar by absolute path: the Conan build env may export
        # AR=llvm-ar, which is not on PATH on the CI worker.
        ar = "/data/service/hnp/bin/ar"
        if not os.path.isfile(ar):
            ar = shutil.which("ar") or "ar"
        subprocess.run([ar, "rcs", archive] + objects, check=True)
        self.output.info(
            "archived %d core objects into libnestopia_core.a" % len(objects)
        )

    def _count_core_sources(self):
        root = os.path.join(self.source_folder, "source", "core")
        return sum(
            1
            for _, _, files in os.walk(root)
            for name in files
            if name.endswith(".cpp")
        )

    # ------------------------------------------------------------------
    # Package
    # ------------------------------------------------------------------
    def package(self):
        autotools = Autotools(self)
        autotools.install()

        core_archive = os.path.join(self.build_folder, "libnestopia_core.a")
        if os.path.isfile(core_archive):
            copy(
                self,
                "libnestopia_core.a",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "lib"),
            )
        else:
            raise ConanInvalidConfiguration(
                "libnestopia_core.a was not produced by the build"
            )

        include_dir = os.path.join(self.package_folder, "include")
        core_src = os.path.join(self.source_folder, "source", "core")
        for current, dirs, files in os.walk(core_src):
            relative = os.path.relpath(current, core_src)
            target = os.path.join(include_dir, "core", relative)
            os.makedirs(target, exist_ok=True)
            for name in files:
                if name.endswith((".hpp", ".h")):
                    shutil.copy2(
                        os.path.join(current, name), os.path.join(target, name)
                    )

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS":
            executable = os.path.join(self.package_folder, "bin", "nestopia")
            if os.path.isfile(executable):
                self._sign_ohos_elf(executable)

    def _sign_ohos_elf(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning(
                "HarmonyOS ELF signing tools unavailable; skipping sign of %s"
                % path
            )
            return
        clean_path = "%s.codesign-clean" % path
        signed_path = "%s.signed" % path
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path, clean_path],
                check=True,
            )
            subprocess.run(
                [signer, "sign", "-inFile", clean_path, "-outFile", signed_path,
                 "-selfSign", "1"],
                check=True,
            )
            os.replace(signed_path, path)
            os.chmod(path, 0o755)
        finally:
            for temporary in (clean_path, signed_path):
                if os.path.exists(temporary):
                    os.remove(temporary)

    # ------------------------------------------------------------------
    # package_info
    # ------------------------------------------------------------------
    def package_info(self):
        # core component: the headless emulation library (static archive +
        # headers).  Consumers that link nestopia::core only need zlib.
        core = self.cpp_info.components["core"]
        core.libs = ["nestopia_core"]
        core.includedirs = ["include"]
        core.set_property("cmake_target_name", "nestopia::core")
        core.requires = ["zlib::zlib"]

        # app component: declares the remaining direct dependencies that the
        # GUI binary links at build time.  It carries no library of its own,
        # so consumers of nestopia::core never link libarchive/sdl2/fltk...
        app = self.cpp_info.components["app"]
        app.set_property("cmake_target_name", "nestopia::app")
        app.requires = [
            "libarchive::libarchive",
            "libsamplerate::libsamplerate",
            "sdl2::sdl2",
            "libepoxy::libepoxy",
            "libfltk::libfltk",
            "xorgproto::xorgproto",
        ]