#!/usr/bin/env python3
"""Conan recipe for glances 4.5.4 — Python curses-based system monitoring tool.

Glances is a cross-platform monitoring tool written in Python. It uses
psutil for system metrics and optionally curses for the terminal UI.

Build system: setuptools (pyproject.toml, build-backend: setuptools.build_meta)
Package type: application (CLI tool with console_scripts entry point)

Dependencies (runtime, installed via pip to a bundled deps directory):
  - psutil >= 5.6.7 (C extension, OHOS-adapted wheel from community PyPI)
  - defusedxml
  - packaging
  - jinja2
  - pyinstrument >= 5.1.2
  - shtab (non-Windows)

NOTE: pip must resolve against an OHOS-adapted index that ships
cp312-ohos_aarch64 wheels (e.g. https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi
or https://pypi.repo.openharmony.cn/...). The official pypi.org has no
linux-ohos platform wheels for psutil/pyinstrument.

R32: settings.os check uses in ("Linux", "OHOS").
R38: Command-line tool — commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GlancesConan(ConanFile):
    name = "glances"
    version = "4.5.4"
    description = "A cross-platform curses-based monitoring tool"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/nicolargo/glances"
    url = "https://github.com/nicolargo/glances"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # Install glances itself (no deps, just the package)
        ret = self.run(
            f'python3 -m pip install . --no-deps --target="{self.build_folder}/install" --quiet 2>&1',
            cwd=src,
        )
        if ret != 0:
            raise ConanException(
                f"pip install glances failed with exit code {ret}"
            )

        # Install runtime deps to a bundled deps directory
        deps_target = os.path.join(self.build_folder, "install", "glances-deps")
        ret = self.run(
            'python3 -m pip install '
            '"psutil>=5.6.7" defusedxml packaging jinja2 "pyinstrument>=5.1.2" shtab '
            f'--target="{deps_target}" --quiet 2>&1',
            cwd=src,
        )
        if ret != 0:
            raise ConanException(
                f"pip install runtime deps failed with exit code {ret}"
            )

    def package(self):
        install_dir = os.path.join(self.build_folder, "install")

        # Copy bin/ (glances entry-point script)
        copy(self, "*", src=os.path.join(install_dir, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        # Copy glances Python package
        copy(self, "*", src=os.path.join(install_dir, "glances"),
             dst=os.path.join(self.package_folder, "glances"), keep_path=True)

        # Copy bundled runtime deps
        # keep_path=True is REQUIRED: pip --target installs each dep as a
        # package directory (psutil/, jinja2/, ...). Flattening would destroy
        # the layout and let stray top-level modules (e.g. pyinstrument's
        # types.py) shadow stdlib modules.
        deps_dir = os.path.join(install_dir, "glances-deps")
        if os.path.isdir(deps_dir):
            copy(self, "*", src=deps_dir,
                 dst=os.path.join(self.package_folder, "glances-deps"),
                 keep_path=True)

        # Copy license and docs
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        # Copy man page
        man_src = os.path.join(self.source_folder, "docs", "man", "glances.1")
        if os.path.isfile(man_src):
            copy(self, "glances.1", src=os.path.join(self.source_folder, "docs", "man"),
                 dst=os.path.join(self.package_folder, "share", "man", "man1"),
                 keep_path=False)

        # Copy config files
        conf_src = os.path.join(self.source_folder, "conf")
        if os.path.isdir(conf_src):
            copy(self, "*", src=conf_src,
                 dst=os.path.join(self.package_folder, "share", "glances", "conf"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share", "glances", "glances-deps"]

        # Set PYTHONPATH so glances can find its modules and bundled deps
        # PYTHONPATH must include package root (parent of glances/) and deps
        pkg = self.package_folder
        self.runenv_info.append_path(
            "PYTHONPATH",
            pkg,
        )
        self.runenv_info.append_path(
            "PYTHONPATH",
            os.path.join(pkg, "glances-deps"),
        )
