#!/usr/bin/env python3
"""Conan recipe for critter 2.0.4 on HarmonyOS PC (OHOS / aarch64 / musl / libc++).

Critter is a top-down arcade shooter, the SDL2 fork of Critical Mass.  Upstream
ships a CMake build (the root Makefile is Emscripten-only) and declares no
install rules at all, so packaging is done by hand in package().

OHOS adaptation points
----------------------
1. VERSION: the root CMakeLists derives VERSION from
   `git describe --always --tags --abbrev=0` and raises FATAL_ERROR when no tag
   is reachable.  A release tarball carries no git metadata, so VERSION is
   injected explicitly instead.

2. 3rdparty/glm: the root CMakeLists appends
   -I${PROJECT_SOURCE_DIR}/3rdparty/glm, but the release tarball ships no
   3rdparty/ directory at all.  glm (used by game/Particles.cpp) comes from the
   registry.

3. GLEW / desktop GL: OHOS has neither.  The GL stack is gl4es/1.1.6.  This
   recipe ships compat/GL/glew.h + compat/glew-shim.c (same approach as
   logstalgia/1.1.4): the header supplies the GLEW entry points Critter calls
   plus the GL_KHR_debug subset used by its DEBUG_OPENGL block, and the shim is
   archived into a static libGLEW.a that CMake's FindGLEW picks up
   (GLEW_USE_STATIC_LIBS=ON -> GLEW::glew_s).  The header exists mainly because
   gl4es' GL/gl.h defines GL_GLEXT_PROTOTYPES only under __EMSCRIPTEN__ /
   __APPLE__, so the desktop GL 2.0/3.0 prototypes would otherwise be missing.

4. Legacy CMake variables: upstream links ${SDL2_LIBRARIES},
   ${SDL2_IMAGE_LIBRARY}, ${SDL2_MIXER_LIBRARY}, ${PHYSFS_LIBRARY},
   ${PNG_LIBRARY}, ${ZLIB_LIBRARY} and ${OPENGL_LIBRARY} - the variables
   produced by its own find-modules (mooflu.common/utilscmake/) and by CMake's
   FindZLIB / FindPNG / FindOpenGL.  CMakeDeps only emits modern IMPORTED
   targets, so those legacy variables are seeded from the dependency package
   folders before configure runs.

5. resource.dat: the root CMakeLists feeds ${PROJECT_SOURCE_DIR}/resource.dat to
   add_executable(), so the archive has to exist before configure.  It is not
   part of the tarball (upstream builds it with `zip -9r` over data/), so build()
   packs it.  At runtime the game mounts it through PhysFS relative to its
   working directory, hence it is installed next to the executable.

6. Runtime: gl4es dlopen()s its EGL/GLES backend instead of linking it, so
   package_info() exports LIBGL_GLES / LIBGL_EGL (same as gl4es' own
   test_package and logstalgia/1.1.4).
"""

import glob
import os
import shlex
import shutil
import zipfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout

# Name the GLEW shim archive carries; CMake's FindGLEW searches for these.
_GLEW_LIB_NAME = "libGLEW.a"


class CritterConan(ConanFile):
    name = "critter"
    version = "2.0.4"
    description = ("Critter - SDL2/OpenGL top-down arcade shooter "
                   "(Critical Mass fork)")
    license = "GPL-2.0-only"
    url = "https://github.com/mooflu/critter"
    homepage = "https://games.mooflu.com/"
    topics = ("game", "sdl2", "opengl", "gl4es", "ohos")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # GL/GLEW compat sources (see module docstring, point 3).
    def export_sources(self):
        copy(self, "compat/GL/glew.h", self.recipe_folder,
             self.export_sources_folder)
        copy(self, "compat/glew-shim.c", self.recipe_folder,
             self.export_sources_folder)

    # ------------------------------------------------------------------
    # configuration
    # ------------------------------------------------------------------
    def validate(self):
        # R32: the OHOS build host also reports "OHOS"; Linux stays accepted so
        # the recipe can be sanity-checked natively.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports Linux/OHOS only "
                "(gl4es + SDL2 OpenGL stack)")

    def requirements(self):
        # game/main.cpp prints zlibVersion() and game/CMakeLists links
        # ${ZLIB_LIBRARY}, so zlib is a genuine direct dependency rather than an
        # override-only node.  libpng/1.6.58 keeps its zlib floor in step with
        # libtiff/4.7.2 (both settle on zlib/1.3.1.1) - the same pin
        # criticalmass/1.0.2 uses, and the runtime banner confirms both
        # ("zlib Version 1.3.1", "PNG Version 1.6.58").
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        self.requires("sdl2/2.30.10")
        self.requires("sdl2-image/2.8.12")
        self.requires("sdl2-mixer/2.8.2")
        self.requires("physfs/3.2.0.1")
        self.requires("gl4es/1.1.6")
        self.requires("glm/0.9.9.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # No patches are required today; kept so the recipe follows the repo
        # template and a future adaptation fix only has to add a patches: entry
        # to conandata.yml.  With no patches: section this is a no-op.
        apply_conandata_patches(self)

    # ------------------------------------------------------------------
    # dependency helpers
    # ------------------------------------------------------------------
    def _dep_folder(self, name):
        """Package folder of a (possibly transitive) dependency, or None."""
        try:
            folder = self.dependencies[name].package_folder
        except (KeyError, ConanException):
            return None
        return folder or None

    def _dep_include(self, name):
        folder = self._dep_folder(name)
        return os.path.join(folder, "include") if folder else None

    @staticmethod
    def _pick(folder, patterns, kind="lib"):
        """First usable library in `folder`/kind matching `patterns`.

        Preference: a plain/static archive before a versioned shared object,
        then the shortest name (libz.a before libz.so.1.3.1.1).
        """
        for pattern in patterns:
            hits = sorted(glob.glob(os.path.join(folder, kind, pattern)))
            if hits:
                hits.sort(key=lambda path: (".so." in path, len(path)))
                return hits[0]
        return None

    def _require_lib(self, name, patterns):
        folder = self._dep_folder(name)
        if folder is None:
            raise ConanException(f"dependency {name} has no package folder")
        lib = self._pick(folder, patterns)
        if not lib:
            raise ConanException(
                f"no library matching {patterns} in {folder}/lib "
                f"(dependency {name})")
        return lib

    # ------------------------------------------------------------------
    # OHOS compat prefix: gl4es headers + GLEW shim
    # ------------------------------------------------------------------
    def _compat_dir(self):
        return os.path.join(self.build_folder, "compat")

    def _compat_include(self):
        return os.path.join(self._compat_dir(), "include")

    def _gl4es_include(self):
        return self._dep_include("gl4es")

    def _materialize_compat(self):
        """Populate the private compat prefix with GL headers and the GLEW shim.

        R49: everything stays inside the build folder - no shared prefix such as
        /usr/local is ever written to (CI workers share the filesystem).
        """
        compat = self._compat_dir()
        include_dir = self._compat_include()
        os.makedirs(os.path.join(compat, "lib"), exist_ok=True)
        # gl4es' GL/ headers, so the prefix is self-contained for FindGLEW
        copy(self, "*", src=self._gl4es_include(), dst=include_dir)
        copy(self, "GL/glew.h", src=os.path.join(self.source_folder, "compat"),
             dst=include_dir)
        copy(self, "glew-shim.c", src=os.path.join(self.source_folder, "compat"),
             dst=compat)
        return include_dir

    def _compile_glew_shim(self):
        """Archive compat/glew-shim.c into <compat>/lib/libGLEW.a."""
        compat = self._compat_dir()
        libdir = os.path.join(compat, "lib")
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        # R33: never rely on bare ${CC}/${AR}; the SDK compiler comes from conf.
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        target = ""
        if self.settings.os == "OHOS" and self.settings.arch == "armv8":
            # be explicit; the SDK clang would otherwise take the build host
            target = " --target=aarch64-linux-ohos"
        obj = os.path.join(libdir, "glew-shim.o")
        self.run(
            f"{cc}{target} -O2 -fPIC -c "
            f"{shlex.quote(os.path.join(compat, 'glew-shim.c'))} -o "
            f"{shlex.quote(obj)} -I{shlex.quote(self._compat_include())} "
            f"-I{shlex.quote(self._gl4es_include())}",
            env="conanbuild")
        shim_lib = os.path.join(libdir, _GLEW_LIB_NAME)
        self.run(f"{ar} rcs {shlex.quote(shim_lib)} {shlex.quote(obj)}",
                 env="conanbuild")
        return shim_lib

    def _write_resource_dat(self):
        """Pack data/ into resource.dat, mirroring upstream `zip -9r`.

        The root CMakeLists hands ${PROJECT_SOURCE_DIR}/resource.dat to
        add_executable(), and the runtime mounts it through PhysFS, so the
        archive must exist before configure and carry the very same layout
        (top-level entries, no leading "./").
        """
        dat = os.path.join(self.source_folder, "resource.dat")
        if os.path.isfile(dat):
            self.output.info(f"reusing existing resource.dat "
                             f"({os.path.getsize(dat)} bytes)")
            return dat
        data_dir = os.path.join(self.source_folder, "data")
        if not os.path.isdir(data_dir):
            raise ConanException(
                f"upstream data/ directory missing below {self.source_folder}")
        with zipfile.ZipFile(dat, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for root, _dirs, files in os.walk(data_dir):
                for name in sorted(files):
                    full = os.path.join(root, name)
                    archive.write(full, os.path.relpath(full, data_dir))
        self.output.info(f"packed resource.dat ({os.path.getsize(dat)} bytes)")
        return dat

    # ------------------------------------------------------------------
    # cmake invocation
    # ------------------------------------------------------------------
    def _include_dirs(self):
        """Header trees upstream CMakeLists does not propagate.

        It forwards only ${SDL2_INCLUDE_DIRS} plus ${CMAKE_PREFIX_PATH}/include,
        so every other component's include dir is added explicitly.  SDL_image.h
        and SDL_mixer.h do `#include "SDL.h"`, which resolves only with the SDL2
        core's own SDL2/ subdirectory on the include path.
        """
        dirs = [self._compat_include(), self._gl4es_include()]
        for name in ("sdl2", "sdl2-mixer", "sdl2-image", "physfs",
                     "libpng", "zlib", "glm"):
            folder = self._dep_folder(name)
            if folder:
                dirs.append(os.path.join(folder, "include"))
        for name in ("sdl2", "sdl2-mixer", "sdl2-image"):
            folder = self._dep_folder(name)
            if folder:
                nested = os.path.join(folder, "include", "SDL2")
                if os.path.isdir(nested):
                    dirs.append(nested)
        return dirs

    def _cmake_args(self):
        sdl_lib = self._require_lib(
            "sdl2", ["libSDL2.a", "libSDL2.so*", "libSDL2-2.0.so*"])
        mixer_lib = self._require_lib(
            "sdl2-mixer",
            ["libSDL2_mixer.a", "libSDL2_mixer.so*", "*.a", "*.so*"])
        # libSDL2_image.a is static with TIFF/WebP support compiled in, so the
        # backing libraries have to join the link line as well.
        image_libs = [self._require_lib(
            "sdl2-image",
            ["libSDL2_image.a", "libSDL2_image.so*", "*.a", "*.so*"])]
        for name, patterns in (("libwebp", ["libwebp.so*", "libwebp.a"]),
                               ("libwebp", ["libwebpdemux.so*", "libwebpdemux.a"]),
                               ("libtiff", ["libtiff.so*", "libtiff.a"])):
            folder = self._dep_folder(name)
            if folder:
                lib = self._pick(folder, patterns)
                if lib:
                    image_libs.append(lib)
        physfs_lib = self._require_lib(
            "physfs", ["libphysfs.a", "libphysfs.so*", "*.a", "*.so*"])
        png_lib = self._require_lib(
            "libpng", ["libpng.a", "libpng*.a", "libpng*.so*"])
        zlib_lib = self._require_lib("zlib", ["libz.a", "libz.so*"])
        gl_lib = self._require_lib("gl4es", ["libGL.so*", "libGL.a"])

        include_flags = " ".join(f"-I{d}" for d in self._include_dirs())
        args = [
            f"-DCMAKE_TOOLCHAIN_FILE={os.path.join(self.generators_folder, 'conan_toolchain.cmake')}",
            # a release tarball has no git tag for `git describe` to find
            f"-DVERSION={self.version}",
            # the compat prefix carries the GLEW shim FindGLEW must locate
            f"-DCMAKE_PREFIX_PATH={self._compat_dir()};{self.generators_folder}",
            # upstream adds no include dirs of its own beyond SDL2's
            f"-DCMAKE_C_FLAGS={include_flags}",
            f"-DCMAKE_CXX_FLAGS={include_flags}",
            # static shim archive -> GLEW::glew_s
            "-DGLEW_USE_STATIC_LIBS=ON",
            "-DBUILD_SHARED_LIBS=OFF",
            # CMake's FindZLIB / FindPNG (module mode) honour seeded cache vars
            f"-DZLIB_LIBRARY={zlib_lib}",
            f"-DZLIB_INCLUDE_DIR={self._dep_include('zlib')}",
            f"-DPNG_LIBRARY={png_lib}",
            f"-DPNG_PNG_INCLUDE_DIR={self._dep_include('libpng')}",
            # SDL2 core: CMakeDeps resolves find_package(SDL2), upstream then
            # consumes the upper-case variable names
            f"-DSDL2_LIBRARIES={sdl_lib}",
            f"-DSDL2_INCLUDE_DIRS={self._dep_include('sdl2')}",
            # upstream-shipped find-modules (utilscmake) honour seeded cache vars
            f"-DSDL2_MIXER_LIBRARY={mixer_lib}",
            f"-DSDL2_MIXER_INCLUDE_DIR={self._dep_include('sdl2-mixer')}",
            f"-DSDL2_IMAGE_LIBRARY={';'.join(image_libs)}",
            f"-DSDL2_IMAGE_INCLUDE_DIR={self._dep_include('sdl2-image')}",
            f"-DPHYSFS_LIBRARY={physfs_lib}",
            f"-DPHYSFS_INCLUDE_DIR={self._dep_include('physfs')}",
            # gl4es provides libGL.so; FindOpenGL must not go looking for GLX
            f"-DOPENGL_gl_LIBRARY={gl_lib}",
            f"-DOPENGL_INCLUDE_DIR={self._gl4es_include()}",
        ]
        return args

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        self._materialize_compat()
        self._compile_glew_shim()
        self._write_resource_dat()

        # cmake is driven directly (rather than through the CMake helper) so the
        # exact argument set stays visible next to the comments explaining why
        # each legacy variable has to be seeded.
        generator = "Ninja" if shutil.which("ninja") else "Unix Makefiles"
        configure = ["cmake", "-S", self.source_folder, "-B", self.build_folder,
                     "-G", generator,
                     f"-DCMAKE_BUILD_TYPE={self.settings.build_type}"]
        configure += self._cmake_args()
        command = " ".join(shlex.quote(arg) for arg in configure)
        self.output.info(f"cmake configure: {command}")

        # R33/runtime: OHOS /bin/sh is mksh and resets LD_LIBRARY_PATH, which
        # kills conan-injected loader paths; env="conanbuild" routes through the
        # bash from the profile instead.
        self.run(command, env="conanbuild")
        self.run(" ".join(shlex.quote(arg) for arg in (
            ["cmake", "--build", self.build_folder, "-j",
             str(os.cpu_count() or 2)])), env="conanbuild")

    # ------------------------------------------------------------------
    # packaging
    # ------------------------------------------------------------------
    def _built_executable(self):
        candidates = [path for path in glob.glob(
            os.path.join(self.build_folder, "**", "critter"), recursive=True)
            if os.path.isfile(path) and not path.endswith(".o")]
        if not candidates:
            raise ConanException(
                f"critter executable not found under {self.build_folder}")
        candidates.sort(key=len)
        exe = candidates[0]
        with open(exe, "rb") as handle:
            if handle.read(4) != b"\x7fELF":
                raise ConanException(f"{exe} is not an ELF binary")
        return exe

    def package(self):
        exe = self._built_executable()
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, os.path.basename(exe), src=os.path.dirname(exe), dst=bindir)
        # the game mounts ./resource.dat through PhysFS at runtime, so the
        # archive lives next to the executable (upstream has no install rules)
        copy(self, "resource.dat", src=self.source_folder, dst=bindir)
        copy(self, "critter.6", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man6"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # gl4es dlopen()s its backend, so consumers that launch critter need
        # LIBGL_* pointed at the OHOS system GLES3/EGL stacks.
        self.runenv_info.define("LIBGL_GLES", "/system/lib64/libGLESv3.so")
        self.runenv_info.define("LIBGL_EGL", "/system/lib64/libEGL.so")
