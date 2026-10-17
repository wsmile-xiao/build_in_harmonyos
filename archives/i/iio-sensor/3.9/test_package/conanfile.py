#!/usr/bin/env python3
"""Conan test package for the iio-sensor (iio-sensor-proxy) binaries.

CI worker is x86 but iio-sensor-proxy is cross-compiled for OHOS aarch64,
so the packaged binaries (iio-sensor-proxy daemon, monitor-sensor CLI)
cannot be executed on the build host (Exec format error).  Verification:

- build(): compiles test.c with IIO_SENSOR_PROXY_PATH / MONITOR_SENSOR_PATH
  baked in (Conan packaged binary absolute paths) — compile-time
  verification target (R34, no host PATH lookup).
- test(): runs a host-side bash script (test_iio_sensor.sh) via self.run,
  verifying presence + ELF magic of the packaged binaries.  Satisfies L0d
  (self.run required) and R34 (real packaged-binary verification).
"""

import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IioSensorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        dep = self.dependencies["iio-sensor"]
        iio_sensor_proxy = os.path.join(dep.package_folder, "libexec", "iio-sensor-proxy")
        monitor_sensor = os.path.join(dep.package_folder, "bin", "monitor-sensor")
        cmake = CMake(self)
        cmake.configure(
            variables={
                "IIO_SENSOR_PROXY_PATH": iio_sensor_proxy,
                "MONITOR_SENSOR_PATH": monitor_sensor,
            }
        )
        cmake.build()

    def test(self):
        dep = self.dependencies["iio-sensor"]
        script = os.path.join(self.source_folder, "test_iio_sensor.sh")
        iio_sensor_proxy = os.path.join(dep.package_folder, "libexec", "iio-sensor-proxy")
        monitor_sensor = os.path.join(dep.package_folder, "bin", "monitor-sensor")
        bash = shutil.which("bash") or "/bin/sh"
        self.run(f"{bash} {script} {iio_sensor_proxy} {monitor_sensor}", env="conanrun")
