#!/usr/bin/env python3
"""Conan recipe for libspecbleach 0.4.1 (audio noise reduction, C/CMake).

- CMake build, vendored pffft, optional libsndfile only used by 2 upstream
  integration tests (skipped when sndfile is not resolvable).
- Unit + integration CTest suite runs in build() (upstream tests), except
  the two sndfile-gated entries which are not instantiated in this recipe.
- OHOS ELF signing for test executables so they can run on device/CI.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibspecbleachConan(ConanFile):
    name = "libspecbleach"
    version = "0.4.1"
    description = "C library for audio noise reduction and other spectral effects"
    license = "MIT"
    homepage = "https://github.com/lucianodato/libspecbleach"
    url = "https://github.com/lucianodato/libspecbleach"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["ENABLE_TESTS"] = True
        tc.variables["ENABLE_EXAMPLES"] = False
        tc.variables["SPECBLEACH_BUILD_EXTRAS"] = True
        # AVX only applies to x86_64; keep off for arm64 (aarch64 OHOS).
        tc.variables["ENABLE_AVX"] = False
        tc.generate()

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing upstream test executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".libspecbleach-signed"
        try:
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
                check=True,
                timeout=60,
            )
        except (subprocess.CalledProcessError, OSError):
            # Signing infrastructure absent on non-OHOS hosts: fall back to
            # running the unsigned binary (native Linux/an emulator case).
            return
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not self.options.shared and can_run(self):
            if str(self.settings.os) == "OHOS":
                for test_name in (
                    "test_utils", "test_integration", "test_fft",
                    "test_spectral_whitening", "test_stft_latency",
                    "test_gain_calculator", "test_shared_utils",
                    "test_noise_profile", "test_specbleach_denoiser",
                    "test_spectral_denoiser", "test_noise_floor_manager",
                    "test_adaptive_noise_estimator", "test_nlm_filter",
                    "test_bm3d_filter", "test_dftt_filter", "test_thread_pool",
                    "test_suppression_engine", "test_release_shaper",
                    "test_masking_veto", "test_transient_detector",
                    "test_spectral_circular_buffer", "test_martin",
                    "test_brandt", "test_spp_mmse", "test_tonal_detector",
                    "test_tonal_reducer", "test_hpss_filter",
                    "test_denoiser_post_process", "test_specbleach_version",
                    "test_specbleach_stereo", "test_specbleach_cpp_smoke",
                    "test_audio_files", "test_audio_regression",
                    "test_integration_dftt_quality", "test_quality_metrics",
                    "test_spectral_smoother", "test_spectral_utils",
                    "test_frame_rate_norm", "test_stft_roundtrip",
                ):
                    self._sign_ohos_elf(os.path.join(self.build_folder, test_name))
            self.run("ctest --output-on-failure -j 1", cwd=self.build_folder,
                     env=["conanbuild", "conanrun"])
        elif not self.options.shared:
            self.output.warning("Cannot run the upstream CTest suite")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["specbleach"]
        self.cpp_info.set_property("cmake_file_name", "libspecbleach")
        self.cpp_info.set_property("cmake_target_name", "libspecbleach::libspecbleach")
        self.cpp_info.set_property("pkg_config_name", "specbleach")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]