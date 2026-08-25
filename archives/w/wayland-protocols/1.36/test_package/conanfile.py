#!/usr/bin/env python3
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["wayland-protocols"].package_folder
        # data 包：meson 默认把 .pc 装到 share/pkgconfig（非 lib/pkgconfig）
        for sub in ("share/pkgconfig", "lib/pkgconfig"):
            pc = os.path.join(pkg, sub, "wayland-protocols.pc")
            if os.path.isfile(pc):
                break
        found = os.path.isfile(pc)
        self.output.info(f"wayland-protocols.pc found: {found} ({pc})")
        if not found:
            raise Exception("wayland-protocols package missing")
        script = os.path.join(self.source_folder, "src", "test_wayland-protocols.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{pkg}"', env="conanrun")
        self.output.info("wayland-protocols test_package PASS")
