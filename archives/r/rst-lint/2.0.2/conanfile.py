#!/usr/bin/env python3
"""Conan recipe — rst-lint 2.0.2 (reStructuredText linter, pure-Python CLI).

Upstream  : https://github.com/twolfson/restructuredtext-lint
PyPI name : restructuredtext-lint   (import package: restructuredtext_lint)
Product   : lib/pythonX.Y/site-packages/restructuredtext_lint/ + the two
            console scripts `rst-lint` and `restructuredtext-lint`
            (setup.py console_scripts -> restructuredtext_lint.cli:main).

HarmonyOS PC adaptation
-----------------------
`rst-lint` is a pure-Python application (no C/C++ extension modules): the
upstream sdist ships `setup.py` (setuptools, no pyproject.toml). The package
is staged by copying `restructuredtext_lint/` into a versioned site-packages
directory and generating the two POSIX entry scripts from the upstream
`console_scripts` metadata (docutils 0.23 precedent) — deterministic and
network-free; pip is never asked to resolve anything during the build.

Runtime dependency `docutils` (requirements.txt: ``docutils>=0.11,<1.0``) is
consumed as the published Conan package ``docutils/0.23`` (verified published
on ohpcd — the recipe download check returned EXIT=0, see notes.md); the
declared range is satisfied by 0.23. `docutils` ships its own site-packages
directory, which is appended to PYTHONPATH in package_info() so that
``import docutils`` resolves from the Conan run environment.

Upstream test/lint-only requirements (requirements-dev.txt: nose-py3==1.8.0,
flake8==7.3.0, flake8-quotes==3.4.0) are NOT runtime dependencies; see
notes.md and test_package/MANIFEST.yml.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# Upstream setup.py `entry_points.console_scripts` (two aliases, one target).
_ENTRY_POINTS = {
    "rst-lint": "restructuredtext_lint.cli:main",
    "restructuredtext-lint": "restructuredtext_lint.cli:main",
}


class RstLintConan(ConanFile):
    name = "rst-lint"
    version = "2.0.2"
    description = "reStructuredText linter (pure-Python CLI)"
    license = "Unlicense"
    homepage = "https://github.com/twolfson/restructuredtext-lint"
    url = "https://github.com/twolfson/restructuredtext-lint"

    package_type = "application"
    # L0p: the OHOS profile supplies all four settings (compiler=clang/15).
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # requirements.txt: docutils>=0.11,<1.0 -> published ohpcd recipe 0.23
        self.requires("docutils/0.23")

    # -- helpers ---------------------------------------------------------
    def _pyver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _site_packages(self, base):
        return os.path.join(base, "lib", self._pyver(), "site-packages")

    def _dep_site_packages(self, dep):
        for cand in (
            os.path.join("lib", self._pyver(), "site-packages"),
            os.path.join("lib", "python3.12", "site-packages"),
            os.path.join("lib", "site-packages"),
            os.path.join("lib", "python", "site-packages"),
        ):
            path = os.path.join(str(dep.package_folder), cand)
            if os.path.isdir(path):
                return path
        return None

    # -- conan flow ------------------------------------------------------
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src_pkg = os.path.join(self.source_folder, "restructuredtext_lint")
        if not os.path.isdir(src_pkg):
            raise ConanException(
                "restructuredtext_lint package directory missing: " + src_pkg)
        # Fail fast on syntax errors, then stage a clean copy.
        for name in ("__init__.py", "cli.py", "lint.py"):
            path = os.path.join(src_pkg, name)
            if not os.path.isfile(path):
                raise ConanException("expected source file missing: " + path)
            with open(path, "rb") as fh:
                compile(fh.read(), path, "exec")
        staging = os.path.join(self.build_folder, "site-packages")
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            src_pkg, os.path.join(staging, "restructuredtext_lint"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def package(self):
        staging = os.path.join(self.build_folder, "site-packages")
        if not os.path.isdir(staging):
            raise ConanException("staging directory missing: " + staging)
        site = self._site_packages(self.package_folder)
        shutil.copytree(staging, site, dirs_exist_ok=True)
        # cli.py reads its VERSION file at import time -> it must ship.
        version_file = os.path.join(site, "restructuredtext_lint", "VERSION")
        if not os.path.isfile(version_file):
            raise ConanException("restructuredtext_lint/VERSION missing in package")
        # Generate the two console scripts (docutils 0.23 precedent):
        # POSIX shebang + sys.path injection so the CLI runs without conanrun.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        rel_site = os.path.join("lib", self._pyver(), "site-packages")
        for script_name, entry_point in _ENTRY_POINTS.items():
            module_path, func_name = entry_point.split(":")
            content = (
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "_pkg_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))\n"
                '_sp = os.path.join(_pkg_root, "{0}")\n'.format(rel_site) +
                "if _sp not in sys.path:\n"
                "    sys.path.insert(0, _sp)\n"
                "from {0} import {1}\n".format(module_path, func_name) +
                'if __name__ == "__main__":\n'
                '    sys.argv[0] = sys.argv[0].removesuffix(".exe")\n'
                "    sys.exit({0}())\n".format(func_name)
            )
            script_path = os.path.join(bin_dir, script_name)
            with open(script_path, "w") as fh:
                fh.write(content)
            os.chmod(script_path, 0o755)

    def package_info(self):
        # R38: CLI tool -> expose bin/; consumers run `rst-lint`.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        site = self._site_packages(self.package_folder)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        # docutils ships its own site-packages and does not publish PYTHONPATH
        # itself; expose it so `import docutils` resolves in the run env.
        if "docutils" in self.dependencies:
            dep_site = self._dep_site_packages(self.dependencies["docutils"])
            if dep_site:
                self.runenv_info.append_path("PYTHONPATH", dep_site)
                self.buildenv_info.append_path("PYTHONPATH", dep_site)
