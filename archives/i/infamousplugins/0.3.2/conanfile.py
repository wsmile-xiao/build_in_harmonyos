#!/usr/bin/env python3
"""Conan recipe for infamousPlugins 0.3.2 — LV2 audio plug-in collection.

Build system : CMake (upstream declares cmake_minimum_required(VERSION 2.8))
Products     : 12 LV2 bundles installed as lib/lv2/<plug>.lv2/
               (<plug>.so + manifest.ttl + <plug>.ttl [+ *_presets.ttl])
License      : GPL-2.0-or-later
Homepage     : https://github.com/ssj71/infamousPlugins

OHOS adaptation notes
---------------------
1. Legacy LV2 header layout.  The 2023 sources still use the pre-2012 LV2
   include paths (<lv2.h> and "lv2/lv2plug.in/ns/ext/...").  LV2 1.18 — the
   version published on the ohpcd remote — installs only
   include/lv2/<spec>/<header>.h.  A private compatibility include root is
   generated under the build folder and put first on the compiler search path,
   so the 23 upstream files stay untouched (the idiom already used by
   archives/a/artyfx and archives/b/boops for this exact LV2 transition).
2. zita-resampler.  Every plug-in links -lzita-resampler by bare name and
   ewham/lushlife include <zita-resampler/resampler.h>.  The Conan dependency
   is not on the compiler/linker default search path, so its include and lib
   directories are injected through the toolchain (no upstream CMake change).
3. GUI plug-ins.  The X11/FLTK GUIs need cairo + ntk, which do not exist on
   OHOS.  Upstream's own `if(CAIRO_FOUND AND NTK_FOUND)` guard then skips them,
   exactly as on a headless Linux host; the DSP plug-ins are unaffected.
4. bin/infamous-rule (standalone cellular-automaton viewer) is not packaged:
   its main loop never returns, so the platform smoke test (<bin> --version /
   --help, conan-verify L2 and CI L2) would block forever for the whole
   package.  Records in notes.md.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
    rmdir,
    save,
)
from conan.tools.gnu import PkgConfigDeps


class InfamousPluginsConan(ConanFile):
    name = "infamousplugins"
    version = "0.3.2"
    description = (
        "infamousPlugins — LV2 audio plug-in collection (casynth, envfollower, "
        "hip2b, powerup, powercut, cheapdist, stuck, ewham, lushlife, "
        "bentdelay, mindi, octolo)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ssj71/infamousPlugins"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # The plug-ins are always built as shared objects (add_library(... SHARED));
    # the option only satisfies Conan's package_type contract.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # Legacy LV2 include path -> LV2 1.18 header it actually stands for.
    _LV2_LEGACY_HEADERS = {
        "lv2.h": "lv2/core/lv2.h",
        "lv2/lv2plug.in/ns/lv2core/lv2.h": "lv2/core/lv2.h",
        "lv2/lv2plug.in/ns/ext/urid/urid.h": "lv2/urid/urid.h",
        "lv2/lv2plug.in/ns/ext/midi/midi.h": "lv2/midi/midi.h",
        "lv2/lv2plug.in/ns/ext/atom/util.h": "lv2/atom/util.h",
        "lv2/lv2plug.in/ns/ext/atom/forge.h": "lv2/atom/forge.h",
        "lv2/lv2plug.in/ns/ext/time/time.h": "lv2/time/time.h",
        "lv2/lv2plug.in/ns/ext/buf-size/buf-size.h": "lv2/buf-size/buf-size.h",
        "lv2/lv2plug.in/ns/ext/options/options.h": "lv2/options/options.h",
        "lv2/lv2plug.in/ns/extensions/ui/ui.h": "lv2/ui/ui.h",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lv2/1.18.11-git")           # header-only LV2 core + extensions
        self.requires("fftw3f/3.3.10")             # ewham + lushlife DSP
        self.requires("libzita-resampler/1.11.2")  # ewham + lushlife DSP

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # lv2 and fftw3f are discovered by upstream's CMakeLists through
        # pkg_check_modules(), so their .pc files must be laid down in the
        # generator folder that CMakeToolchain puts on PKG_CONFIG_PATH.
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        # CMake has no "OHOS" platform name; OHOS is Linux-based (R32)
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        compat = self._write_lv2_compat_headers()
        tc.extra_cflags.append(f"-I{compat}")
        tc.extra_cxxflags.append(f"-I{compat}")

        zita_folder = self.dependencies["libzita-resampler"].package_folder
        zita_cpp_info = self.dependencies["libzita-resampler"].cpp_info
        for rel in zita_cpp_info.includedirs:
            tc.extra_cflags.append(f"-I{os.path.join(zita_folder, rel)}")
            tc.extra_cxxflags.append(f"-I{os.path.join(zita_folder, rel)}")
        for rel in zita_cpp_info.libdirs:
            tc.extra_sharedlinkflags.append(f"-L{os.path.join(zita_folder, rel)}")
            tc.extra_exelinkflags.append(f"-L{os.path.join(zita_folder, rel)}")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # cmake_minimum_required(VERSION 2.8) at line 1 of the upstream
        # CMakeLists.txt is rejected by CMake >= 4; the variable has to be on the
        # command line because the toolchain file is only read from project() on.
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()
        # Upstream ships no automated test suite: no enable_testing()/add_test()
        # anywhere, `make test` has no rule and ctest reports "No test
        # configuration file found!" (see test_package/MANIFEST.yml for the
        # audit).  The executed tests live in test_package/, so no test target
        # is called here.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Deliverable = the LV2 plug-in bundles.  bin/infamous-rule is a
        # standalone viewer whose main loop never exits (it ignores --version /
        # --help and spins until killed), which would hang the platform smoke
        # test for the whole package; see notes.md.
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            rm(self, "*", bin_dir)
            rmdir(self, bin_dir)

    def package_info(self):
        # Every product is a dlopen()ed LV2 bundle: lib/lv2/<plug>.lv2/<plug>.so
        lv2_root = os.path.join(self.package_folder, "lib", "lv2")
        bundles = sorted(os.listdir(lv2_root)) if os.path.isdir(lv2_root) else []
        self.cpp_info.libdirs = [os.path.join("lib", "lv2", bundle) for bundle in bundles]
        self.cpp_info.bindirs = []

    # ── helpers ──────────────────────────────────────────────────────────────

    def _write_lv2_compat_headers(self) -> str:
        """Create the legacy LV2 include tree under the build folder.

        Returns the root to be prepended to the compiler include search path.
        """
        root = os.path.join(self.build_folder, "lv2-legacy-include")
        for legacy_path, modern_header in self._LV2_LEGACY_HEADERS.items():
            save(
                self,
                os.path.join(root, legacy_path),
                f"/* infamousPlugins 0.3.2 / OHOS: legacy LV2 include path\n"
                f" * '{legacy_path}' -> LV2 1.18 header <{modern_header}> */\n"
                f"#include <{modern_header}>\n",
            )
        return root
