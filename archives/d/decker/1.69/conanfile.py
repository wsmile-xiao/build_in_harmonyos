#!/usr/bin/env python3
"""Conan recipe for Decker — a multimedia sketchpad (Makefile project).

Decker builds two targets:
  - lilt:  standalone Lil interpreter (no SDL dependency, always built)
  - decker: GUI app (requires SDL2 + SDL2_image, optional)

Build uses PkgConfigDeps to provide SDL2/SDL2_image flags via pkg-config
when SDL2 dependencies are available.
"""
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class DeckerConan(ConanFile):
    name = "decker"
    version = "1.69"
    description = "Decker is a multimedia platform for creating and sharing interactive documents, with sound, images, hypertext, and scripted behavior."
    license = "MIT"
    homepage = "https://github.com/JohnEarnest/Decker"
    url = "https://github.com/JohnEarnest/Decker"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "with_sdl": [True, False]}
    default_options = {"shared": False, "with_sdl": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_sdl:
            self.requires("sdl2/2.30.10")
            self.requires("sdl2_image/2.8.0")

    def layout(self):
        basic_layout(self)

    def generate(self):
        if self.options.with_sdl:
            VirtualBuildEnv(self).generate()
            PkgConfigDeps(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler - use settings.compiler to determine compiler name
        # The profile provides tools.build:compiler_executables as a JSON dict,
        # but Conan 2.x doesn't support nested key access on that conf.
        # Fall back to the standard compiler name from settings.
        cc = "clang" if str(self.settings.compiler) == "clang" else "gcc"

        version = self.version

        # All source-relative paths must be absolute. basic_layout() makes
        # self.build_folder distinct from self.source_folder, and self.run()
        # executes in self.build_folder by default — so './c/lilt.c' would
        # resolve to <build_folder>/c/lilt.c, which does not exist. Use
        # self.source_folder explicitly and run with cwd=source so the
        # upstream './scripts/resources.sh' relative commands also work.
        src = self.source_folder
        c_dir = os.path.join(src, "c")
        build_dir = os.path.join(c_dir, "build")

        # Ensure c/build/ exists before writing lilt/decker binaries into it.
        # git does not track empty dirs, so the source tarball has no c/build/.
        os.makedirs(build_dir, exist_ok=True)

        # Generate resources.h (upstream script uses relative paths).
        self.run("chmod +x scripts/resources.sh", cwd=src)
        self.run("./scripts/resources.sh examples/decks/tour.deck", cwd=src)

        # Common flags. -O2 is fixed upstream; build_type is a Makefile project
        # so we don't remap Debug/Release here.
        # _POSIX_C_SOURCE=200809L: upstream c/lib/bestline.c and lil.h use
        # fileno()/strdup()/realpath() without a feature-test macro, so on
        # HarmonyOS musl they are implicit declarations (C99 forbids this).
        # Defining _POSIX_C_SOURCE exposes the prototypes in <unistd.h>/
        # <string.h>/<stdlib.h>.
        flags = "-std=c99 -Wall -Wextra -O2 -Wno-misleading-indentation"
        flags += " -Wno-unknown-warning-option -Wno-overlength-strings -lm"
        flags += " -D_POSIX_C_SOURCE=200809L"

        lilt_src = os.path.join(c_dir, "lilt.c")
        lilt_out = os.path.join(build_dir, "lilt")

        # Build lilt (standalone interpreter, no SDL needed)
        self.run(
            f"{cc} \"{lilt_src}\" -o \"{lilt_out}\" "
            f"{flags} -DVERSION='\"{version}\"'"
        )

        # Build decker (GUI app, needs SDL2 + SDL2_image)
        if self.options.with_sdl:
            # Query SDL2 flags via self.run() redirecting pkg-config stdout to
            # temp files. Unlike os.popen(), self.run() sources the Conan build
            # environment (conanbuild.sh) so PKG_CONFIG_PATH points at the
            # PkgConfigDeps-generated .pc files. Using os.popen() would bypass
            # the Conan env and could silently fall back to any system-installed
            # sdl2 .pc, linking the wrong version.
            import tempfile
            cflags_f = tempfile.NamedTemporaryFile(
                mode="r", delete=False, suffix=".cflags")
            libs_f = tempfile.NamedTemporaryFile(
                mode="r", delete=False, suffix=".libs")
            try:
                self.run(
                    f"pkg-config --cflags sdl2 SDL2_image > \"{cflags_f.name}\"",
                    cwd=src,
                )
                self.run(
                    f"pkg-config --libs sdl2 SDL2_image > \"{libs_f.name}\"",
                    cwd=src,
                )
                sdl2_cflags = cflags_f.read().strip()
                sdl2_libs = libs_f.read().strip()
            finally:
                cflags_f.close()
                libs_f.close()
                os.unlink(cflags_f.name)
                os.unlink(libs_f.name)
            if not sdl2_cflags or not sdl2_libs:
                raise ConanException(
                    "with_sdl=True but pkg-config could not resolve "
                    "sdl2/SDL2_image flags (PKG_CONFIG_PATH / deps missing?)"
                )
            decker_src = os.path.join(c_dir, "decker.c")
            decker_out = os.path.join(build_dir, "decker")
            self.run(
                f"{cc} \"{decker_src}\" -o \"{decker_out}\" "
                f"{sdl2_cflags} {sdl2_libs} "
                f"{flags} -DVERSION='\"{version}\"'"
            )

    def package(self):
        # Binaries are built into <source_folder>/c/build/ (see build()).
        bin_src = os.path.join(self.source_folder, "c", "build")
        bin_dst = os.path.join(self.package_folder, "bin")
        # Install lilt binary (keep_path=False to flatten: bin/lilt, not bin/c/build/lilt)
        copy(self, "lilt", bin_src, bin_dst, keep_path=False)
        # Install decker binary if built
        decker_bin = os.path.join(bin_src, "decker")
        if os.path.exists(decker_bin):
            copy(self, "decker", bin_src, bin_dst, keep_path=False)
        # Install resources
        copy(self, "*.deck", os.path.join(self.source_folder, "examples", "decks"),
             os.path.join(self.package_folder, "share", "decker", "examples"))
        copy(self, "*.lil", os.path.join(self.source_folder, "tests"),
             os.path.join(self.package_folder, "share", "decker", "tests"), keep_path=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []