#!/usr/bin/env python3
"""Conan recipe for ptyprocess 0.7.0.

ptyprocess is a pure-Python library.  The recipe builds the upstream wheel,
installs its package files under lib/pythonX.Y/site-packages, and exposes that
location to consumers through PYTHONPATH.
"""
import glob
import os
import shutil
import sys
import zipfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PtyprocessConan(ConanFile):
    name = "ptyprocess"
    version = "0.7.0"
    description = "Run a subprocess in a pseudo terminal"
    license = "ISC"
    homepage = "https://github.com/pexpect/ptyprocess"
    url = "https://github.com/pexpect/ptyprocess"
    topics = ("python", "pty", "terminal", "posix")
    package_type = "python-require"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ptyprocess requires a POSIX Linux or OHOS host")

    def source(self):
        get(self, strip_root=True, **self.conan_data["sources"])
        apply_conandata_patches(self)

    def build(self):
        ret = self.run(
            "python3 -m unittest discover -s tests -p 'test_*.py' -v 2>&1",
            cwd=self.source_folder,
        )
        if ret != 0:
            raise ConanException(f"upstream test suite failed with exit code {ret}")

        wheel_dir = os.path.join(self.build_folder, "dist")
        os.makedirs(wheel_dir, exist_ok=True)
        ret = self.run(
            f"python3 -m pip wheel --no-deps -w {wheel_dir} . 2>&1",
            cwd=self.source_folder,
        )
        if ret != 0:
            raise ConanException(f"pip wheel failed with exit code {ret}")
        wheels = glob.glob(os.path.join(wheel_dir, "ptyprocess-*.whl"))
        if len(wheels) != 1:
            raise ConanException(f"expected one ptyprocess wheel, found {wheels}")
        self._wheel = wheels[0]

    def package(self):
        wheel_dir = os.path.join(self.build_folder, "dist")
        wheels = glob.glob(os.path.join(wheel_dir, "ptyprocess-*.whl"))
        if len(wheels) != 1:
            raise ConanException(f"expected one ptyprocess wheel, found {wheels}")
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(
            self.package_folder, "lib", pyver, "site-packages"
        )
        os.makedirs(site_packages, exist_ok=True)
        with zipfile.ZipFile(wheels[0]) as archive:
            root = os.path.realpath(site_packages)
            for member in archive.namelist():
                if member.endswith("/"):
                    continue
                if os.path.isabs(member) or ".." in member.split("/"):
                    raise ConanException(f"unsafe wheel member: {member}")
                target = os.path.realpath(os.path.join(site_packages, member))
                if os.path.commonpath((root, target)) != root:
                    raise ConanException(f"wheel member escapes site-packages: {member}")
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with archive.open(member) as source, open(target, "wb") as dest:
                    shutil.copyfileobj(source, dest)

        package = os.path.join(site_packages, "ptyprocess")
        if not os.path.isfile(os.path.join(package, "__init__.py")):
            raise ConanException("wheel does not contain ptyprocess/__init__.py")

    def package_info(self):
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(self.package_folder, "lib", pyver, "site-packages")
        self.buildenv_info.define_path("PYTHONPATH", site_packages)
        self.runenv_info.define_path("PYTHONPATH", site_packages)
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
