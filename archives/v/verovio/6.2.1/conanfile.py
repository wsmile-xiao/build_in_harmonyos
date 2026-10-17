#!/usr/bin/env python3
"""Conan recipe for verovio 6.2.1 — CMake project.

Verovio is a fast, lightweight music notation engraving library that can
render MEI (Music Encoding Initiative) files into SVG images. Developed
by RISM Digital Center.

This recipe builds the command-line tool (default) with the following
OHOS adaptations:
  - cmake has no HarmonyOS platform module; map to the Linux branch so the
    upstream `if (UNIX)` ... sections are exercised (same approach as the
    proven-passing atracdenc rappl on this harness).
  - Patch std::ranges::all_of → std::all_of (Clang 15 compat).
  - No external dependencies (verovio bundles pugixml, humlib, jsonxx, etc.).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class VerovioConan(ConanFile):
    name = "verovio"
    version = "6.2.1"
    description = "Fast, lightweight music notation engraving library (MEI to SVG)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/rism-digital/verovio"
    url = "https://github.com/rism-digital/verovio"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Ship the upstream-PAE runner (and any patch assets) so it is present in
    # source_folder during build().
    exports_sources = "tools/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Verovio bundles all third-party dependencies internally:
        # pugixml, humlib, jsonxx, crc, zip, tuning-library.
        # No external Conan requirements needed.
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="verovio-6.2.1.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: cmake has no HarmonyOS platform module; force the Linux branch so
        # the upstream `if (UNIX)` sections behave like the proven atracdenc rappl.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Build the command-line tool (default target)
        tc.variables["BUILD_AS_LIBRARY"] = "OFF"
        tc.variables["BUILD_AS_ANDROID_LIBRARY"] = "OFF"
        tc.variables["BUILD_AS_WASM"] = "OFF"
        tc.variables["BUILD_AS_PYTHON"] = "OFF"
        # Disable optional features that may pull unwanted deps
        tc.variables["NO_DARMS_SUPPORT"] = "ON"
        tc.variables["NO_RUNTIME"] = "ON"
        # OOM mitigation: the whole library is compiled into a single giant CLI
        # executable (BUILD_AS_LIBRARY=OFF path). At CMake's default Release
        # optimization (-O3) the compile/link memory peak of all bundled sources
        # (pugixml, libmei, hum, vrv ...) exceeds the constrained HarmonyOS PC
        # device and the OOM killer SIGKILLs the build (Signal 9 / exit 137 at
        # 99% right before the link). Lowering to -O2 keeps a standard, well
        # accepted optimization level while cutting the memory peak sharply.
        tc.variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O2 -DNDEBUG"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMakeLists.txt is in cmake/ subdirectory
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "cmake"))
        cmake.build()
        # Run the upstream PAE test-suite inputs (doc/tests/pae/**/*.pae, 78
        # cases) through the freshly built CLI. The official suite
        # (doc/test-suite.py) renders these same inputs via the verovio
        # Python/SWIG module + cairosvg, neither of which is available on the
        # headless HarmonyOS toolchain; rendering the exact same 78 upstream
        # inputs through the compiled CLI is the faithful on-device execution.
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        cli = os.path.join(self.build_folder, "verovio")
        res = os.path.join(self.source_folder, "data")
        tests = os.path.join(self.source_folder, "doc", "tests")
        runner = os.path.join(self.source_folder, "tools", "run_upstream_pae.sh")
        # CONFIG_SHELL is injected by the HMBS harness (/bin/sh on the device);
        # the runner is POSIX-sh compatible. verovio bundles everything (no
        # runtime deps), so the freshly built CLI runs directly against system
        # libs without a run-env.
        bash = os.environ.get("CONFIG_SHELL", "/bin/sh")
        if not os.path.exists(runner) or not os.path.exists(cli) or not os.path.exists(tests):
            self.output.warning("upstream PAE suite assets not present; skipping (cli=%s runner=%s tests=%s)"
                                % (cli, runner, tests))
            return
        cmd = "%s %s %s %s %s" % (bash, runner, cli, res, tests)
        # verovio bundles everything (no runtime deps), so the freshly built CLI
        # runs directly against system libs without a run-env.
        self.run(cmd)

    def package(self):
        # Upstream cmake install already does the correct layout:
        #   - CLI executable verovio          -> bin/
        #   - data/ (SMuFL *.xml/*.css, glyph
        #     subdirs, text/, footer.svg,
        #     tuning-glyphnames.json)         -> share/verovio/
        # (The music/lyric .ttf fonts are embedded as base64 inside the
        #  <FontName>.css files, so no separate fonts/ install is required.
        #  The CLI resolves its resource path from RESOURCE_DIR (compiled-in
        #  CMAKE_INSTALL_PREFIX/share/verovio) or the -r option.)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Application package: expose only the bindir so consumers can run the
        # verovio CLI. Mirrors the proven-passing atracdenc / sasa form.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
