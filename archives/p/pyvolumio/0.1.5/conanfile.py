#!/usr/bin/env python3
"""Conan recipe for pyvolumio 0.1.5 — Python interface to control Volumio.

Pure Python package (setuptools). No C/C++ compilation.
Runtime deps (aiohttp + transitive) are vendored into package site-packages
from files.pythonhosted.org direct URLs so consumers only need PYTHONPATH.
"""
import os
import sys
import textwrap

from conan import ConanFile
from conan.tools.files import (
    get,
    copy,
    download,
    apply_conandata_patches,
    export_conandata_patches,
)


class PyvolumioConan(ConanFile):
    name = "pyvolumio"
    version = "0.1.5"
    description = "A python library to control Volumio."
    license = "MIT"
    homepage = "https://github.com/OnFreund/PyVolumio"
    url = ""

    # R32: settings.os check must use in ("Linux", "OHOS")
    # Pure Python: no compiler/build_type needed
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _find_site_packages(self, root, require_pkg="pyvolumio"):
        py_ver = self._py_ver()
        for candidate in (
            os.path.join(root, "lib", py_ver, "site-packages"),
            os.path.join(root, "lib", py_ver, "dist-packages"),
            os.path.join(root, "local", "lib", py_ver, "site-packages"),
            os.path.join(root, "local", "lib", py_ver, "dist-packages"),
            os.path.join(root, "lib64", py_ver, "site-packages"),
        ):
            if os.path.isdir(candidate) and (
                require_pkg is None
                or os.path.isdir(os.path.join(candidate, require_pkg))
            ):
                return candidate
        return None

    def _download_python_deps(self):
        """Fetch pinned wheels/sdists from files.pythonhosted.org (CI-reachable)."""
        deps_dir = os.path.join(self.build_folder, "pypi_deps")
        os.makedirs(deps_dir, exist_ok=True)
        local_paths = []
        for dep in self.conan_data["python_deps"]:
            filename = os.path.basename(dep["url"].split("?")[0])
            dest = os.path.join(deps_dir, filename)
            download(self, url=dep["url"], filename=dest, sha256=dep["sha256"])
            local_paths.append(dest)
        return local_paths

    def build(self):
        apply_conandata_patches(self)

        python_exe = sys.executable
        src_dir = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f"--timeout 120 --retries 3 setuptools wheel"
        )

        # Install runtime deps from direct URLs (no pypi.org/simple).
        # --no-deps: every transitive package is listed in conandata.yml.
        # AIOHTTP_NO_EXTENSIONS: OHOS has no linkable libpython for aiohttp
        # C extensions; keep the package ELF-free (L2/L4 skip).
        # --no-build-isolation: aiohttp sdist lists pkgconfig in build-system
        # requires, but pure-Python mode never imports it; isolation would try
        # (and fail) to fetch pkgconfig under --no-index.
        dep_files = " ".join(f'"{p}"' for p in self._download_python_deps())
        self.run(
            f'env AIOHTTP_NO_EXTENSIONS=1 {python_exe} -m pip install '
            f'--break-system-packages --ignore-installed --no-deps '
            f'--no-index --no-build-isolation --timeout 120 --retries 3 '
            f'--prefix="{staging}" {dep_files}'
        )
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--ignore-installed --prefix="{staging}" "{src_dir}"'
        )

        # ── Upstream has no official test suite ──
        # Run an offline smoke suite covering import, construction, and
        # canonic_url as build-phase verification (prints PASS for CI L1c).
        site = self._find_site_packages(staging)
        if site is None:
            raise Exception(f"pyvolumio site-packages not found under staging={staging}")

        smoke = os.path.join(self.build_folder, "_upstream_smoke.py")
        with open(smoke, "w", encoding="utf-8") as fh:
            fh.write(
                textwrap.dedent(
                    """\
                    from pyvolumio import CannotConnectError, Volumio

                    assert Volumio is not None
                    assert issubclass(CannotConnectError, Exception)

                    v = Volumio("192.168.1.10", 3000)
                    assert v._host == "192.168.1.10"
                    assert v._port == 3000
                    assert v._session is None
                    assert v._created_session is False

                    assert v.canonic_url(None) is None
                    assert v.canonic_url("https://cdn.example/cover.jpg") == (
                        "https://cdn.example/cover.jpg"
                    )
                    assert v.canonic_url("http://cdn.example/cover.jpg") == (
                        "http://cdn.example/cover.jpg"
                    )
                    assert v.canonic_url("/albumart?web=x") == (
                        "http://192.168.1.10:3000/albumart?web=x"
                    )
                    assert callable(v.get_state)
                    assert callable(v.play)
                    assert callable(v.get_queue)
                    print("PASS: pyvolumio upstream smoke (import/construct/canonic_url)")
                    """
                )
            )
        self.run(f'env PYTHONPATH="{site}" {python_exe} "{smoke}"')

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )

        site_src = self._find_site_packages(staging)
        if site_src is None:
            raise Exception(
                f"pyvolumio site-packages not found under staging={staging}"
            )
        copy(self, "*", src=site_src, dst=site_dst)

        license_src = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(license_src):
            copy(
                self,
                "LICENSE",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )

    def package_info(self):
        # Library-only Python package: do not declare executable dirs
        # (avoids L0k false CLI detect from recipe text matching).
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        site_packages = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
