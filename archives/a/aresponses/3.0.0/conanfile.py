#!/usr/bin/env python3
"""Conan recipe — aresponses 3.0.0 (Pure Python package).

aresponses is an asyncio HTTP mocking library / pytest plugin.
Built with setuptools (pip install), not C/C++ build systems.
"""
import os
import sys
import zipfile

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class AresponsesConan(ConanFile):
    name = "aresponses"
    version = "3.0.0"
    description = "Asyncio response mocking. Similar to the responses library used for 'requests'"
    license = "MIT"
    homepage = "https://github.com/CircleUp/aresponses"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R32: If using settings.os, must use in ("Linux", "OHOS")
    # R37: OHOS profile requires all four settings
    settings = "os", "compiler", "build_type", "arch"
    package_type = "unknown"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure Python package — build wheel using setuptools
        # R33: Use sys.executable, not "python3" string
        apply_conandata_patches(self)
        self.run(f"{sys.executable} -m pip install setuptools --quiet 2>&1")
        self.run(f"{sys.executable} setup.py bdist_wheel")

    def package(self):
        # Unpack the wheel into the package directory
        build_dir = self.build_folder
        wheel_dir = os.path.join(build_dir, "dist")
        py_version = f"python{sys.version_info[0]}.{sys.version_info[1]}"
        pkg_dir = os.path.join(self.package_folder, "lib", py_version, "site-packages")
        os.makedirs(pkg_dir, exist_ok=True)
        if os.path.isdir(wheel_dir):
            for f in os.listdir(wheel_dir):
                if f.endswith(".whl"):
                    # Unpack the wheel (zip archive) so Python can import it
                    with zipfile.ZipFile(os.path.join(wheel_dir, f)) as zf:
                        zf.extractall(pkg_dir)
        # Install runtime deps so aresponses can be imported in CI
        deps_dir = os.path.join(self.package_folder, "deps")
        os.makedirs(deps_dir, exist_ok=True)
        self.run(
            f"{sys.executable} -m pip install aiohttp pytest pytest-asyncio "
            f"--target={deps_dir} --quiet 2>&1",
            cwd=build_dir,
        )

    def package_info(self):
        # Set PYTHONPATH so the package and its deps are importable at runtime
        py_version = f"python{sys.version_info[0]}.{sys.version_info[1]}"
        site_packages = os.path.join("lib", py_version, "site-packages")
        self.cpp_info.libdirs = [site_packages]
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "deps"))
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, site_packages))
