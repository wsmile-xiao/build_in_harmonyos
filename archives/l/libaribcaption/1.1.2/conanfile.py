#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# libaribcaption 1.1.2 — Conan recipe (OpenHarmony PC adaptation)
#
# Upstream: https://github.com/xqq/libaribcaption
# Portable ARIB STD-B24 Caption Decoder/Renderer (C API + C++ API).
#
# OHOS adaptation notes:
# - Upstream CMake falls into the generic Unix branch on OHOS and enables
#   ARIBCC_USE_FONTCONFIG + ARIBCC_USE_FREETYPE (same as Linux).
# - Upstream sets no VERSION/SOVERSION on the aribcaption target, so the
#   built libaribcaption.so would ship WITHOUT DT_SONAME. The CI L5a gate
#   rejects that. The linker flag is injected instead (see generate()),
#   mirroring the ayatana-ido/accessibility precedent, giving the library
#   the unversioned SONAME "libaribcaption.so" which matches the only
#   installed filename — consumers resolve it via LD_LIBRARY_PATH.
# - Upstream tests are EXCLUDE_FROM_ALL and never registered with ctest.
#   We build and run them explicitly in build() (see _run_upstream_tests).

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.scm import Version


class LibAribCaptionConan(ConanFile):
    name = "libaribcaption"
    version = "1.1.2"
    description = "Portable ARIB STD-B24 Caption Decoder/Renderer"
    license = "MIT"
    url = "https://github.com/xqq/libaribcaption"
    homepage = "https://github.com/xqq/libaribcaption"
    topics = ("arib", "caption", "subtitle", "isdb", "decoder", "renderer")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_renderer": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_renderer": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)
        # GitHub tag tarballs extract into "libaribcaption-<version>/"; the
        # conan build folder must hold the sources at its root for the
        # patches (and cmake) to find them.
        self.folders.source = "."

    def requirements(self):
        # Renderer backend (default on): fontconfig + freetype, both W0-published.
        # ARIBCC_NO_RENDERER=ON removes both the renderer and these deps.
        if self.options.get_safe("with_renderer"):
            self.requires("fontconfig/2.18.3")
            self.requires("freetype/2.14.3")

    def build_requirements(self):
        # Only needed when upstream tests are executed (test/png_writer).
        # test_requires (host context) so CMakeDeps generates the config
        # package for it (astlib/gtest precedent).
        self.test_requires("libpng/1.6.58.2")

    def validate(self):
        if self.info.settings.compiler.cppstd:
            # Library targets C++17 (target_compile_features cxx_std_17).
            if Version(str(self.info.settings.compiler.cppstd)) < "17":
                raise ConanInvalidConfiguration(
                    "libaribcaption requires C++17 or higher"
                )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Shared lib needs a real DT_SONAME on OHOS (L5a): upstream defines
        # no SOVERSION, and without it the linker records the build-tree
        # relative path (../../libaribcaption.so) as NEEDED. Re-arm the
        # standard CMake mechanism: the platform module's
        # CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG prefix + target name appended
        # by CMake yields DT_SONAME=libaribcaption.so (== installed file).
        if self.options.shared:
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["ARIBCC_BUILD_TESTS"] = True
        tc.variables["ARIBCC_NO_RENDERER"] = not self.options.with_renderer
        # caption2srt/ffmpeg tests need an external MPEG-TS sample + avcodec
        tc.variables["ARIBCC_SKIP_FFMPEG_TESTS"] = True
        # Never let upstream FetchContent an embedded freetype from the
        # network; the conan freetype package is found via find_package.
        tc.variables["ARIBCC_USE_EMBEDDED_FREETYPE"] = False
        # Renderer deps reach upstream via CMake's bundled Find modules
        # (FindFontconfig/FindFreetype) which honor CMAKE_PREFIX_PATH and
        # CMAKE_FIND_ROOT_PATH — both populated by CMakeToolchain/CMakeDeps
        # from the dependency package folders (same bridge as libxft).
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream official tests: 8 test targets exist, all EXCLUDE_FROM_ALL
        # and none registered with ctest. Build the 5 that are self-contained
        # (caption2srt/ffmpeg need an external MPEG-TS sample file passed via
        # argv, which the repo does not ship) and run them below.
        self._run_upstream_tests(cmake)

    def _run_upstream_tests(self, cmake):
        # test targets runnable without external sample data:
        #   test_alphablend — internal headers only (static build only:
        #                     Canvas/Bitmap symbols are hidden in the shared
        #                     library by upstream design)
        #   test_decode     — public ARIBCC_API decoder (any build type)
        #   test_capi       — public C API + png_writer (any build type)
        #   test_drcs       — internal renderer headers (static build only)
        #   test_fontconfig_freetype — internal renderer headers (static only)
        if self.options.shared:
            test_targets = ["test_decode", "test_capi"]
        else:
            test_targets = [
                "test_alphablend",
                "test_decode",
                "test_capi",
                "test_drcs",
                "test_fontconfig_freetype",
            ]
        for target in test_targets:
            cmake.build(target=target)

        if self.conf.get("tools.build:skip_test", default=False):
            return

        # cmake_layout multi-build-type dir: <build>/Release/<target>
        build_type = self.settings.get_safe("build_type", "Release")
        def exe_path(target):
            for cand in (Path(self.build_folder) / target,
                         Path(self.build_folder) / build_type / target):
                if cand.exists():
                    return cand
            raise ConanException(f"test executable {target} not found")

        if self.settings.os == "OHOS":
            self._run_upstream_tests_ohos([exe_path(t) for t in test_targets])
        else:
            for target in test_targets:
                self.run(f"{exe_path(target)}", cwd=self.build_folder, env="conanrun")

    def _run_upstream_tests_ohos(self, exes):
        """Run the upstream tests on the HarmonyOS PC itself.

        The conan dependency .so files are linked with `-Wl,--code-sign`
        (empty self-signature) and the musl loader refuses to map them;
        sign each library and the test executables with binary-sign-tool,
        assemble a runtime closure named by SONAME, and provide a writable
        fontconfig cache (the system font dirs are not writable and the
        packaged fonts.conf points at non-existent dirs on this device).
        """
        runlibs = Path(self.build_folder) / "runlibs"
        runlibs.mkdir(parents=True, exist_ok=True)
        # the freshly built library itself (build tree output, before packaging)
        build_type = self.settings.get_safe("build_type", "Release")
        for so in (Path(self.build_folder) / "libaribcaption.so",
                   Path(self.build_folder) / build_type / "libaribcaption.so"):
            if so.exists():
                soname = self._soname_of(so)
                if soname and not (runlibs / soname).exists():
                    shutil.copy2(so, runlibs / soname)
                    self._codesign(runlibs / soname)
        for dep in self.dependencies.values():
            if not dep.cpp_info:
                continue
            for libdir in dep.cpp_info.libdirs:
                for so in Path(libdir).glob("*.so"):
                    soname = self._soname_of(so)
                    if not soname:
                        continue
                    dst = runlibs / soname
                    if not dst.exists():
                        shutil.copy2(so, dst)
                        self._codesign(dst)

        fcdir = Path(self.build_folder) / "fc" / "cache"
        fcdir.mkdir(parents=True, exist_ok=True)
        fonts_conf = Path(self.build_folder) / "fc" / "fonts.conf"
        # HarmonyOS PC: /system/fonts ships NotoSansCJK-Regular.ttc (JP/KR/
        # SC/TC/HK faces) but no Hiragino/YuGothic/Rounded M+ families that
        # the upstream renderer prefers; alias them so fontconfig's generic
        # substitution lands on the real CJK face instead of falling back
        # to a non-CJK font (which fails DrawChar with "doesn't contain").
        fonts_conf.write_text(
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
            '<fontconfig>\n'
            '  <dir>/system/fonts</dir>\n'
            f'  <cachedir>{fcdir}</cachedir>\n'
            '  <match target="pattern">\n'
            '    <test qual="any" name="family"><string>Hiragino Maru Gothic ProN</string></test>\n'
            '    <edit name="family" mode="prepend" binding="strong"><string>Noto Sans CJK JP</string></edit>\n'
            '  </match>\n'
            '  <match target="pattern">\n'
            '    <test qual="any" name="family"><string>Hiragino Sans</string></test>\n'
            '    <edit name="family" mode="prepend" binding="strong"><string>Noto Sans CJK JP</string></edit>\n'
            '  </match>\n'
            '  <match target="pattern">\n'
            '    <test qual="any" name="family"><string>YuGothic</string></test>\n'
            '    <edit name="family" mode="prepend" binding="strong"><string>Noto Sans CJK JP</string></edit>\n'
            '  </match>\n'
            '  <match target="pattern">\n'
            '    <test qual="any" name="family"><string>Rounded M+ 1m for ARIB</string></test>\n'
            '    <edit name="family" mode="prepend" binding="strong"><string>Noto Sans CJK JP</string></edit>\n'
            '  </match>\n'
            '</fontconfig>\n'
        )

        env = Environment()
        env.define("LD_LIBRARY_PATH", str(runlibs))
        env.define("FONTCONFIG_FILE", str(fonts_conf))
        env.define("XDG_CACHE_HOME", str(fcdir))
        with env.vars(self).apply():
            for exe in exes:
                self._codesign(exe)
                self.run(f"{exe}", cwd=self.build_folder)

    def _soname_of(self, libpath):
        readelf = shutil.which("readelf")
        if not readelf:
            return None
        ret = subprocess.run([readelf, "-d", str(libpath)],
                             capture_output=True, text=True)
        for line in ret.stdout.splitlines():
            if "Library soname:" in line:
                return line.split("[")[-1].rstrip("]").strip()
        return None

    def _codesign(self, path):
        sign = shutil.which("binary-sign-tool")
        if not sign:
            self.output.warning("binary-sign-tool not found, skipping signature")
            return
        out = str(path) + ".signed"
        ret = subprocess.run(
            [sign, "sign", "-inFile", str(path), "-outFile", out, "-selfSign", "1"],
            capture_output=True, text=True,
        )
        if ret.returncode == 0:
            os.replace(out, path)
            os.chmod(path, os.stat(path).st_mode | 0o111)
        else:
            self.output.warning(f"sign failed for {path.name}: {ret.stderr[:200]}")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libaribcaption")
        self.cpp_info.set_property("cmake_target_name", "libaribcaption::libaribcaption")
        self.cpp_info.set_property("pkg_config_name", "libaribcaption")
        self.cpp_info.libs = ["aribcaption"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
        if self.options.get_safe("with_renderer"):
            self.cpp_info.requires = ["fontconfig::fontconfig", "freetype::freetype"]
