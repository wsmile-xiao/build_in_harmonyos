"""Conan recipe for TinyDB, a pure-Python document database."""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class TinyDBConan(ConanFile):
    name = "tinydb"
    version = "4.8.2"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/msiemens/tinydb"
    description = "TinyDB is a tiny, document oriented database written in pure Python"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # The PyPI sdist includes the upstream suite. Keep its test runner in
        # this package's build folder instead of mutating the shared Python.
        py = "/data/service/hnp/bin/python3" if os.path.isfile(
            "/data/service/hnp/bin/python3") else sys.executable
        env = dict(os.environ)
        test_tools = os.path.join(self.build_folder, "test-tools")
        probe = subprocess.run([py, "-m", "pytest", "--version"],
                              env=env, capture_output=True, text=True)
        if probe.returncode != 0:
            os.makedirs(test_tools, exist_ok=True)
            install = subprocess.run(
                [py, "-m", "pip", "install", "--disable-pip-version-check",
                 "--no-input", "--target", test_tools, "pytest==8.4.2"],
                env=env, capture_output=True, text=True, timeout=900)
            for line in (install.stdout + install.stderr).splitlines()[-12:]:
                self.output.info("test-tool: " + line)
            if install.returncode != 0:
                raise ConanException(
                    "Unable to provision isolated pytest 8.4.2 (exit %d)" %
                    install.returncode)
        paths = [test_tools, self.source_folder]
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        result = subprocess.run(
            [py, "-m", "pytest", "tests/", "-q", "--no-header",
             "-p", "no:cacheprovider", "--basetemp=" + os.path.join(self.build_folder, "pytest-tmp")],
            cwd=self.source_folder, env=env, capture_output=True,
            text=True, timeout=1800)
        for line in (result.stdout + result.stderr).splitlines()[-20:]:
            self.output.info("upstream: " + line)
        if result.returncode != 0:
            raise ConanException(
                "TinyDB upstream pytest suite failed (exit %d)" %
                result.returncode)

    def package(self):
        py_ver = "python%d.%d" % sys.version_info[:2]
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        source = os.path.join(self.source_folder, "tinydb")
        if not os.path.isdir(source):
            raise ConanException("TinyDB runtime source missing: " + source)
        shutil.copytree(source, os.path.join(site, "tinydb"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        license_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(license_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "LICENSE"),
                     os.path.join(license_dir, "LICENSE"))

    def package_info(self):
        self.cpp_info.libs = []
        py_ver = "python%d.%d" % sys.version_info[:2]
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)