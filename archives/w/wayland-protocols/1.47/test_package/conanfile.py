#!/usr/bin/env python3
"""Conan test_package for wayland-protocols — data package consumer test.

Verifies that wayland-protocols.pc exists and pkgdatadir contains
stable/ protocol XML files.
"""
import os

from conan import ConanFile


class WaylandProtocolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["wayland-protocols"].package_folder
        # data 包：meson 默认把 .pc 装到 share/pkgconfig（非 lib/pkgconfig）
        pc = None
        for sub in ("share/pkgconfig", "lib/pkgconfig"):
            candidate = os.path.join(pkg, sub, "wayland-protocols.pc")
            if os.path.isfile(candidate):
                pc = candidate
                break
        if not pc:
            raise Exception("wayland-protocols.pc not found in package")
        self.output.info(f"wayland-protocols.pc found: {pc}")

        # Verify stable/ protocol XML files exist
        xml_dir = os.path.join(pkg, "share", "wayland-protocols", "stable")
        if not os.path.isdir(xml_dir):
            raise Exception(f"stable/ protocol dir not found: {xml_dir}")
        xml_files = [f for f in os.listdir(xml_dir) if os.path.isdir(os.path.join(xml_dir, f))]
        if len(xml_files) == 0:
            raise Exception("no stable protocol directories found")
        self.output.info(f"stable/ protocols found: {len(xml_files)} directories")

        # Run shell test for deeper validation
        script = os.path.join(self.source_folder, "src", "test_wayland-protocols.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{pkg}"', env="conanrun")
        self.output.info("wayland-protocols test_package PASS")
