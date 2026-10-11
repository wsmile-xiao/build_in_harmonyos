#!/usr/bin/env python3
"""Conan recipe for smpeg 0.4.5-cvs20030824 (MPEG-1 audio/video decoder).

smpeg is the LGPL MPEG-1 decoder library (`libsmpeg`) that SDL_mixer and
several SDL based players link against.  The 2003 code base is built with
autotools; the release tarball ships a generated `configure`, so no
autoreconf is involved.

Two portability issues have to be fixed for the OHOS toolchain (see
`patches/`):

* the decoder sources use the `register` storage class, which was removed in
  C++17 - the OHOS profile builds C++ with `-std=c++17`, where any remaining
  `register` is a hard error;
* upstream forces the libtool C++ link driver to `cc` and appends a hardcoded
  `-lstdc++` to `libsmpeg_la_LDFLAGS`; the OHOS toolchain ships libc++
  (`libc++_shared.so`) and no `libstdc++`.

`AM_PATH_SDL` (bundled in `acinclude.m4`) requires a `sdl-config` script,
while the published `sdl/1.2.15` Conan package only ships the headers and
`libSDL.a`: the recipe therefore generates an equivalent `sdl-config` shim
for the configure step.
"""
import os
import stat
import textwrap

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, chmod, copy, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SmpegConan(ConanFile):
    name = "smpeg"
    version = "0.4.5-cvs20030824"
    package_type = "library"
    description = "MPEG-1 audio/video decoder library (libsmpeg) with a demo SDL player"
    license = "LGPL-2.0-or-later"
    homepage = "https://www.libsdl.org/projects/smpeg/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_demo_player": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_demo_player": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libsmpeg itself is SDL independent, but the top level autotools check
        # (AM_PATH_SDL) and the bundled plaympeg demo player need SDL 1.2.
        self.requires("sdl/1.2.15")

    def layout(self):
        basic_layout(self)
        # This 2003 autotools tree only supports in-source builds.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _sdl_config_shim(self):
        """Create the sdl-config script AM_PATH_SDL looks for."""
        sdl = self.dependencies["sdl"]
        include_dir = sdl.cpp_info.includedirs[0]
        lib_dir = sdl.cpp_info.libdirs[0]
        path = os.path.join(self.build_folder, "sdl-config")
        save(self, path, textwrap.dedent("""\
            #!/bin/sh
            # Minimal sdl-config replacement: the published sdl/1.2.15 package
            # ships SDL.h and libSDL.a but not the upstream sdl-config script.
            for arg in "$@"; do
              case "$arg" in
                --version) echo "1.2.15" ;;
                --cflags) echo "-I{include_dir}" ;;
                --libs) echo "-L{lib_dir} -lSDL" ;;
              esac
            done
            """).format(include_dir=include_dir, lib_dir=lib_dir))
        # Follow the sdl-image/sdl_mixer/lbreakout2 recipes: set the executable
        # bits explicitly (the HMDFS mode of a freshly written file is 0640).
        os.chmod(path, os.stat(path).st_mode
                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.output.info("sdl-config shim %s (mode %o)"
                         % (path, os.stat(path).st_mode & 0o777))
        return path

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # The GTK and OpenGL demo players need toolkits that are not part
            # of the OHOS profile; the decoder library and plaympeg do not.
            "--disable-gtk-player",
            "--disable-opengl-player",
            # MMX/ATI code paths are x86 assembly.
            "--disable-mmx",
            "--disable-ati",
            "--disable-debug",
        ])
        if self.settings.os == "OHOS":
            # AutotoolsToolchain does not inject OHOS triplets in this profile,
            # and the bundled config.guess (2001) cannot derive one either
            # (E007).  The triplet is therefore declared explicitly; config.sub
            # is patched (patches/0002) so that "aarch64-linux-ohos" is
            # canonicalised instead of rejected, exactly like aalib/1.4p5.
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        env = tc.environment()
        env.define("SDL_CONFIG", self._sdl_config_shim())
        # configure runs (and executes) probe programs that link SDL, and the
        # OHOS sdl/1.2.15 package pulls the shared alsa-lib libraries in
        # (libatopology.so/libasound.so); the loader needs their directories
        # while configure probes the compiler.
        lib_dirs = []
        for dep in self.dependencies.values():
            lib_dirs.extend(dep.cpp_info.libdirs)
        env.define("LD_LIBRARY_PATH", os.pathsep.join(lib_dirs))
        tc.generate(env)
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: the process working directory cannot always be resolved with
        # getcwd() (knowledge E114/E386), which makes libtool compute relative
        # convenience-archive paths from an empty directory. Presetting PWD
        # keeps the shell side of the build on the right path.
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        self._audit_upstream_tests()

    def _audit_upstream_tests(self):
        # The 2003 release ships no test suite at all: there is no tests/
        # directory, no check_PROGRAMS/TESTS registration and no check target.
        self.run("grep -nE 'check_PROGRAMS|^TESTS|check-local|^check:' "
                 "Makefile.in audio/Makefile.in video/Makefile.in || true")
        self.run("find . -maxdepth 2 -iname '*test*' | head || true")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["smpeg"]
        self.cpp_info.bindirs = ["bin"]
        # smpeg's public headers include SDL headers (MPEGaudio.h), so the SDL
        # include dirs and libraries have to be propagated to consumers.
        self.cpp_info.requires = ["sdl::sdl"]
        self.cpp_info.set_property("cmake_file_name", "smpeg")
        self.cpp_info.set_property("cmake_target_name", "smpeg::smpeg")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]
        if not self.options.shared:
            # libsmpeg is C++ inside a C API; static consumers need the C++ runtime.
            self.cpp_info.system_libs.append("c++")
