#!/usr/bin/env python3
"""Conan recipe for check-jsonschema 0.28.4 — JSON Schema validation CLI.

check-jsonschema is a pure Python tool (no C/C++ extensions in the
package itself). It provides a command-line interface and pre-commit
hook for validating JSON/YAML files against JSON Schema.

Build:  pip wheel . --no-deps
Install: extract wheel to <prefix>/lib/python3.X/site-packages,
         create bin/check-jsonschema wrapper
Type:   application (console_scripts: check-jsonschema = check_jsonschema:main)
Deps:   ruamel.yaml, jsonschema, regress, requests, click (pip-managed,
        not conan dependencies — installed in build() for test availability)

R26: Not applicable (no system-name collision).
R32: settings.os must check in ("Linux", "OHOS").
R38: Command-line tool — commands.json declared at software level.
"""
import os
import shutil
import sys
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout


class CheckJsonschemaConan(ConanFile):
    name = "check-jsonschema"
    version = "0.28.4"
    description = "A jsonschema CLI and pre-commit hook for validating JSON/YAML files against schemas"
    license = "Apache-2.0"
    homepage = "https://github.com/python-jsonschema/check-jsonschema"
    url = "https://github.com/python-jsonschema/check-jsonschema"

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

        # Install runtime deps so test_package can import check_jsonschema
        python3 = shutil.which("python3")
        if not python3:
            raise ConanInvalidConfiguration(
                "python3 is required to build check-jsonschema; "
                "ensure python3 is on PATH")
        # Deps are for test availability only; tolerate failures (e.g.
        # already installed or offline) — the wheel build itself uses --no-deps
        self.run(
            f'"{python3}" -m pip install --quiet '
            f'"click>=8,<9" "jsonschema>=4.18.0,<5.0" '
            f'"ruamel.yaml==0.18.6" "regress>=0.4.0" "requests<3.0" '
            f'2>&1 || true  # deps optional, wheel build is --no-deps',
            env="conanbuild",
        )

        wheel_dir = os.path.join(self.build_folder, "wheel")
        os.makedirs(wheel_dir, exist_ok=True)
        self.run(
            f'"{python3}" -m pip wheel "{self.source_folder}" --no-deps '
            f'--wheel-dir="{wheel_dir}"',
            env="conanbuild",
        )

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkg = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site_pkg, exist_ok=True)

        wheel_dir = os.path.join(self.build_folder, "wheel")
        for whl in os.listdir(wheel_dir):
            if whl.endswith(".whl"):
                with zipfile.ZipFile(os.path.join(wheel_dir, whl)) as z:
                    z.extractall(site_pkg)
                break
        else:
            raise ConanInvalidConfiguration(
                f"No .whl file found in {wheel_dir}; "
                "pip wheel may have failed silently")

        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "check-jsonschema")
        wrapper_content = (
            "#!/bin/sh\n"
            "# check-jsonschema wrapper — by Conan recipe\n"
            'WRAPPER_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'PREFIX_DIR="$(cd "$WRAPPER_DIR/.." && pwd)"\n'
            f'SITE_PKG="$PREFIX_DIR/lib/{py_ver}/site-packages"\n'
            'if [ -d "$SITE_PKG/check_jsonschema" ]; then\n'
            '    PYTHONPATH="$SITE_PKG${PYTHONPATH:+:$PYTHONPATH}" \\\n'
            '        exec python3 -m check_jsonschema "$@"\n'
            'else\n'
            '    exec python3 -m check_jsonschema "$@"\n'
            'fi\n'
        )
        with open(wrapper, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper, 0o755)

        from conan.tools.files import copy
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
