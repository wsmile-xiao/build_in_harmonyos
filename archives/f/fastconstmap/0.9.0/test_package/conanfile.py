#!/usr/bin/env python3
"""Consumer and upstream test runner for fastconstmap."""
import glob
import hashlib
import json
import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class FastconstmapTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    pytest_version = "8.3.5"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The tested package is a Python extension; make its matching Python
        # runtime an explicit consumer requirement rather than ambient PATH.
        self.requires("python/3.12.9")

    @staticmethod
    def _first(pattern, description):
        matches = sorted(glob.glob(pattern))
        if not matches:
            raise ConanException(f"{description} not found: {pattern}")
        return matches[0]

    @staticmethod
    def _writable_temp_root():
        candidates = [
            os.environ.get("TMPDIR", ""),
            os.environ.get("XDG_RUNTIME_DIR", ""),
            os.environ.get("XDG_CACHE_HOME", ""),
            os.environ.get("XDG_CONFIG_HOME", ""),
            os.path.join(os.path.expanduser("~"), "tmp"),
            tempfile.gettempdir(),
            os.getcwd(),
        ]
        for parent in candidates:
            if not parent:
                continue
            candidate = ""
            try:
                os.makedirs(parent, exist_ok=True)
                candidate = tempfile.mkdtemp(prefix="fastconstmap-pytest-", dir=parent)
                probe = os.path.join(candidate, ".write-probe")
                with open(probe, "w", encoding="ascii") as stream:
                    stream.write("probe")
                os.unlink(probe)
                return candidate
            except OSError:
                if candidate:
                    shutil.rmtree(candidate, ignore_errors=True)
                continue
        raise ConanException(
            "no writable temporary directory can be created by the test user"
        )

    @staticmethod
    def _python_executable(package_folder):
        candidates = [
            path
            for path in glob.glob(os.path.join(package_folder, "bin", "python3.*"))
            if not path.endswith("-config")
        ]
        if not candidates:
            raise ConanException("Conan Python interpreter not found")
        return sorted(candidates)[0]

    @staticmethod
    def _python_environment(python_package, python_lib, pythonpath=(), runtime_libs=()):
        environment = Environment()
        environment.define("PYTHONHOME", python_package)
        for path in (python_lib, *runtime_libs):
            if path:
                environment.prepend_path("LD_LIBRARY_PATH", path)
        for path in reversed(tuple(pythonpath)):
            environment.prepend_path("PYTHONPATH", path)
        return environment

    def _runtime_library_dirs(self):
        paths = []
        for dependency in self.dependencies.host.values():
            package_folder = getattr(dependency, "package_folder", "")
            if not package_folder:
                continue
            lib_dir = os.path.join(package_folder, "lib")
            if os.path.isdir(lib_dir) and lib_dir not in paths:
                paths.append(lib_dir)
        return paths

    def _download_test_wheels(self, wheel_dir, test_deps):
        curl = shutil.which("curl")
        if not curl:
            raise ConanException(
                "curl is required to fetch the pinned private pytest test tool"
            )
        packages = (
            ("pytest", self.pytest_version),
            ("iniconfig", "2.1.0"),
            ("packaging", "24.2"),
            ("pluggy", "1.5.0"),
            ("pygments", "2.19.1"),
        )
        metadata_dir = os.path.join(test_deps, "pypi-metadata")
        os.makedirs(metadata_dir, exist_ok=True)
        for name, version in packages:
            metadata = os.path.join(metadata_dir, f"{name}-{version}.json")
            self.run(
                " ".join(
                    [
                        shlex.quote(curl),
                        "-fsSL",
                        "--retry",
                        "3",
                        "--connect-timeout",
                        "15",
                        "--max-time",
                        "120",
                        f"https://pypi.org/pypi/{name}/{version}/json",
                        "-o",
                        shlex.quote(metadata),
                    ]
                ),
                env="conanrun",
            )
            with open(metadata, encoding="utf-8") as stream:
                release = json.load(stream)
            wheels = [
                item
                for item in release.get("urls", [])
                if item.get("packagetype") == "bdist_wheel"
                and item.get("filename", "").endswith("-py3-none-any.whl")
            ]
            if not wheels:
                raise ConanException(
                    f"no universal wheel found for {name}=={version}"
                )
            wheel = wheels[0]
            wheel_path = os.path.join(wheel_dir, wheel["filename"])
            self.run(
                " ".join(
                    [
                        shlex.quote(curl),
                        "-fsSL",
                        "--retry",
                        "3",
                        "--connect-timeout",
                        "15",
                        "--max-time",
                        "120",
                        wheel["url"],
                        "-o",
                        shlex.quote(wheel_path),
                    ]
                ),
                env="conanrun",
            )
            with open(wheel_path, "rb") as stream:
                digest = hashlib.sha256(stream.read()).hexdigest()
            if digest != wheel["digests"]["sha256"]:
                raise ConanException(
                    f"SHA-256 mismatch for downloaded {wheel['filename']}"
                )

    def _install_test_tool(
        self, python, python_package, python_lib, test_deps, runtime_libs
    ):
        # The Conan Python package contains ensurepip but intentionally does
        # not ship third-party test tools. Bootstrap pip and install pinned
        # pytest into a disposable test-only target, never into global Python.
        bootstrap = os.path.join(test_deps, "pip-bootstrap")
        pip_site = os.path.join(test_deps, "pip-site")
        wheel_dir = os.path.join(test_deps, "wheels")
        os.makedirs(bootstrap, exist_ok=True)
        os.makedirs(pip_site, exist_ok=True)
        os.makedirs(wheel_dir, exist_ok=True)
        bootstrap_env = self._python_environment(
            python_package, python_lib, runtime_libs=runtime_libs
        )
        with bootstrap_env.vars(self).apply():
            self.run(
                " ".join(
                    [
                        shlex.quote(python),
                        "-m",
                        "ensurepip",
                        "--root",
                        shlex.quote(bootstrap),
                        "--upgrade",
                        "--default-pip",
                    ]
                ),
                env="conanrun",
            )
        pip_candidates = []
        for root, _, _ in os.walk(bootstrap):
            if os.path.basename(root) == "site-packages":
                pip_candidates.append(root)
        if not pip_candidates:
            raise ConanException("ensurepip did not produce a pip site-packages directory")
        self._download_test_wheels(wheel_dir, test_deps)
        pip_env = self._python_environment(
            python_package,
            python_lib,
            (pip_candidates[0],),
            runtime_libs,
        )
        with pip_env.vars(self).apply():
            self.run(
                " ".join(
                    [
                        shlex.quote(python),
                        "-m",
                        "pip",
                        "install",
                        "--disable-pip-version-check",
                        "--no-index",
                        "--find-links",
                        shlex.quote(wheel_dir),
                        "--no-compile",
                        "--target",
                        shlex.quote(pip_site),
                        f"pytest=={self.pytest_version}",
                    ]
                ),
                env="conanrun",
            )
        return pip_site

    def test(self):
        package = self.dependencies["fastconstmap"].package_folder
        python_package = self.dependencies["python"].package_folder
        site = self._first(
            os.path.join(package, "lib", "python*", "site-packages"),
            "fastconstmap site-packages",
        )
        tests = os.path.join(package, "share", "fastconstmap", "tests")
        if not os.path.isdir(tests):
            raise ConanException(f"upstream tests missing: {tests}")
        python = self._python_executable(python_package)
        python_lib = self._first(
            os.path.join(python_package, "lib", "libpython*.so"),
            "Conan Python shared library",
        )
        test_deps = os.path.join(self.build_folder, "_fastconstmap_test_deps")
        runtime_libs = self._runtime_library_dirs()
        basetmp = self._writable_temp_root()
        script = os.path.join(os.path.dirname(__file__), "test_fastconstmap.py")
        try:
            pytest_site = self._install_test_tool(
                python,
                python_package,
                os.path.dirname(python_lib),
                test_deps,
                runtime_libs,
            )
            test_env = self._python_environment(
                python_package,
                os.path.dirname(python_lib),
                (site, pytest_site),
                runtime_libs,
            )
            with test_env.vars(self).apply():
                self.run(
                    " ".join(
                        [
                            shlex.quote(python),
                            shlex.quote(script),
                            shlex.quote(tests),
                            shlex.quote(basetmp),
                        ]
                    ),
                    env="conanrun",
                )
        finally:
            shutil.rmtree(test_deps, ignore_errors=True)
            shutil.rmtree(basetmp, ignore_errors=True)
