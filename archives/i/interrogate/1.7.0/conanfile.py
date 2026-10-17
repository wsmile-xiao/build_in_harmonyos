#!/usr/bin/env python3
"""Conan recipe for interrogate 1.7.0 (pure-Python CLI tool, src layout).

interrogate measures docstring coverage of a Python codebase and reports it
from the command line. It is packaged as an application: the module tree
under lib/pythonX.Y/site-packages plus a bin/interrogate console entry point,
both exported through PYTHONPATH/PATH -- the same shape the pytest/9.1.1
recipe uses for command-carrying python packages.

Runtime dependencies come from this repo's registry (attrs/click/colorama/
tabulate). The fourth upstream dependency, `py` (the deprecated pylib shim
that OutputFormatter uses for its TerminalWriter), is NOT in the registry
(verified: conan list 'py/*' -> 0 recipes) and has no task card, so py 1.11.0
is vendored into the package's site-packages -- a self-contained tree equal
to what a wheel install of both would lay down. See notes.md for the
decision trail.

The upstream suite (tests/, pytest + pytest-mock) is driven by build-local
wheels bootstrapped with pip, and runs against the staged module tree so what
is tested is what will be packaged.
"""

import os
import shutil
import sys
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, download, get
from conan.tools.layout import basic_layout

# Pinned so the measured upstream result is reproducible; pytest 9.1.1 is the
# release this repository's own pytest package carries, and pytest-mock
# provides the `mocker` fixture the suite's unit tests are written against.
UPSTREAM_PYTEST = "pytest==9.1.1"
UPSTREAM_PYTEST_MOCK = "pytest-mock==3.16.0"

# interrogate 1.7.0's expected-output fixtures were generated against
# tabulate 0.9.x. tabulate 0.10.0 widened every cell by one space on each
# side, so the five verbosity-2 fixture comparisons drift by exactly that
# amount (measured: byte-identical rendering with 0.9.0, +2 cols with
# 0.10.0) while the tool itself stays fully functional. The suite therefore
# pins 0.9.0 by URL+sha256; the registry dependency stays tabulate/0.10.0
# and the consumer test_package drives the real CLI against it.
_SUITE_TABULATE_WHEEL = (
    "https://files.pythonhosted.org/packages/40/44/4a5f08c96eb108af5cb50b41f"
    "76142f0afa346dfa99d5296fe7202a11854/tabulate-0.9.0-py3-none-any.whl",
    "024ca478df22e9340661486f85298cff5f6dcdba14f3813e8830015b9ed1948f",
)


class InterrogateConan(ConanFile):
    name = "interrogate"
    version = "1.7.0"
    description = "Interrogate a codebase for docstring coverage"
    license = "MIT"
    homepage = "https://github.com/econchick/interrogate"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"interrogate supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Exactly the runtime set declared by interrogate 1.7.0's
        # Requires-Dist, minus `py` (vendored -- see module docstring) and
        # minus tomli (python_version < "3.11" only; this package targets
        # the 3.12 interpreters the recipes here build for, which carry
        # tomllib in the stdlib).
        #
        # run=True so an application consumer propagates the dependencies'
        # environment downstream (measured in the pytest/9.1.1 recipe: plain
        # requires land under "Skipped binaries" and their runenv never
        # reaches the consumer).
        self.requires("attrs/26.1.0", run=True)
        self.requires("click/8.4.2", run=True)
        self.requires("colorama/0.4.6", run=True)
        self.requires("tabulate/0.10.0", run=True)

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

    def _vendor_py(self, site):
        """Lay the vendored py 1.11.0 module tree into the staging site.

        `py` is a hard runtime dependency (interrogate/utils.py imports
        `from py import io` at module top level) that this repo's registry
        does not carry. The vendored tree is the sdist's own py/ package
        (which bundles its _vendored_packages the same way the wheel does),
        plus dist-info so tooling can discover it.
        """
        entry = self.conan_data["vendored_py"]
        tarball = os.path.join(self.build_folder, "py-1.11.0.tar.gz")
        download(self, entry["url"], filename=tarball, sha256=entry["sha256"])

        extract_root = os.path.join(self.build_folder, "vendored-py-src")
        if os.path.isdir(extract_root):
            shutil.rmtree(extract_root)
        os.makedirs(extract_root, exist_ok=True)
        with tarfile.open(tarball) as tar:
            tar.extractall(extract_root, filter="data")

        py_src = os.path.join(extract_root, "py-1.11.0", "py")
        if not os.path.isdir(py_src):
            raise ConanException("vendored py-1.11.0 package directory missing")
        shutil.copytree(py_src, os.path.join(site, "py"))

        dist_info = os.path.join(site, "py-1.11.0.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as handle:
            handle.write(
                "Metadata-Version: 2.1\n"
                "Name: py\n"
                "Version: 1.11.0\n"
                "License: MIT\n"
            )
        with open(
            os.path.join(dist_info, "top_level.txt"), "w", encoding="utf-8"
        ) as handle:
            handle.write("py\n")
        self.output.info("vendored py 1.11.0 into the staging site")

    def _stage(self):
        """Lay the module and the entry point out under a staging prefix."""
        site = os.path.join(self.build_folder, "staging", *self._site_relpath())
        bin_dir = os.path.join(self.build_folder, "staging", "bin")
        os.makedirs(site, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        module = os.path.join(self.source_folder, "src", "interrogate")
        if not os.path.isdir(module):
            raise ConanException("interrogate source package directory is missing")
        # The whole package tree goes in, including the badge/ template
        # directory badge_gen serves through importlib.resources.
        shutil.copytree(module, os.path.join(site, "interrogate"))

        self._vendor_py(site)

        dist_info = os.path.join(site, f"interrogate-{self.version}.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as handle:
            handle.write(
                "Metadata-Version: 2.1\n"
                "Name: interrogate\n"
                f"Version: {self.version}\n"
                "License: MIT\n"
            )
        with open(
            os.path.join(dist_info, "top_level.txt"), "w", encoding="utf-8"
        ) as handle:
            handle.write("interrogate\n")
        # Mirror upstream's console_scripts (setup.py:
        # "interrogate = interrogate.cli:main") so entry-point-aware tooling
        # sees the same command the bin/ wrapper provides.
        with open(
            os.path.join(dist_info, "entry_points.txt"), "w", encoding="utf-8"
        ) as handle:
            handle.write(
                "[console_scripts]\n"
                "interrogate = interrogate.cli:main\n"
            )

        path = os.path.join(bin_dir, "interrogate")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!/usr/bin/env python3\n"
                '"""Console entry point for interrogate."""\n'
                "import sys\n"
                "from interrogate.cli import main\n"
                "\n"
                'if __name__ == "__main__":\n'
                "    sys.exit(main())\n"
            )
        os.chmod(path, 0o755)
        return site, bin_dir

    @staticmethod
    def _find_site_packages(package_folder):
        """Locate a dependency's site-packages directory.

        click/8.4.2 installs flat (the package folder itself is the
        site-packages), while attrs/colorama/tabulate install to
        lib/pythonX.Y/site-packages. Discovering instead of assuming keeps
        this correct for both layouts.
        """
        if os.path.isdir(os.path.join(package_folder, "click")):
            return package_folder
        for dirpath, dirnames, _files in os.walk(package_folder):
            if "site-packages" in dirnames:
                return os.path.join(dirpath, "site-packages")
        return None

    def _suite_tmpdir(self, fallback, inherited):
        """Pick a usable temp root for the upstream suite.

        /tmp is read-only on this platform and directories created under
        the user home (HMDFS) do not come back owned by the caller, which
        pytest's tmp_path fixture rejects. An inherited TMPDIR is honoured
        only when writable and outside the home; the device's own cache
        path is next; the build folder is the last resort.
        """
        home = os.path.expanduser("~")
        for path in (inherited, "/data/storage/el2/base/cache", fallback):
            if not path:
                continue
            absolute = os.path.abspath(path)
            if home and absolute.startswith(home + os.sep):
                continue
            if os.path.isdir(absolute) and os.access(absolute, os.W_OK):
                return absolute
        return fallback

    def _run_upstream_tests(self, site):
        """Run the upstream pytest suite against the staged tree.

        Reported as measured: the suite failing fails the build, and the
        suite not running at all is announced rather than skipped silently.
        """
        tests = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests):
            raise ConanException("interrogate upstream tests/ directory is missing")

        test_deps = os.path.join(self.build_folder, "test-deps")
        try:
            self.run(
                f"{sys.executable} -m pip install --disable-pip-version-check "
                f"--no-compile --no-input --target \"{test_deps}\" "
                f"{UPSTREAM_PYTEST} {UPSTREAM_PYTEST_MOCK}",
                cwd=self.build_folder,
            )
            wheel_url, wheel_sha = _SUITE_TABULATE_WHEEL
            wheel_file = os.path.join(
                self.build_folder, "tabulate-0.9.0-py3-none-any.whl"
            )
            download(self, wheel_url, filename=wheel_file, sha256=wheel_sha)
            self.run(
                f"{sys.executable} -m pip install --disable-pip-version-check "
                f"--no-compile --no-input --no-deps "
                f'--target "{test_deps}" "{wheel_file}"',
                cwd=self.build_folder,
            )
        except ConanException as exc:
            self.output.warning(
                "could not bootstrap the build-local test dependencies "
                f"({str(exc).strip().splitlines()[-1:]}): the upstream suite "
                "(tests/functional + tests/unit) did NOT run. Install "
                f"{UPSTREAM_PYTEST} and {UPSTREAM_PYTEST_MOCK} for "
                f"{sys.executable} to execute it — this is a coverage "
                "reduction, not a pass."
            )
            return

        # The conan-provided runtime dependencies join the suite's import
        # path from their own package folders (staged tree first, then the
        # pinned suite wheels, then the registry packages), so the suite
        # exercises exactly the dependency set the package declares --
        # except tabulate, where the pinned 0.9.0 wheel shadows the registry
        # 0.10.0 for the fixture-comparison reasons documented above.
        dep_sites = []
        for dep in ("attrs", "click", "colorama"):
            dependency = self.dependencies.get(dep)
            if dependency is None or not dependency.package_folder:
                raise ConanException(f"declared dependency not available: {dep}")
            dep_site = self._find_site_packages(dependency.package_folder)
            if dep_site is None:
                raise ConanException(
                    f"{dep} package folder has no importable layout: "
                    f"{dependency.package_folder}"
                )
            dep_sites.append(dep_site)

        basetemp = os.path.join(
            self._suite_tmpdir(self.build_folder, os.environ.get("TMPDIR")),
            "interrogate-pytest",
        )
        os.makedirs(basetemp, exist_ok=True)

        environment = Environment()
        # Staged tree first: the suite must exercise what will be packaged.
        # Conan's Environment.prepend_path composes with the LAST prepended
        # value in FRONT (measured: prepending site before test_deps made
        # `import py` resolve to pytest's module-level py.py shim inside
        # test_deps instead of the vendored py/ package in the staged tree,
        # killing collection with "cannot import name 'io' from 'py'"). The
        # prepend order is therefore reversed on purpose: dependencies
        # first, test deps next, staged tree last.
        for dep_site in dep_sites:
            environment.prepend_path("PYTHONPATH", dep_site)
        environment.prepend_path("PYTHONPATH", test_deps)
        environment.prepend_path("PYTHONPATH", site)
        with environment.vars(self).apply():
            self.run(
                f'{sys.executable} -m pytest "{tests}" -q --no-header '
                f'-p no:cacheprovider --basetemp="{basetemp}"',
                cwd=self.source_folder,
            )

    def build(self):
        site, _bin = self._stage()
        self._run_upstream_tests(site)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        if not os.path.isdir(staging):
            raise ConanException("interrogate staging directory is missing")
        copy(self, "*", src=staging, dst=self.package_folder)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        site = os.path.join(self.package_folder, *self._site_relpath())
        bin_dir = os.path.join(self.package_folder, "bin")

        # Re-export the runtime dependencies' import paths. At least attrs
        # and colorama do not publish their own site-packages through Conan
        # 2 env objects (their package_info only clears cpp_info lists), so
        # without this block a consumer's `import interrogate` dies with
        # "No module named 'attr'" even though the dependency is installed
        # -- the same failure mode the pytest/9.1.1 recipe measured and fixed
        # for packaging/26.3.
        dep_sites = []
        for name in ("attrs", "click", "colorama", "tabulate"):
            try:
                folder = self.dependencies[name].package_folder
            except Exception:  # pragma: no cover - defensive, keyed by name
                folder = None
            if not folder:
                self.output.warning(
                    f"runtime dependency '{name}' has no package folder; its "
                    f"import path cannot be published to consumers"
                )
                continue
            dep_site = self._find_site_packages(folder)
            if not dep_site:
                self.output.warning(
                    f"no importable layout under '{name}': {folder}"
                )
                continue
            dep_sites.append(dep_site)

        # Everything is PREPENDED, never appended: this host's interpreter
        # carries its own PYTHONPATH (a pip-global tree holding colorama and
        # friends), and append_path would leave those host copies shadowing
        # the packaged dependencies -- measured: `import colorama` resolved
        # from the host tree and failed the consumer provenance check. Conan
        # composes prepends stack-like (the last call lands frontmost), so
        # the dependencies are prepended first and this package's own site
        # last, giving <package site>:<deps...>:<inherited environment>.
        for env in (self.buildenv_info, self.runenv_info):
            for dep_site in reversed(dep_sites):
                env.prepend_path("PYTHONPATH", dep_site)
            env.prepend_path("PYTHONPATH", site)
            env.prepend_path("PATH", bin_dir)

        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.output.info(
            f"interrogate installed: {bin_dir}/interrogate; vendored py "
            f"1.11.0; published {len(dep_sites)} dependency import path(s)"
        )
