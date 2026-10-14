#!/usr/bin/env python3
"""Conan consumer verification for the RtAudio OHAudio backend."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RtaudioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if self.settings.os == "OHOS":
            serial = self.conf.get("user.rtaudio:hdc_serial", default=None)
            hdc = self.conf.get("user.rtaudio:hdc_executable", default=None)
            hvigor = self.conf.get("user.rtaudio:hvigor_js", default=None)
            node = self.conf.get("user.rtaudio:node_executable", default=None)
            sdk = self.conf.get("user.rtaudio:ohos_base_sdk", default=None)
            harmonyos_sdk = self.conf.get("user.rtaudio:harmonyos_sdk", default=None)
            signing_config = self.conf.get("user.rtaudio:harmonyos_signing_config", default=None)
            signed_hap = self.conf.get("user.rtaudio:harmonyos_signed_hap", default=None)
            if signing_config and signed_hap:
                raise RuntimeError(
                    "set only one of user.rtaudio:harmonyos_signing_config or user.rtaudio:harmonyos_signed_hap")
            device_settings = (serial, hdc, hvigor, node, sdk)
            optional_hap_settings = (harmonyos_sdk, signing_config, signed_hap)
            if not any(device_settings + optional_hap_settings):
                self.output.info(
                    "Skipping OHOS device HAP execution: no user.rtaudio device, SDK, or signing settings "
                    "are configured. The Conan consumer target was already built and linked; run the signed-HAP "
                    "device suite with the local profile to verify live OHAudio callbacks.")
                return
            if not all((serial, hdc, hvigor, node, sdk)):
                raise RuntimeError(
                    "OHOS Conan device tests have incomplete configuration; set user.rtaudio HDC, DevEco Hvigor, "
                    "Node.js and SDK settings together")
            runner = os.path.join(self.recipe_folder, "run_ohos_device_test.py")
            app_template = os.path.join(self.recipe_folder, "ohos_device_app")
            workspace = os.path.abspath(os.path.join(self.build_folder, "ohos_device_app"))
            build_root = os.path.abspath(self.build_folder)
            generators = os.path.abspath(os.path.join(self.build_folder, "generators"))
            command = ('python "{runner}" --app-template "{app_template}" --workspace "{workspace}" '
                       '--build-root "{build_root}" '
                       '--generators-dir "{generators}" --serial "{serial}" --hdc "{hdc}" '
                       '--hvigor "{hvigor}" --node "{node}" --sdk-root "{sdk}"').format(
                           runner=runner, app_template=app_template, workspace=workspace,
                           build_root=build_root,
                           generators=generators, serial=serial, hdc=hdc,
                           hvigor=hvigor, node=node, sdk=sdk)
            if signing_config:
                command += ' --signing-config "{}"'.format(signing_config)
            if signed_hap:
                command += ' --signed-hap "{}"'.format(signed_hap)
            if harmonyos_sdk:
                command += ' --harmonyos-sdk-root "{}"'.format(harmonyos_sdk)
            self.run(command)
        else:
            cmake = CMake(self)
            cmake.test()
