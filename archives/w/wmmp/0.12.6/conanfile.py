#!/usr/bin/env python3
"""Conan recipe for WMmp 0.12.6.

WMmp is a Window Maker dockapp client for mpd (Music Player Daemon).
Upstream builds a single executable with CMake and links the X11 stack:

    find_package(X11 REQUIRED)
    target_link_libraries(WMmp ${X11_LIBRARIES} ${X11_Xpm_LIB})

Upstream ships no FindX11.cmake and relies on CMake's builtin module, which
probes host X11 installs -- useless under Conan cross compilation.  This
recipe generates a thin ``FindX11.cmake`` module that maps CMake's X11
variables onto the Conan-provided libx11/libxext/libxpm packages (full .so
paths, so no libdir plumbing is needed):

    X11_INCLUDE_DIR -> aggregated include dirs of the three deps
    X11_LIBRARIES   -> libX11.so + libXext.so (wmmp uses XShape from Xext)
    X11_Xpm_LIB     -> libXpm.so

wmmp embeds its own (old) copy of libmpdclient in src/libmpdclient.c and
compiles it as part of the executable, so no external libmpdclient is
required.  ``config.h`` is guarded by ``#ifdef HAVE_CONFIG_H`` and upstream's
CMake build never defines it, so no configure-time header generation is
needed.

CMake compatibility: upstream declares ``cmake_minimum_required(VERSION 2.8)``
which CMake >= 4 rejects.  We do not patch the source; the toolchain sets
``CMAKE_POLICY_VERSION_MINIMUM=3.5`` so CMake 4.x accepts the old declaration.
No platform macros are involved (R8/PF5).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

FIND_X11_TEMPLATE = """\
# Conan-injected FindX11 module for WMmp ({version}).
# Maps upstream find_package(X11) onto the Conan X11 stack
# (libx11 + libxext for XShape, libxpm for X11/xpm.h).
# Linking uses -L/-l instead of absolute .so paths: make stats absolute
# prerequisites and the HMDFS conan cache denies stat on lib files
# (see R49/E524), while the linker resolves -l flags through -L dirs fine.
set(X11_FOUND TRUE)
set(X11_INCLUDE_DIR "{include_dirs}")
set(X11_LIBRARIES "{x11_linkdir};{xext_linkdir};-lX11;-lXext")
set(X11_X11_FOUND TRUE)
set(X11_Xext_LIB "{xext_linkdir};-lXext")
set(X11_Xext_FOUND TRUE)
set(X11_Xpm_LIB "{xpm_linkdir};-lXpm")
set(X11_Xpm_FOUND TRUE)
mark_as_advanced(X11_INCLUDE_DIR X11_LIBRARIES X11_Xpm_LIB X11_Xext_LIB)
"""


class WmmpConan(ConanFile):
    name = "wmmp"
    version = "0.12.6"
    description = "Window Maker dockapp client for the Music Player Daemon (mpd)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/yogsothoth/wmmp"
    url = "https://github.com/yogsothoth/wmmp"
    topics = ("dockapp", "window-maker", "mpd", "music", "x11")
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS 与 Linux 同族，禁止单独 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmmp supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # XShape (X11/extensions/shape.h) comes from libxext;
        # X11/xpm.h and -lXpm come from libxpm; Xlib from libx11.
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        module_dir = os.path.join(self.build_folder, "conan_cmake_modules")
        os.makedirs(module_dir, exist_ok=True)

        # Aggregate include dirs from the FULL host graph: Xlib.h pulls in
        # X11/X.h, Xmd.h etc. which live in xorgproto (xproto), not libx11.
        include_dirs = []
        for dep in self.dependencies.values():
            cpp = dep.cpp_info.aggregated_components()
            include_dirs.extend(d for d in cpp.includedirs if d)

        # HMDFS/E524 quirk: the dep package files in the conan cache are owned
        # by a different uid and link-time access (make stat / lld open) is
        # unreliable on HarmonyOS mounts, even though header reads compile
        # fine.  The build folder is created by the current process and is the
        # sanctioned reliable location (R49), so materialise the shared
        # libraries there and link against the copies.  Runtime loading still
        # resolves the SONAMEs (libX11.so.6, ...) via the conanrun env.
        needed_libs = {"X11": "libx11", "Xext": "libxext", "Xpm": "libxpm"}
        link_libs_dir = os.path.join(self.build_folder, "conan_link_libs")
        os.makedirs(link_libs_dir, exist_ok=True)
        for lib, dep_name in needed_libs.items():
            cpp = self.dependencies[dep_name].cpp_info.aggregated_components()
            src = os.path.join(cpp.libdirs[0], f"lib{lib}.so")
            dst = os.path.join(link_libs_dir, f"lib{lib}.so")
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o644)

        find_x11 = FIND_X11_TEMPLATE.format(
            version=self.version,
            include_dirs=";".join(dict.fromkeys(include_dirs)),
            x11_linkdir=f"-L{link_libs_dir}",
            xext_linkdir=f"-L{link_libs_dir}",
            xpm_linkdir=f"-L{link_libs_dir}",
        )
        with open(os.path.join(module_dir, "FindX11.cmake"), "w") as f:
            f.write(find_x11)

        tc = CMakeToolchain(self)
        # CMake >= 4 rejects upstream's cmake_minimum_required(VERSION 2.8);
        # policy floor without touching upstream sources.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_MODULE_PATH"] = module_dir
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        # The policy floor must be a *command line* -D: the toolchain file is
        # only included at project(), i.e. after upstream's
        # cmake_minimum_required(VERSION 2.8) at CMakeLists.txt line 1.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "wmmp")
