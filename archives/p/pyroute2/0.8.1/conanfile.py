#!/usr/bin/env python3
"""Conan recipe for pyroute2 0.8.1 — Pure Python Netlink library.

pyroute2 provides netlink / RTNL APIs (addresses, routes, ipset, nftables, …).
Build system: setuptools (setup.py + setup.cfg). No C/C++ compilation.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Pyroute2Conan(ConanFile):
    name = "pyroute2"
    version = "0.8.1"
    description = "Python Netlink library"
    license = "GPL-2.0-or-later OR Apache-2.0"
    homepage = "https://github.com/svinota/pyroute2"
    url = ""

    # R32: settings.os check must use in ("Linux", "OHOS")
    # Pure Python: no compiler/build_type needed (same pattern as internetarchive)
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # GitHub tag tarballs omit this gitignored file; PyPI sdist includes it.
        # Generate from VERSION when missing so either source URL works.
        version_py = os.path.join(
            self.source_folder, "pyroute2", "config", "version.py"
        )
        if not os.path.isfile(version_py):
            version_file = os.path.join(self.source_folder, "VERSION")
            with open(version_file, encoding="utf-8") as fh:
                ver = fh.read().strip()
            with open(version_py, "w", encoding="utf-8") as fh:
                fh.write(f'__version__ = "{ver}"\n')
            self.output.info(f"Generated {version_py} from VERSION ({ver})")

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        apply_conandata_patches(self)

        python_exe = sys.executable
        src_dir = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        # Build deps (setuptools) + pytest for upstream unit tests
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools wheel pytest',
        )

        # Install into staging via --prefix (also places console_scripts in bin/)
        # Debian/Ubuntu pip may nest under staging/local/... — normalized in package()
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
        )

        # ── Upstream official unit tests (required) ──
        # Must run with cwd=tests so relative dump file paths resolve.
        # TEST_QUALITY_SPEC §3.3: tests/test_unit/test_entry_points/test_basic.py
        # opens a real AF_NETLINK socket to verify that NetlinkError aliases
        # behave identically at runtime. That socket is unavailable in the
        # OHOS worker container (no CAP_NET_ADMIN, no AF_NETLINK in the
        # unprivileged harness). Exempt it via --deselect and document
        # in MANIFEST.yml::upstream_test_exemption.
        tests_dir = os.path.join(src_dir, "tests")
        self.run(
            f'env PYTHONPATH="{src_dir}" {python_exe} -m pytest test_unit -q '
            f'--deselect tests/test_unit/test_entry_points/test_basic.py::test_exceptions',
            cwd=tests_dir,
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        bin_dst = os.path.join(self.package_folder, "bin")

        # Locate site-packages / dist-packages under staging (with or without local/)
        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
            os.path.join(staging, "lib64", py_ver, "site-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "pyroute2")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"pyroute2 site-packages not found under staging={staging}"
            )

        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

        for lic_name in (
            "LICENSE",
            "LICENSE.Apache-2.0",
            "LICENSE.GPL-2.0-or-later",
        ):
            src = os.path.join(self.source_folder, lic_name)
            if os.path.isfile(src):
                copy(
                    self,
                    lic_name,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

        site_packages = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
