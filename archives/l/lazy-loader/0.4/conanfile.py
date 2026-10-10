#!/usr/bin/env python3
"""Conan recipe for lazy-loader 0.4 (pure-Python, setuptools src layout).

lazy_loader implements lazy loading of subpackages and functions on demand
(scientific-python SPEC 1, PEP 562 module __getattr__). It is a runtime
dependency of scikit-image and a build-time helper for several
scientific-python projects, so it is packaged the same way as the other
python-require packages in this repository (packaging/26.3, iniconfig/2.3.0,
attrs/26.1.0): a plain module tree under lib/pythonX.Y/site-packages,
advertised through PYTHONPATH.

The upstream suite (lazy_loader/tests/test_lazy_loader.py) is driven by a
build-local pytest, bootstrapped with pip from the source tarball -- the same
mechanism iniconfig/2.3.0 uses. The suite runs against the staged module tree
so what is tested is what will be packaged.
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
# release this package was validated against (matches the repo's pytest pkg).
UPSTREAM_PYTEST = "pytest==9.1.1"


class LazyLoaderConan(ConanFile):
    name = "lazy-loader"
    version = "0.4"
    description = "Makes it easy to load subpackages and functions on demand"
    license = "BSD-3-Clause"
    homepage = "https://github.com/scientific-python/lazy_loader"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lazy-loader supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Runtime set declared by lazy_loader 0.4's Requires-Dist: packaging.
        # It is imported lazily inside _check_requirement() (the require=
        # kwarg of load()/attach_stub()), not at module import, but declaring
        # it keeps the PYTHONPATH chain complete for consumers instead of
        # relying on the host having it installed.
        # run=True so an application consumer propagates the dependency's
        # environment downstream (measured in the pytest/9.1.1 recipe: plain
        # requires are listed under "Skipped binaries" and their runenv never
        # reaches the consumer).
        self.requires("packaging/26.3", run=True)

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

        # The sdist ships the module at the top level (no src/ layout), and
        # the wheel records the same top_level.txt: lazy_loader.
        module = os.path.join(self.source_folder, "lazy_loader")
        if not os.path.isdir(module):
            raise ConanException("lazy_loader source package directory is missing")
        shutil.copytree(module, os.path.join(site, "lazy_loader"))

        dist_info = os.path.join(site, f"lazy_loader-{self.version}.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as handle:
            handle.write(
                "Metadata-Version: 2.1\n"
                "Name: lazy_loader\n"
                f"Version: {self.version}\n"
                "License: BSD-3-Clause\n"
            )
        with open(
            os.path.join(dist_info, "top_level.txt"), "w", encoding="utf-8"
        ) as handle:
            handle.write("lazy_loader\n")
        return site

    def _run_upstream_tests(self, site):
        """Run the upstream pytest suite against the staged module.

        Reported as measured: the suite failing fails the build, and the suite
        not running at all is announced rather than skipped silently.

        The suite lives inside the module tree itself (lazy_loader/tests/,
        11 test functions), so running it against the staged tree requires the
        staged copy of the tests, which is exactly what _stage() laid down.
        numpy-dependent cases call pytest.importorskip("numpy") and skip when
        it is absent; numpy is available in this repo's registry
        (numpy/2.5.2) and on the build hosts, so they run rather than skip
        here, but the skip path stays the suite's own decision either way.
        """
        tests = os.path.join(site, "lazy_loader", "tests")
        if not os.path.isdir(tests):
            raise ConanException("upstream lazy_loader/tests/ directory is missing")

        test_deps = os.path.join(self.build_folder, "test-deps")
        try:
            self.run(
                f"{sys.executable} -m pip install --disable-pip-version-check "
                f'--no-compile --no-input --target "{test_deps}" {UPSTREAM_PYTEST}',
                cwd=self.build_folder,
            )
        except ConanException as exc:
            self.output.warning(
                "could not bootstrap a build-local pytest "
                f"({str(exc).strip().splitlines()[-1:]}): the upstream suite "
                "(11 test functions in lazy_loader/tests/test_lazy_loader.py) "
                "did NOT run. Install "
                f"{UPSTREAM_PYTEST} for {sys.executable} to execute it — "
                "this is a coverage reduction, not a pass."
            )
            return

        # /tmp is read-only on this platform and the user home (HMDFS) hands
        # back directories whose owner pytest's tmp_path fixture rejects, so
        # a usable root is probed instead of assumed (same order as the
        # pytest/9.1.1 recipe's _suite_tmpdir).
        home = os.path.expanduser("~")
        basetemp = None
        for path in (
            os.environ.get("TMPDIR"),
            "/data/storage/el2/base/cache",
            self.build_folder,
        ):
            if not path:
                continue
            absolute = os.path.abspath(path)
            if home and absolute.startswith(home + os.sep):
                continue
            if os.path.isdir(absolute) and os.access(absolute, os.W_OK):
                basetemp = os.path.join(absolute, "lazy-loader-pytest")
                break
        if basetemp is None:
            basetemp = os.path.join(self.build_folder, "pytest-tmp")
        os.makedirs(basetemp, exist_ok=True)

        environment = Environment()
        # Staged module first: the suite must exercise what will be packaged,
        # not the copy pip pulled in alongside pytest or any host copy.
        environment.prepend_path("PYTHONPATH", site)
        environment.prepend_path("PYTHONPATH", test_deps)
        # The consumer's runtime dependency must resolve from its own package
        # folder too, so the require= kwarg cases behave as they will after
        # installation instead of being answered by a host copy.
        packaging = self.dependencies.get("packaging")
        if packaging is not None and packaging.package_folder:
            for dirpath, dirnames, _files in os.walk(packaging.package_folder):
                if "site-packages" in dirnames:
                    environment.prepend_path(
                        "PYTHONPATH", os.path.join(dirpath, "site-packages")
                    )
                    break
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
            raise ConanException("lazy-loader staging directory is missing")
        copy(
            self,
            "*",
            src=staging,
            dst=os.path.join(self.package_folder, *self._site_relpath()),
        )
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        site = os.path.join(self.package_folder, *self._site_relpath())
        # Build-time consumers need this on PYTHONPATH while it builds, not
        # only at run time (python-require convention in this repository).
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.output.info(f"lazy-loader installed: {site}/lazy_loader/")
