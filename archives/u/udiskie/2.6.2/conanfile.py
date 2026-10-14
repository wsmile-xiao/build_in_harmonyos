#!/usr/bin/env python3
"""Conan recipe for udiskie 2.6.2 — removable-disk automounter based on udisks2.

Upstream: https://github.com/coldfix/udiskie (MIT)

udiskie is a **pure Python 3 application** (PEP 517 / setuptools); the upstream
source tree contains no C/C++ sources. It ships four console scripts
(pyproject.toml ``[project.scripts]``):

    udiskie / udiskie-mount / udiskie-umount / udiskie-info

HarmonyOS PC (aarch64) adaptation
---------------------------------
* The four upstream entry points are regenerated as portable launchers
  (``#!/usr/bin/env python3`` plus a package-relative site-packages bootstrap)
  so that they run standalone, without the conan runenv and without touching
  the shared interpreter's site-packages.
* The pure-Python runtime dependencies are **vendored** into the package so the
  launchers are self-contained:
    - ``docopt`` (MIT)   - CLI argument parsing (needed to start the CLI),
    - ``PyYAML`` (MIT)   - YAML config parsing.
  They are pulled at build time through ``tool_requires`` and copied into the
  package's site-packages (only the pure-Python ``yaml`` package is copied; the
  optional ``_yaml`` C accelerator is skipped). PyGObject (``gi``) is a native
  binding and stays a conan requirement.
* Two portability patches are applied (see conandata.yml):
    0001  defer the gi runtime so ``--version`` / ``--help`` work where the gi
          C extension cannot be loaded,
    0002  make ``python-keyutils`` optional with an in-process fallback.
* The upstream unittest suites (``test/test_match.py``, ``test/test_cache.py``)
  are executed for real in :meth:`build` (R51).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# Native runtime dependency (the only one that must come from the registry).
REQUIRES = ["pygobject/3.58.0"]

# Pure-Python runtime dependencies, vendored into the package.
# (ref, entry in the dependency's site-packages, destination name)
VENDOR_PY = [
    ("docopt", "docopt.py", "docopt.py"),
    ("pyyaml", "yaml", "yaml"),
]
# Build-time provenance of the vendored sources (also in the ohpcd registry).
TOOL_REQUIRES = ["docopt/0.6.2", "pyyaml/6.0.2"]

# pyproject.toml [project.scripts] -> entry-point class in udiskie.cli
SCRIPTS = [
    ("udiskie", "Daemon"),
    ("udiskie-mount", "Mount"),
    ("udiskie-umount", "Umount"),
    ("udiskie-info", "Info"),
]

# Upstream unittest suites (run in build(), R51).
UPSTREAM_TESTS = ["test/test_match.py", "test/test_cache.py"]


class UdiskieConan(ConanFile):
    name = "udiskie"
    version = "2.6.2"
    description = ("Removable disk automounter based on udisks "
                   "(pure Python CLI: udiskie/udiskie-mount/udiskie-umount/"
                   "udiskie-info)")
    license = "MIT"
    homepage = "https://github.com/coldfix/udiskie"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    requires = tuple(REQUIRES)
    tool_requires = tuple(TOOL_REQUIRES)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS is part of the Linux family for this package.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is only supported on Linux/OHOS, "
                f"not {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _py_tag(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _dep_site(self, ref):
        """site-packages directory of a build-time (tool_requires) python dep."""
        dep = self.dependencies.build[ref]
        base = dep.package_folder
        for sub in (os.path.join("lib", "python", "site-packages"),
                    os.path.join("lib", self._py_tag(), "site-packages")):
            cand = os.path.join(base, sub)
            if os.path.isdir(cand):
                return cand
        raise ConanException(f"site-packages not found for {ref}")

    def _vendor_python(self, site):
        """Copy the pure-Python runtime deps into the staged site-packages."""
        for ref, entry, dest in VENDOR_PY:
            src = os.path.join(self._dep_site(ref), entry)
            if not os.path.exists(src):
                raise ConanException(f"vendored source missing: {src}")
            if os.path.isdir(src):
                os.makedirs(os.path.join(site, dest), exist_ok=True)
                # keep_path=True preserves the yaml/ sub-package layout; the
                # C accelerator (yaml/_yaml) is skipped so the package stays
                # pure Python (it cannot be loaded on OHOS anyway).
                shutil.copytree(src, os.path.join(site, dest),
                                dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("_yaml"))
            else:
                shutil.copy2(src, os.path.join(site, dest))

    @staticmethod
    def _launcher(cls, site_rel):
        """Regenerate an upstream console script for OHOS packaging.

        Portable shebang plus a package-relative site-packages bootstrap so the
        script runs standalone (no conan runenv, no shared interpreter
        site-packages).
        """
        return (
            "#!/usr/bin/env python3\n"
            "# udiskie console script regenerated for OHOS conan packaging\n"
            "import os\n"
            "import sys\n"
            "_pkg_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))\n"
            "_site = os.path.join(_pkg_root, {site!r})\n"
            "if os.path.isdir(_site) and _site not in sys.path:\n"
            "    sys.path.insert(0, _site)\n"
            "from udiskie.cli import {cls}\n"
            "if __name__ == '__main__':\n"
            "    sys.exit({cls}.main())\n"
        ).format(site=site_rel, cls=cls)

    # ------------------------------------------------------------------ #
    # build / package
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)
        site_rel = os.path.join("lib", self._py_tag(), "site-packages")
        staging = os.path.join(self.build_folder, "staging")
        site = os.path.join(staging, site_rel)

        # 1. stage the pure-Python package (udiskie/ incl. icons/ + *.ui data)
        copy(self, "*",
             src=os.path.join(self.source_folder, "udiskie"),
             dst=os.path.join(site, "udiskie"),
             keep_path=True)

        # 2. vendor the pure-Python runtime deps (self-contained launchers)
        self._vendor_python(site)

        # 3. regenerate the four console scripts (OHOS-portable launchers)
        bindir = os.path.join(staging, "bin")
        os.makedirs(bindir, exist_ok=True)
        for name, cls in SCRIPTS:
            path = os.path.join(bindir, name)
            with open(path, "w") as f:
                f.write(self._launcher(cls, site_rel))
            os.chmod(path, 0o755)

        # 4. execute the upstream unittest suites for real (R51)
        pythonpath = os.pathsep.join([self.source_folder, site])
        for test in UPSTREAM_TESTS:
            self.output.info(f"=== upstream test: {test} ===")
            self.run(
                f'PYTHONPATH="{pythonpath}" python3 {test} -v',
                cwd=self.source_folder)

    def package(self):
        site_rel = os.path.join("lib", self._py_tag(), "site-packages")
        staging = os.path.join(self.build_folder, "staging")
        site = os.path.join(staging, site_rel)
        if not os.path.isdir(os.path.join(site, "udiskie")):
            raise ConanException(
                f"staged udiskie package missing: {site}/udiskie")
        copy(self, "*", src=site, dst=os.path.join(self.package_folder, site_rel))
        copy(self, "*", src=os.path.join(staging, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # license of the vendored pure-Python dependencies (MIT)
        lic = os.path.join(self.dependencies.build["pyyaml"].package_folder,
                           "licenses", "LICENSE")
        if os.path.isfile(lic):
            shutil.copy2(lic, os.path.join(self.package_folder, "licenses",
                                           "PyYAML-LICENSE"))

    def package_info(self):
        site_rel = os.path.join("lib", self._py_tag(), "site-packages")
        own_site = os.path.join(self.package_folder, site_rel)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        # The package site-packages also carries the vendored pure-Python deps,
        # so consumers only need this single import path.
        self.runenv_info.prepend_path("PYTHONPATH", own_site)
        self.buildenv_info.prepend_path("PYTHONPATH", own_site)
