#!/usr/bin/env python3
"""Conan recipe for freeglut 3.6.0 — OpenGL Utility Toolkit (GLUT) implementation.

This recipe adds an OpenHarmony/HarmonyOS platform back end to freeglut.
See notes.md for the full porting rationale; the two headline issues are:

1. **OHOS has no window system.**  There is no X11, no Wayland and no Android
   app-glue, so freeglut's upstream platform back ends all fail to build.  OHOS
   does expose EGL in every plain native process (EGL 1.4 OpenHarmony,
   EGL_DEFAULT_DISPLAY, pbuffer configs, EGL_KHR_surfaceless_context), so this
   recipe implements freeglut on top of **EGL pbuffer (offscreen) surfaces**.

2. **OHOS GL symbols are dispatcher stubs.**  Calling a GL entry point through
   the directly linked libGLESv2.so symbol silently does nothing
   (glGetString() returns NULL, glClear() reports no error yet does not clear),
   while the same entry point obtained from eglGetProcAddress() is the real
   driver function.  A dispatch layer therefore routes freeglut's GL calls
   through eglGetProcAddress() and is bound locally with -Wl,-Bsymbolic.
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rmdir)


class FreeglutConan(ConanFile):
    name = "freeglut"
    version = "3.6.0"
    description = ("FreeGLUT: an OpenGL Utility Toolkit (GLUT) implementation, "
                   "ported to OpenHarmony/HarmonyOS on EGL pbuffer surfaces")
    license = "X11"
    homepage = "https://github.com/freeglut/freeglut"
    url = "https://github.com/freeglut/freeglut"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    # ------------------------------------------------------------------ #
    # OHOS SDK discovery
    # ------------------------------------------------------------------ #
    def _sdk_sysroot(self):
        """Locate the OHOS native sysroot.

        Order: $OHOS_SDK_ROOT, then the newest ohos-sdk_* installation next to
        the compiler.  The EGL/GLESv2 libraries and headers live in the
        sysroot, and freeglut needs their exact paths because its CMake uses
        CMake's own FindOpenGL module (which cannot search a cross sysroot by
        itself).
        """
        env = os.environ.get("OHOS_SDK_ROOT")
        if env and os.path.isdir(env):
            # accept both the sysroot itself and the sdk root
            if os.path.isdir(os.path.join(env, "usr", "include", "EGL")):
                return env
            cand = os.path.join(env, "ohos", "native", "sysroot")
            if os.path.isdir(cand):
                return cand

        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or "/data/service/hnp/bin/clang"
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(cc))))
        for pattern in (os.path.join(base, "ohos-sdk.org", "ohos-sdk_*",
                                     "ohos", "native", "sysroot"),
                        os.path.join(base, "*", "ohos", "native", "sysroot"),
                        "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot"):
            hits = sorted(glob.glob(pattern), reverse=True)
            for h in hits:
                if os.path.isdir(os.path.join(h, "usr", "include", "EGL")):
                    return h
        return None

    def generate(self):
        tc = CMakeToolchain(self)
        # GLES path (EGL + GLES2), matching the patched CMakeLists.
        tc.variables["FREEGLUT_GLES"] = True
        tc.variables["FREEGLUT_BUILD_DEMOS"] = False
        tc.variables["FREEGLUT_BUILD_TESTS"] = False
        tc.variables["FREEGLUT_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["FREEGLUT_BUILD_STATIC_LIBS"] = not bool(self.options.shared)
        # freeglut's CMakeLists requires CMake >= 3.1.2; CMake 4 removed
        # compatibility with < 3.5 policies.
        # MUST be a **cache** variable: the toolchain file is processed after
        # CMakeLists.txt line 1 (where CMAKE_MINIMUM_REQUIRED runs), so a plain
        # tc.variables entry is applied too late and the build fails with
        # "Compatibility with CMake < 3.5 has been removed from CMake."
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        if self.settings.os == "OHOS":
            sysroot = self._sdk_sysroot()
            if not sysroot:
                self.output.warning(
                    "OHOS sysroot not found; EGL/GLESv2 paths will not be set and "
                    "configure will fail.  Set OHOS_SDK_ROOT to "
                    "<sdk>/ohos/native/sysroot.")
            else:
                inc = os.path.join(sysroot, "usr", "include")
                lib = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
                tc.variables["OPENGL_egl_LIBRARY"] = os.path.join(lib, "libEGL.so")
                tc.variables["OPENGL_gles2_LIBRARY"] = os.path.join(lib, "libGLESv2.so")
                tc.variables["OPENGL_EGL_INCLUDE_DIR"] = inc
                tc.variables["OPENGL_GLES2_INCLUDE_DIR"] = inc
                tc.variables["OPENGL_INCLUDE_DIR"] = inc
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._fix_so_permissions()
        self._sign_so_files()

    def _fix_so_permissions(self):
        """chmod 0755 the packaged .so files.

        meson/cmake installs may land with restrictive modes (observed 750 with
        owner 20001006:file_manager); CI processes that are neither owner nor in
        that group then fail to dlopen with Permission denied.  chmod does not
        alter file contents, so signing stays valid.
        """
        for so in self._packaged_so_files():
            try:
                os.chmod(so, 0o755)
            except OSError as e:
                self.output.warning(f"chmod failed for {so}: {e}")

    def _packaged_so_files(self):
        out = set()
        for pat in ("**/*.so", "**/*.so.*"):
            out.update(glob.glob(os.path.join(self.package_folder, pat), recursive=True))
        return sorted(f for f in out if not os.path.islink(f))

    def _sign_so_files(self):
        """Re-sign the packaged .so files for OHOS.

        Installing rewrites RUNPATH, changing the file bytes and invalidating the
        .codesign section written at link time; such a file still carries a
        .codesign section but its contents no longer match, and dlopen fails
        with Permission denied.  Verified on device: signing the packaged file
        makes dlopen succeed.
        """
        signer = next((p for p in ("/data/service/hnp/bin/binary-sign-tool",
                                   "/storage/Users/currentUser/usr/local/bin/binary-sign-tool")
                       if os.path.isfile(p)), None)
        objcopy = next((p for p in ("/data/service/hnp/bin/llvm-objcopy",
                                    "/storage/Users/currentUser/usr/local/bin/llvm-objcopy")
                        if os.path.isfile(p)), None)
        if signer is None:
            self.output.warning(
                "binary-sign-tool not found; skipping .so signing -- unsigned .so "
                "files cannot be dlopen()ed on OHOS.  Ignore on non-OHOS hosts.")
            return
        n = 0
        for so in self._packaged_so_files():
            if objcopy:
                self.run(f'"{objcopy}" --remove-section .codesign "{so}" 2>/dev/null || true',
                         ignore_errors=True)
            self.run(f'"{signer}" sign -inFile "{so}" -outFile "{so}" -selfSign 1')
            try:
                os.chmod(so, 0o755)
            except OSError as e:
                self.output.warning(f"chmod failed for {so}: {e}")
            n += 1
        self.output.info(f"signed {n} .so file(s) for OHOS")

    def package_info(self):
        # The shared library is installed as libfreeglut-gles.so because the
        # FREEGLUT_GLES build renames it (upstream behaviour).
        self.cpp_info.libs = ["freeglut-gles"]
        self.cpp_info.set_property("cmake_file_name", "freeglut")
        self.cpp_info.set_property("cmake_target_name", "freeglut::freeglut")
        self.cpp_info.set_property("pkg_config_name", "freeglut")
        # Consumers must define FREEGLUT_GLES to bootstrap GLES header inclusion
        # (see include/GL/freeglut_std.h).
        self.cpp_info.defines = ["FREEGLUT_GLES"]
        if self.settings.os == "OHOS":
            self.cpp_info.system_libs = ["EGL", "GLESv2"]
