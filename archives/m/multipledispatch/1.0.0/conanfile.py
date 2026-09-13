#!/usr/bin/env python3
"""Conan recipe for multipledispatch 1.0.0.

The package is pure Python and has no runtime dependencies or native
extensions. The PyPI sdist is used because it is the canonical packaged
source and has a stable SHA256 digest.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


SOURCE_URL = (
    "https://files.pythonhosted.org/packages/fe/3e/"
    "a62c3b824c7dec33c4a1578bcc842e6c30300051033a4e5975ed86cc2536/"
    "multipledispatch-1.0.0.tar.gz"
)
SOURCE_SHA256 = (
    "5C839915465C68206C3E9C473357908216C28383B425361E5D144594BF85A7E0"
)


class MultipledispatchConan(ConanFile):
    name = "multipledispatch"
    version = "1.0.0"
    description = (
        "Multiple dispatch for Python; pure Python with no runtime dependencies"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/mrocklin/multipledispatch"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = (
        "upstream_tests/conftest.py",
        "upstream_tests/run_upstream_tests.py",
        "upstream_tests/multipledispatch/tests/*.py",
    )

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "multipledispatch/1.0.0 is prepared for Linux/OHOS"
            )

    def requirements(self):
        # Upstream setup.py declares no install_requires entries.
        pass

    def source(self):
        get(self, url=SOURCE_URL, sha256=SOURCE_SHA256, strip_root=True)

    def build(self):
        package_dir = os.path.join(self.source_folder, "multipledispatch")
        if not os.path.isdir(package_dir):
            raise ConanException(
                "multipledispatch package directory missing from source"
            )

        staging = os.path.join(self.build_folder, "python-stage")
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            package_dir,
            os.path.join(staging, "multipledispatch"),
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        egg_info = os.path.join(
            self.source_folder, "multipledispatch.egg-info"
        )
        if os.path.isdir(egg_info):
            shutil.copytree(egg_info, os.path.join(staging, "multipledispatch.egg-info"))

        smoke = (
            "from multipledispatch import dispatch\n"
            "@dispatch(int, int)\n"
            "def add(a, b): return a + b\n"
            "@dispatch(str, str)\n"
            "def add(a, b): return a + ':' + b\n"
            "assert add(2, 3) == 5\n"
            "assert add('a', 'b') == 'a:b'\n"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = staging
        python = sys.executable
        result = subprocess.run(
            [python, "-c", smoke],
            cwd=self.source_folder,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ConanException(
                "multipledispatch API smoke test failed: "
                + (result.stderr or result.stdout).strip()
            )

        upstream_root = os.path.join(self.source_folder, "upstream_tests")
        upstream_tests = os.path.join(upstream_root, "multipledispatch", "tests")
        runner = os.path.join(upstream_root, "run_upstream_tests.py")
        if not os.path.isdir(upstream_tests) or not os.path.isfile(runner):
            raise ConanException("upstream pytest suite is missing")

        test_env = dict(env)
        test_pythonpath = os.pathsep.join(
            value
            for value in (staging, upstream_tests, os.environ.get("PYTHONPATH", ""))
            if value
        )
        test_env["PYTHONPATH"] = test_pythonpath
        upstream = subprocess.run(
            [python, runner],
            cwd=self.source_folder,
            env=test_env,
            capture_output=True,
            text=True,
        )
        print("[multipledispatch upstream tests]")
        print((upstream.stdout or "")[-6000:])
        if upstream.stderr:
            print((upstream.stderr or "")[-3000:])
        if upstream.returncode != 0:
            raise ConanException(
                "multipledispatch upstream pytest suite failed with exit code "
                + str(upstream.returncode)
            )

    def package(self):
        staging = os.path.join(self.build_folder, "python-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"Python staging directory missing: {staging}")

        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        os.makedirs(site, exist_ok=True)
        copy(self, "*", src=staging, dst=site)

        if not os.path.isdir(os.path.join(site, "multipledispatch")):
            raise ConanException(
                "multipledispatch package missing from packaged site-packages"
            )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PYTHONPATH", site)
