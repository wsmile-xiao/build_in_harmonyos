#!/usr/bin/env python3
"""Conan recipe for pysmappee 0.2.29 — Official Smappee API/MQTT Python wrapper.

Pure Python package (setuptools). No C/C++ compilation.
Runtime deps installed into the package site-packages so consumers only need
PYTHONPATH from package_info.
"""
import os
import sys
import textwrap

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PysmappeeConan(ConanFile):
    name = "pysmappee"
    version = "0.2.29"
    description = "Official Smappee dev API and MQTT python wrapper"
    license = "MIT"
    homepage = "https://github.com/smappee/pysmappee"
    url = ""

    # R32: settings.os check must use in ("Linux", "OHOS")
    # Pure Python: no compiler/build_type needed
    settings = "os", "arch"

    # Keep in sync with setup.py install_requires
    _RUNTIME_DEPS = (
        "cachetools>=4.0.0",
        "paho-mqtt>=1.5.0",
        "pytz>=2019.3",
        "requests>=2.23.0",
        "requests-oauthlib>=1.3.0",
        "schedule>=1.1.0",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _find_site_packages(self, root, require_pkg="pysmappee"):
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

    def build(self):
        apply_conandata_patches(self)

        python_exe = sys.executable
        src_dir = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        deps = " ".join(f'"{d}"' for d in self._RUNTIME_DEPS)
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f"--timeout 120 --retries 3 setuptools wheel"
        )

        # Install runtime deps + pysmappee into staging (self-contained PYTHONPATH).
        # --ignore-installed is required: otherwise pip skips packages already
        # present on the system and staging only gets pysmappee itself.
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--ignore-installed --timeout 120 --retries 3 '
            f'--prefix="{staging}" {deps}'
        )
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--ignore-installed --prefix="{staging}" "{src_dir}"'
        )

        # ── Upstream has no real test suite (test/ is empty) ──
        # Run an offline smoke suite covering pure helpers/config as build-phase
        # verification substitute (prints PASS for CI L1c evidence).
        site = self._find_site_packages(staging)
        if site is None:
            raise Exception(f"pysmappee site-packages not found under staging={staging}")

        smoke = os.path.join(self.build_folder, "_upstream_smoke.py")
        with open(smoke, "w", encoding="utf-8") as fh:
            fh.write(
                textwrap.dedent(
                    """\
                    import sys
                    from pysmappee.helper import (
                        urljoin,
                        is_smappee_energy,
                        is_smappee_solar,
                        is_smappee_plus,
                        is_smappee_genius,
                        is_smappee_connect,
                    )
                    from pysmappee import config
                    from pysmappee import Smappee
                    from pysmappee.api import SmappeeApi

                    assert urljoin("https://a.com/", "b", "c") == "https://a.com/b/c"
                    assert is_smappee_energy("100123")
                    assert is_smappee_solar("110123")
                    assert is_smappee_plus("200123")
                    assert is_smappee_genius("500123")
                    assert is_smappee_connect("510123")
                    assert 1 in config.config["API_URL"]
                    assert "servicelocation_url" in config.config["API_URL"][1]
                    assert Smappee is not None
                    assert SmappeeApi is not None
                    print("PASS: pysmappee upstream smoke (helper/config/API symbols)")
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
                f"pysmappee site-packages not found under staging={staging}"
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
        # Library-only Python package: leave bindirs unset (avoid L0k false CLI detect)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        site_packages = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
