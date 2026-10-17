#!/usr/bin/env python3
"""Conan recipe for kernel-hardening-checker 0.6.17.1 — pure Python CLI tool.

kernel-hardening-checker checks the security hardening options of the Linux
kernel (Kconfig options, kernel cmdline, sysctl). Pure Python, stdlib only,
no C/C++ compilation. Entry point: console script `kernel-hardening-checker`
(kernel_hardening_checker:main).

Packaging notes (differs from the py-cpuinfo sibling recipe):
  * the package has NO __main__.py, so `python3 -m kernel_hardening_checker`
    does NOT work; the bin/ wrapper imports the package and calls main()
    directly (same as the upstream bin/kernel-hardening-checker launcher);
  * the wrapper resolves site-packages relative to its own location, so it
    works without the conanrun environment (CI L2 runs it bare);
  * the built wheel already ships kernel_hardening_checker/config_files/
    (pyproject-mode setuptools defaults include_package_data=True); the
    recipe still copies that sample Kconfig tree from the exported source
    as a defensive, idempotent safety net.

R38 applies (CLI tool, software-level commands.json required). R26 not
applicable (no system-typed native library). No patches needed: upstream code
has no platform branches and runs on pure stdlib.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class KernelHardeningCheckerConan(ConanFile):
    name = "kernel-hardening-checker"
    version = "0.6.17.1"
    description = "A tool for checking the security hardening options of the Linux kernel"
    license = "GPL-3.0-only"
    homepage = "https://github.com/a13xp0p0v/kernel-hardening-checker"
    url = ""

    package_type = "application"
    # Pure Python noarch: no compiler needed, but OHOS profile requires all 4 settings
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            filename="kernel-hardening-checker-0.6.17.1.tar.gz",
            strip_root=True,
        )

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        # No patches for this version (kept for conandata-driven future use)
        apply_conandata_patches(self)

        python_exe = sys.executable
        src_dir = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        # Build deps: setuptools (pyproject requires >= 77.0.3) + wheel
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools wheel',
        )

        # Install into staging via --prefix (also places console_scripts in bin/).
        # --no-build-isolation: reuse the bootstrapped setuptools instead of
        # letting pip create an isolated env that would re-download setuptools.
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--no-build-isolation --prefix="{staging}" "{src_dir}"',
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        bin_dst = os.path.join(self.package_folder, "bin")

        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "kernel_hardening_checker")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"kernel_hardening_checker site-packages not found under staging={staging}"
            )

        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

        # pip embeds the build-machine Python path in console-script shebangs.
        # Replace it with a portable wrapper. The package has no __main__.py,
        # so the wrapper imports the package and calls main() directly (the
        # upstream launcher bin/kernel-hardening-checker does the same).
        cli_path = os.path.join(bin_dst, "kernel-hardening-checker")
        if not os.path.isfile(cli_path):
            raise Exception(f"console script not found in staging bin/: {cli_path}")
        wrapper = (
            "#!/bin/sh\n"
            "# kernel-hardening-checker wrapper - by Conan recipe\n"
            'WRAPPER_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'PREFIX_DIR="$(cd "$WRAPPER_DIR/.." && pwd)"\n'
            f'SITE_PKG="$PREFIX_DIR/lib/{py_ver}/site-packages"\n'
            'PYTHONPATH="$SITE_PKG${PYTHONPATH:+:$PYTHONPATH}" \\\n'
            "    exec python3 -c 'import kernel_hardening_checker;"
            " kernel_hardening_checker.main()' \"$@\"\n"
        )
        with open(cli_path, "w", encoding="utf-8") as cli:
            cli.write(wrapper)
        os.chmod(cli_path, 0o755)

        # Defensive copy: the built wheel already includes
        # kernel_hardening_checker/config_files/ (pyproject-mode setuptools
        # defaults include_package_data=True), so this copy is an idempotent
        # safety net rather than a missing-data fix; it keeps `-c` runs
        # against real-world example configs working even if the wheel ever
        # stops shipping the data files.
        cfg_src = os.path.join(self.source_folder, "kernel_hardening_checker", "config_files")
        if os.path.isdir(cfg_src):
            copy(self, "*", src=cfg_src,
                 dst=os.path.join(site_dst, "kernel_hardening_checker", "config_files"))

        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

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
