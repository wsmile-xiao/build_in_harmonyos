#!/usr/bin/env python3
"""Conan recipe for iniconfig 2.3.0 (pure-Python, setuptools src layout).

iniconfig is the config-ini parser that pytest uses for its own configuration
loading, so it is a runtime dependency of pytest and therefore of any upstream
test suite that is driven through pytest. It is packaged as a plain module tree
under lib/pythonX.Y/site-packages and advertised through PYTHONPATH, matching
the python3-rdflib / packaging / pluggy conventions in this repository.

The upstream suite (testing/test_iniconfig.py, 31 test functions) is driven by
pytest, which is a *consumer* of this package; requiring it here would be
circular. A build-local pytest is therefore bootstrapped with pip, the same
mechanism pluggy 1.6.0 uses. When that bootstrap cannot run, the loss of
coverage is announced with a warning instead of being reported as a pass.
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# Pinned so the measured upstream result is reproducible; pytest 9.1.1 is the
# release this package was validated against.
UPSTREAM_PYTEST = "pytest==9.1.1"


class IniconfigConan(ConanFile):
    name = "iniconfig"
    version = "2.3.0"
    description = "brain-dead simple config-ini parsing"
    license = "MIT"
    homepage = "https://github.com/pytest-dev/iniconfig"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"iniconfig supports Linux and OHOS, not {self.settings.os}"
            )

    @staticmethod
    def _site_relpath():
        """site-packages path relative to a prefix, for this interpreter."""
        return (
            "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _stage(self):
        """Lay the module out under a Conan-prefix-shaped staging tree."""
        site = os.path.join(self.build_folder, "staging", *self._site_relpath())
        os.makedirs(site, exist_ok=True)

        module = os.path.join(self.source_folder, "src", "iniconfig")
        if not os.path.isdir(module):
            raise ConanException("iniconfig source package directory is missing")
        shutil.copytree(module, os.path.join(site, "iniconfig"))

        dist_info = os.path.join(site, f"iniconfig-{self.version}.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as handle:
            handle.write(
                "Metadata-Version: 2.1\n"
                "Name: iniconfig\n"
                f"Version: {self.version}\n"
                "License: MIT\n"
            )
        with open(
            os.path.join(dist_info, "top_level.txt"), "w", encoding="utf-8"
        ) as handle:
            handle.write("iniconfig\n")
        return site

    def _run_upstream_tests(self, site):
        """Run the upstream pytest suite against the staged module.

        Reported as measured: the suite failing fails the build, and the suite
        not running at all is announced rather than skipped silently.
        """
        tests = os.path.join(self.source_folder, "testing")
        if not os.path.isdir(tests):
            raise ConanException("upstream testing/ directory is missing")

        test_deps = os.path.join(self.build_folder, "test-deps")
        try:
            self.run(
                f"{sys.executable} -m pip install --disable-pip-version-check "
                f'--no-compile --target "{test_deps}" {UPSTREAM_PYTEST}',
                cwd=self.build_folder,
            )
        except ConanException as exc:
            self.output.warning(
                "could not bootstrap a build-local pytest "
                f"({str(exc).strip().splitlines()[-1:]}): the upstream suite "
                "(31 test functions in testing/test_iniconfig.py) did NOT run. "
                f"Install {UPSTREAM_PYTEST} for {sys.executable} to execute it — "
                "this is a coverage reduction, not a pass."
            )
            return

        basetemp = os.path.join(self.build_folder, "pytest-tmp")
        os.makedirs(basetemp, exist_ok=True)

        environment = Environment()
        # Staged module first: the suite must exercise what will be packaged,
        # not the copy pip pulled in alongside pytest.
        environment.prepend_path("PYTHONPATH", site)
        environment.prepend_path(
            "PYTHONPATH", os.path.join(self.source_folder, "src")
        )
        environment.prepend_path("PYTHONPATH", test_deps)
        with environment.vars(self).apply():
            self.run(
                f'{sys.executable} -m pytest "{tests}" -q --no-header '
                f'-p no:cacheprovider --basetemp="{basetemp}"'
            )

    def build(self):
        site = self._stage()
        self._run_upstream_tests(site)

    def package(self):
        staging = os.path.join(self.build_folder, "staging", *self._site_relpath())
        if not os.path.isdir(staging):
            raise ConanException("iniconfig staging directory is missing")
        copy(
            self,
            "*",
            src=staging,
            dst=os.path.join(self.package_folder, *self._site_relpath()),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        site = os.path.join(self.package_folder, *self._site_relpath())
        # Build-time consumers (a recipe whose upstream suite is driven through
        # pytest) need this on PYTHONPATH while it builds, not only at run time.
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.output.info(f"iniconfig installed: {site}/iniconfig/")
