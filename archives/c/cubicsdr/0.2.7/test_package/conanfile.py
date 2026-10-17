#!/usr/bin/env python3
"""Conan test package for cubicsdr 0.2.7 core library.

Consumer-side verification of the delivered DSP core on HarmonyOS PC:

  1. Modem factory registry — all 23 demodulation modes instantiate
     through the public Modem::makeModem() API.
  2. FM demodulation loop — synthesize an FM-modulated IQ carrier with
     liquid-dsp (freqmod), demodulate with CubicSDR's ModemFM through
     the public demodulate() API, assert the demodulated audio carries
     the injected tone (Goertzel amplitude check).
  3. AM demodulation loop — amplitude-modulated IQ signal → ModemAM →
     envelope follows the injected tone.
  4. Digital modem instantiation + demodulation smoke — BPSK mode
     exercises the ModemDigital path (symbol synchronizer, recovery
     loop objects) without asserting payload bytes (the GUI-layer
     bit sink lives in the out-of-scope DigitalConsole).
  5. SoapySDR no-hardware enumeration characterisation — the SDR
     hardware abstraction layer's documented behaviour on a machine
     without SDR hardware: Device::enumerate() returns an empty
     result, no crash.  This is the truthful form of "SDR hardware
     interaction layer" on OHOS PC (no RTL-SDR/USRP/BladeRF attached).
"""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class CubicSDRTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # cubicsdr-core public headers include liquid/liquid.h — the
        # consumer needs the DSP library headers on its include path.
        self.requires("liquid-dsp/1.8.2")
        # SoapySDR for the no-hardware enumeration characterisation
        # (the delivered core library itself does not link SoapySDR —
        # see conanfile.py scope notes).
        self.requires("soapysdr/0.8.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info(
                "Cross-building: defer execution to a HarmonyOS PC device"
            )
            return
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries —
        # wrap with bash.  LD_LIBRARY_PATH must put /system/lib64 in
        # front: the system libc++.so provides the __n1-namespace
        # symbols (std::__n1::...) that libSoapySDR.so relocates
        # against; the SDK sysroot libc++.so is a linker script and
        # would shadow them (established platform practice, see the
        # ohos-aarch64 conan profile notes).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        binary = os.path.join(self.cpp.build.bindir, "test_cubicsdr_core")
        self.run(
            f'{bash} -c "LD_LIBRARY_PATH=/system/lib64 '
            f'{binary}"',
            env="conanrun",
        )
