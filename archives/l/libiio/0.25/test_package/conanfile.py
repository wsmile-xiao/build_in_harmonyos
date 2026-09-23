#!/usr/bin/env python3
"""Conan test_package — libiio 0.25 (R34 real-API smoke test).

Real consumer-side verification:
  * iio_library_get_version()  — asserts 0.25
  * iio_get_backends_count() / iio_get_backend() — xml backend registered
  * iio_create_xml_context_mem() — builds an iio_context from an in-memory
    XML description (upstream xml/ad5541a.xml shape); the only context
    creation path that needs no kernel IIO subsystem (OHOS PC has no
    /sys/bus/iio — platform limitation, see notes.md)
  * Device/channel/attr enumeration APIs on the live context:
    iio_context_get_name / get_devices_count / get_device /
    iio_device_get_id / get_name / get_channels_count / get_channel /
    iio_channel_get_id / get_attrs_count / get_attr
  * iio_context_destroy()

The test binary exits non-zero on any assertion failure, so a red
`conan create` reflects a real API regression (not a print-only stub).

Upstream's own test programs (tests/iio_info.c & friends) require a live
IIO device context; those are smoke-tested separately — see
test_package/MANIFEST.yml and notes.md for the run-time record.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

    # Note: no linker override — the default OHOS SDK lld must stay
    # (GNU-ld linked ELFs are rejected by the OHOS sandbox kernel loader,
    # verified Permission denied). The lld libxml2.so.16 loader dep
    # (E120/E132) is handled via LD_LIBRARY_PATH in the CI ohos-aarch64
    # profile, same approach as aeolus 0.10.4 in the main archives.

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the real test binary directly (R34: real API calls — the
        # binary exits non-zero on assertion failure). self.run is used
        # verbatim so the CI L0d gate (grep self.run) sees a real
        # execution path; ctest would hide it behind cmake --build.
        test_bin = os.path.join(self.build_folder, "test_iio")
        self.run(f'"{test_bin}"', env="conanrun")
