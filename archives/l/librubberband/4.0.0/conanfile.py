#!/usr/bin/env python3
"""Conan recipe for librubberband 4.0.0 (Meson build system).

Rubber Band Library — audio time-stretching and pitch-shifting
library from Breakfast Quay (upstream org: breakfastquay, package
name kept separate as librubberband).

Upstream 4.0.0 builds with meson (>= 0.53).  OHOS adaptation notes:
  * FFT selection: -Dfft=builtin (built-in FFT implementation).  FFTW
    is available in the registry but the builtin path keeps this
    package dependency-light; upstream default on non-darwin is
    builtin as well.
  * Resampler: -Dresampler=libsamplerate (registry package
    libsamplerate/0.2.2).  meson probes dependency('samplerate') so a
    pkg-config alias from libsamplerate.pc -> samplerate.pc is staged
    in the generators folder.
  * ladspa/lv2/vamp/jni/cmdline features are disabled (optional
    plugin/UI targets, not needed for the core library).
  * tests=enabled: upstream unit test suite (boost unit_test_framework)
    is registered as 8 meson test() targets and executed with
    `meson test` inside build() — the CI machine is itself an
    OHOS arm64 device, so the cross-built test binaries run natively
    (same approach as aravis 0.8.36).
  * boost 1.90 unit_test_framework is built as shared on OHOS; the
    upstream test.cpp hard-defines BOOST_TEST_DYN_LINK, matching it.
"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibrubberbandConan(ConanFile):
    name = "librubberband"
    version = "4.0.0"
    description = ("Rubber Band Library — audio time-stretching and "
                   "pitch-shifting library")
    license = "GPL-2.0-or-later"
    homepage = "https://breakfastquay.com/rubberband/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libsamplerate/0.2.2", transitive_headers=True,
                      transitive_libs=True)
        # boost is only needed to build/run the upstream unit tests
        # (meson dependency('boost', modules:['unit_test_framework']));
        # visible=False keeps it out of the consumer dependency chain.
        self.requires("boost/1.90.0.4.1", visible=False)

    def build_requirements(self):
        # meson from the registry (account-utils/c-list 同款先例);
        # ninja resolves from the worker PATH (OHOS SDK ships 1.13.1).
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        PkgConfigDeps(self).generate()
        self._stage_samplerate_pc_alias()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static")
        tc.project_options["fft"] = "builtin"
        tc.project_options["resampler"] = "libsamplerate"
        tc.project_options["jni"] = "disabled"
        tc.project_options["ladspa"] = "disabled"
        tc.project_options["lv2"] = "disabled"
        tc.project_options["vamp"] = "disabled"
        tc.project_options["cmdline"] = "disabled"
        tc.project_options["tests"] = "enabled"
        tc.generate()
        self._inject_ar_ranlib()

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["rubberband"]
        self.cpp_info.set_property("cmake_file_name", "rubberband")
        self.cpp_info.set_property("cmake_target_name", "rubberband::rubberband")
        self.cpp_info.set_property("pkg_config_name", "rubberband")
        self.cpp_info.requires = ["libsamplerate::libsamplerate"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _run_upstream_tests(self):
        """Run the upstream meson test suite (8 registered targets).

        The CI worker is an OHOS arm64 machine itself, so cross-built
        test binaries execute natively.  BOOST_TEST_DYN_LINK requires
        the shared boost unit_test_framework to be resolvable at
        runtime — expose its libdir through LD_LIBRARY_PATH.  Missing
        native execution support never silently passes: the run
        reports failure if the test binary does not start.
        """
        boost = self.dependencies.get("boost")
        loader_paths = []
        if boost is not None:
            for libdir in boost.cpp_info.aggregated_components().libdirs:
                loader_paths.append(libdir)
        current = os.environ.get("LD_LIBRARY_PATH")
        if current:
            loader_paths.append(current)
        if loader_paths:
            os.environ["LD_LIBRARY_PATH"] = ":".join(loader_paths)
        try:
            meson = Meson(self)
            meson.test()
        finally:
            if current is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = current

    def _stage_samplerate_pc_alias(self):
        """meson probes dependency('samplerate') — stage samplerate.pc.

        Conan generates libsamplerate.pc (package name based); the
        alias keeps upstream meson.build unpatched.
        """
        src = os.path.join(self.generators_folder, "libsamplerate.pc")
        if not os.path.isfile(src):
            return
        with open(src, encoding="utf-8") as handle:
            content = handle.read()
        alias = os.path.join(self.generators_folder, "samplerate.pc")
        with open(alias, "w", encoding="utf-8") as handle:
            handle.write(content.replace("Name: libsamplerate",
                                         "Name: samplerate", 1))

    def _inject_ar_ranlib(self):
        """OHOS cross builds need llvm-ar/llvm-ranlib in the native file."""
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if not ar:
            cc = compiler_executables.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
        native_file = os.path.join(self.generators_folder,
                                   "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar)
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib)
                content = content.replace("[binaries]\n", insertion, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _ensure_tmpdir(self):
        # /tmp is read-only on OHOS workers — keep temp inside build dir
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
