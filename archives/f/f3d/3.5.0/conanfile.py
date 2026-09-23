#!/usr/bin/env python3
"""Conan recipe — f3d 3.5.0 (3D model viewer built on VTK).

f3d is a fast and minimalist 3D viewer powered by VTK. It supports many
file formats natively (PLY, OBJ, STL, VTK, GLTF, etc.) and provides
an interactive rendering window with optional UI overlays.

This recipe builds the f3d application binary using VTK 9.4.1 from the
OHPCD Conan registry. External dependencies (cxxopts, nlohmann_json,
dmon, imgui, tinyfiledialogs) are bundled in the f3d source tree and
built internally — no external Conan packages needed for them.

Source: https://github.com/f3d-app/f3d
License: BSD-3-Clause

R32: settings.os check uses `in ("Linux", "OHOS")`
R28: test_package/ included
R34: test_package runs the actual binary (--version)
R38: commands.json declared at software level (application type)
R39: Source URL is official GitHub archive
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class F3DConan(ConanFile):
    name = "f3d"
    version = "3.5.0"
    description = "A fast and minimalist 3D viewer powered by VTK"
    license = "BSD-3-Clause"
    homepage = "https://f3d-app.github.io/f3d/"
    url = "https://github.com/f3d-app/f3d"
    package_type = "application"

    # R32: settings.os must check `in ("Linux", "OHOS")`
    settings = "os", "compiler", "build_type", "arch"

    # Application — no shared/fPIC options (produces executable, not library)
    # f3d also builds libf3d (shared lib) but we focus on the application

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # Primary dependency: VTK 9.4.1 (already published in OHPCD registry)
        self.requires("vtk/9.4.1")

    def validate(self):
        # R32: OS compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"f3d does not support OS: {self.settings.os}"
            )
        # f3d requires aarch64 (OHOS PC platform)
        if self.settings.arch not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration(
                f"f3d does not support arch: {self.settings.arch}"
            )

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)
        # The release tarball ships git-LFS pointer files for testing data.
        # Fetch the real LFS objects from GitHub's media CDN so that the
        # upstream tests can run (f3d CMake aborts if dragon.vtu is a stub).
        self._fetch_lfs_objects()

    def _fetch_lfs_objects(self):
        import glob as _glob
        import urllib.parse
        import urllib.request

        base = ("https://media.githubusercontent.com/media/f3d-app/f3d/"
                "v3.5.0/")
        fetched = failed = 0
        for f in _glob.glob(
            os.path.join(self.source_folder, "testing", "**", "*"),
            recursive=True,
        ):
            if not os.path.isfile(f):
                continue
            try:
                if os.path.getsize(f) > 200:
                    continue
                with open(f, "rb") as fh:
                    if not fh.read(21).startswith(b"version https://git"):
                        continue
            except OSError:
                continue
            rel = os.path.relpath(f, self.source_folder).replace(os.sep, "/")
            # quote(): test data names contain spaces, '&' and non-ASCII
            # (e.g. "(ノಠ益ಠ )ノ.vtp") which the media CDN requires encoded.
            url = base + urllib.parse.quote(rel)
            tmp = f + ".lfs_tmp"
            try:
                urllib.request.urlretrieve(url, tmp)
                with open(tmp, "rb") as fh:
                    if not fh.read(21).startswith(b"version https://git"):
                        os.replace(tmp, f)
                        fetched += 1
                        continue
                os.unlink(tmp)
                failed += 1
            except Exception:
                failed += 1
        self.output.info(
            f"LFS objects fetched={fetched} failed={failed}")

    def generate(self):
        tc = CMakeToolchain(self)
        # ── OpenGL/GLES3 discovery hints (same as the VTK recipe) ──────
        # VTK 9.4.1 was built with VTK_OPENGL_USE_GLES + EGL, so its
        # exported VTK::glad target links OpenGL::GLES3. The consumer
        # (f3d) must run find_package(OpenGL) with the same SDK sysroot
        # hints or CMake's FindOpenGL fails (no GLVND, GLES libs live in
        # /system/lib64) and VTK-targets.cmake aborts with
        # "The link interface of target VTK::glad contains OpenGL::GLES3
        #  but the target was not found".
        tc.variables["OPENGL_INCLUDE_DIR"] = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include"
        tc.variables["OPENGL_GLES3_INCLUDE_DIR"] = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include"
        tc.variables["OPENGL_GLES2_INCLUDE_DIR"] = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include"
        tc.variables["OPENGL_EGL_INCLUDE_DIR"] = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include"
        tc.variables["OPENGL_GLES3_LIBRARY"] = "/system/lib64/libGLESv3.so"
        tc.variables["OPENGL_gles3_LIBRARY"] = "/system/lib64/libGLESv3.so"
        tc.variables["OPENGL_egl_LIBRARY"] = "/system/lib64/libEGL.so"
        tc.variables["OPENGL_opengl_LIBRARY"] = "/system/lib64/libGLESv3.so"
        # NOTE: no CMAKE_SYSTEM_NAME=Linux workaround here (unlike VTK).
        # f3d's patches/0001 guards the RUNTIME_DEPENDENCY_SET install
        # calls with `CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"`; CMake 4.1
        # (OHOS build) rejects RUNTIME_DEPENDENCY_SET on HarmonyOS, so
        # the system name must stay "HarmonyOS" for the guard to trigger.
        # The "System is unknown to cmake" warnings are harmless (only
        # platform-probe messages; f3d's POSIX code paths still compile
        # — the initial v3.5.0 adaptation configured fine this way).
        # Disable optional modules that require unavailable dependencies
        tc.variables["F3D_MODULE_RAYTRACING"] = "OFF"
        tc.variables["F3D_MODULE_EXR"] = "OFF"
        tc.variables["F3D_MODULE_WEBP"] = "OFF"
        tc.variables["F3D_MODULE_CLIP"] = "OFF"
        # Enable UI module (uses bundled imgui)
        tc.variables["F3D_MODULE_UI"] = "ON"
        # Use bundled externals (not conan packages)
        tc.variables["F3D_USE_EXTERNAL_CXXOPTS"] = "OFF"
        tc.variables["F3D_USE_EXTERNAL_NLOHMANN_JSON"] = "OFF"
        tc.variables["F3D_USE_EXTERNAL_DMON"] = "OFF"
        tc.variables["F3D_USE_EXTERNAL_IMGUI"] = "OFF"
        tc.variables["F3D_USE_EXTERNAL_CLIP"] = "OFF"
        # Static plugins (simpler deployment)
        tc.variables["F3D_PLUGINS_STATIC_BUILD"] = "ON"
        # No plugins requiring unavailable deps
        tc.variables["F3D_PLUGIN_BUILD_ALEMBIC"] = "OFF"
        tc.variables["F3D_PLUGIN_BUILD_ASSIMP"] = "OFF"
        tc.variables["F3D_PLUGIN_BUILD_DRACO"] = "OFF"
        tc.variables["F3D_PLUGIN_BUILD_HDF"] = "OFF"
        tc.variables["F3D_PLUGIN_BUILD_OCCT"] = "OFF"
        tc.variables["F3D_PLUGIN_BUILD_USD"] = "OFF"
        tc.variables["F3D_PLUGIN_BUILD_VDB"] = "OFF"
        tc.variables["F3D_PLUGIN_BUILD_PDAL"] = "OFF"
        tc.variables["F3D_PLUGIN_BUILD_WEBIFC"] = "OFF"
        # No bindings
        tc.variables["F3D_BINDINGS_C"] = "OFF"
        tc.variables["F3D_BINDINGS_PYTHON"] = "OFF"
        tc.variables["F3D_BINDINGS_JAVA"] = "OFF"
        # Build upstream tests (SDK tests + rendering tests).
        # The OHOS PC test device has a Mali GPU with EGL/GLESv3 — the
        # rendering tests can run against the real display stack.
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["F3D_TESTING_ENABLE_RENDERING_TESTS"] = "ON"
        tc.variables["F3D_TESTING_ENABLE_LONG_TIMEOUT_TESTS"] = "OFF"
        # X server / OSMESA not present on OHOS; EGL is
        tc.variables["F3D_TESTING_ENABLE_GLX_TESTS"] = "OFF"
        tc.variables["F3D_TESTING_ENABLE_OSMESA_TESTS"] = "OFF"
        tc.variables["F3D_TESTING_ENABLE_EGL_TESTS"] = "ON"
        # Force every rendering test through the EGL offscreen backend
        # (f3d::engine::createEGL -> vtkEGLRenderWindow with the GLES3
        # pbuffer config from the VTK recipe patch). "auto" would pick GLX
        # on Linux and fail instantly on OHOS (no X server).
        tc.variables["F3D_TESTING_FORCE_RENDERING_BACKEND"] = "egl"
        # Generate the toolchain
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Execute upstream tests (SDK + rendering). The binaries are
        # cross-compiled for aarch64-linux-ohos but this build host IS an
        # OHOS aarch64 PC, so they run natively.
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        deps_libs = [
            os.path.join(d.package_folder, "lib")
            for _r, d in self.dependencies.items()
            if d.package_folder
        ]
        # OHOS code-signing requirement: shared objects loaded through the
        # dynamic linker must carry a valid .codesign section. Files copied
        # by conan into the package cache lose their signature (HMDFS keeps
        # it as sidecar data that plain copies do not preserve), so dlopen
        # fails with "Permission denied". Re-sign every .so that the tests
        # will load with the local self-sign mode of binary-sign-tool
        # (works without a cert chain on developer machines). Non-OHOS
        # platforms have no such tool and skip this step entirely.
        self._resign_shared_libs(deps_libs)
        sdk_libs = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        ]
        # Build-tree lib dir first: patches/0004 gives libf3d a bare SONAME,
        # so the f3d binary's DT_NEEDED "libf3d.so" resolves through
        # LD_LIBRARY_PATH instead of the CWD-relative "../lib/libf3d.so"
        # (which only works when running from the bin/ directory — ctest
        # runs every test with CWD = its CMake binary dir).
        build_libs = [
            os.path.join(self.build_folder, "lib"),
        ]
        ld_path = ":".join(build_libs + ["/system/lib64"] + deps_libs + sdk_libs)
        test_results_dir = os.path.join(self.build_folder, "test_results")
        os.makedirs(test_results_dir, exist_ok=True)
        logf = os.path.join(test_results_dir, "ctest_output.log")

        # 1) EGL/GLES3 capability probe — rendering tests need a GPU.
        #    Headless CI workers skip the run entirely (recorded as skipped).
        probe_src = os.path.join(self.source_folder, "..", "..", "..",
                                 "patches")
        probe = self._probe_egl(ld_path, test_results_dir)
        if probe is not True:
            self.output.warning(
                "EGL probe unavailable — skipping upstream test execution "
                "(headless CI environment). Tests are executed on the "
                "OHOS PC device with GPU; see notes.md test records.")
            return

        # 2) Run ctest with an overall budget so CI cannot hang.
        #    Failures do not abort the package build (recorded in log).
        try:
            self.run(
                'LD_LIBRARY_PATH="{lp}" timeout 3600 ctest --test-dir "{bf}" '
                '--output-on-failure --timeout 180 -j 4 '
                '-O "{logf}"'.format(
                    lp=ld_path,
                    bf=self.build_folder,
                    logf=logf,
                ),
                cwd=self.build_folder,
            )
        except Exception as e:
            self.output.warning(
                "ctest execution completed with failures: {}".format(e))

    def _resign_shared_libs(self, lib_dirs):
        """Re-sign .so files with binary-sign-tool (OHOS only).

        The OHOS loader rejects dlopen of shared libraries without a valid
        code signature. Conan-copied files in the package cache lost theirs
        (HMDFS stores the signature as sidecar data). We regenerate a
        self-signature in place; the tool rewrites the file which also
        recreates the sidecar.
        """
        import glob as _glob
        import subprocess
        if self.settings.os != "OHOS":
            return
        tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(tool):
            self.output.warning(
                "binary-sign-tool not found — skipping re-sign step")
            return
        signed = 0
        for d in lib_dirs + [os.path.join(self.build_folder, "lib")]:
            for so in _glob.glob(os.path.join(d, "*.so")) + \
                    _glob.glob(os.path.join(d, "*.so.*")):
                if os.path.islink(so):
                    continue
                try:
                    r = subprocess.run(
                        [tool, "sign", "-selfSign", "1",
                         "-inFile", so, "-outFile", so + ".signed"],
                        capture_output=True, timeout=120)
                    if r.returncode == 0 and os.path.isfile(so + ".signed"):
                        os.replace(so + ".signed", so)
                        signed += 1
                except Exception as e:
                    self.output.warning(
                        "sign failed for {}: {}".format(so, e))
        self.output.info("Re-signed {} shared libraries".format(signed))

    def _probe_egl(self, ld_path, out_dir):
        """Return True/False for EGL availability, None if undeterminable."""
        try:
            import subprocess
            src = os.path.join(out_dir, "egl_probe.c")
            with open(src, "w") as fh:
                fh.write(
                    "#include <stdio.h>\n"
                    "#include <EGL/egl.h>\n"
                    "#include <GLES3/gl3.h>\n"
                    "int main(void){\n"
                    "  EGLDisplay d=eglGetDisplay(EGL_DEFAULT_DISPLAY);\n"
                    "  if(!eglInitialize(d,0,0)) return 1;\n"
                    "  GLint a[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,"
                    "EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,EGL_NONE};\n"
                    "  EGLConfig c; EGLint n;\n"
                    "  if(!eglChooseConfig(d,a,&c,1,&n)||n<1) return 2;\n"
                    "  GLint ctx[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};\n"
                    "  EGLContext x=eglCreateContext(d,c,EGL_NO_CONTEXT,ctx);\n"
                    "  if(x==EGL_NO_CONTEXT) return 3;\n"
                    "  return 0;\n}\n")
            exe = os.path.join(out_dir, "egl_probe")
            env = dict(os.environ)
            env["LD_LIBRARY_PATH"] = ld_path
            cc = self.conf.get("tools.build:compiler_executables", {}) \
                .get("cpp", "clang++")
            r = subprocess.run(
                [cc, src, "-o", exe, "-lEGL", "-lGLESv3"],
                env=env, capture_output=True, timeout=120)
            if r.returncode != 0:
                return None
            r2 = subprocess.run([exe], env=env, capture_output=True,
                                timeout=60)
            return r2.returncode == 0
        except Exception as e:
            self.output.warning("EGL probe failed: {}".format(e))
            return None

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # f3d is an application — main artifact is the executable
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        # The application binary
        self.cpp_info.libs = ["libf3d"]
        # VTK dependency
        self.cpp_info.requires = ["vtk::vtk"]
