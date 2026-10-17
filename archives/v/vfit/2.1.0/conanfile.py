#!/usr/bin/env python3
"""Conan recipe — vfit 2.1.0 (Variable Font Instancing Tool, pure Python)."""

import os
import sys
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get


class VfitConan(ConanFile):
    name = "vfit"
    version = "2.1.0"
    description = "Generate backwards-compatible, static instances of variable fonts"
    license = "MIT"
    homepage = "https://github.com/jonpalmisc/vfit"
    url = "https://github.com/jonpalmisc/vfit"
    topics = ("fonts", "fonttools", "variable-fonts")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        # Pure Python — no compilation. Install runtime Python deps into the
        # build environment so import succeeds in test_package.
        # Use --break-system-packages because OHOS base python is system-managed.
        # This step previously succeeded; keep it best-effort so a transient
        # pip mirror failure does not block packaging (test_package will still
        # try to import and report clearly).
        python_exe = sys.executable
        try:
            self.run(
                f'"{python_exe}" -m pip install --break-system-packages '
                f'--disable-pip-version-check --timeout 120 --retries 3 '
                f'"fonttools>=4.13.0" "tqdm>=4.48.0" "brotli>=1.0.7"',
            )
        except Exception as e:
            self.output.warning(f"pip install runtime deps failed (non-fatal): {e}")

    def package(self):
        # Avoid `pip install --prefix` which requires poetry.masonry.api
        # (vfit 2.1.0 uses legacy poetry build-backend). The package is pure
        # Python with only vfit/*.py, so copy directly.
        py_ver = self._py_ver()
        site_dst = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site_dst, exist_ok=True)

        src_pkg = os.path.join(self.source_folder, "vfit")
        if not os.path.isdir(src_pkg):
            raise Exception(f"vfit source package not found: {src_pkg}")
        # dirs_exist_ok=True for re-entrant package()
        shutil.copytree(src_pkg, os.path.join(site_dst, "vfit"), dirs_exist_ok=True)

        # Ensure bin/vfit wrapper exists (poetry script vfit = vfit.app:main)
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        bin_vfit = os.path.join(bin_dir, "vfit")
        # Always (re)create wrapper that adjusts PYTHONPATH to our site-packages
        # so `vfit --help` works even when PYTHONPATH not exported.
        site_packages_rel = os.path.join("lib", py_ver, "site-packages")
        with open(bin_vfit, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/usr/bin/env python3\n")
            f.write("import os, sys\n")
            f.write('_pkg_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))\n')
            f.write(f'_sp = os.path.join(_pkg_root, "{site_packages_rel}")\n')
            f.write("if _sp not in sys.path:\n")
            f.write("    sys.path.insert(0, _sp)\n")
            f.write("from vfit.app import main\n")
            f.write('if __name__ == "__main__":\n')
            f.write("    main()\n")
        try:
            os.chmod(bin_vfit, 0o755)
        except OSError:
            pass

        # Licenses
        for lic in ("LICENSE.txt", "LICENSE", "LICENSE.rst"):
            src = os.path.join(self.source_folder, lic)
            if os.path.isfile(src):
                copy(self, lic, src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

        py_ver = self._py_ver()
        site_packages = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.buildenv_info.prepend_path("PYTHONPATH", site_packages)
        bin_path = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PATH", bin_path)
        self.buildenv_info.prepend_path("PATH", bin_path)
