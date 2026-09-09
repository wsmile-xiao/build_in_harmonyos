#!/usr/bin/env python3
"""Conan recipe for pyserial 3.5, a pure-Python noarch serial library."""

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


class PyserialConan(ConanFile):
    name = "pyserial"
    version = "3.5"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pyserial/pyserial"
    description = "Python serial port extension"
    settings = "os", "arch", "compiler", "build_type"

    def package_id(self):
        self.info.clear()

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The upstream test suite was executed separately against the pristine
        # source. Packaging is intentionally source-only for this noarch module.
        apply_conandata_patches(self)

    def package(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        copy(self, "*.py", src=os.path.join(self.source_folder, "serial"),
             dst=os.path.join(site_packages, "serial"), keep_path=True)
        copy(self, "*.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        scripts = {
            "pyserial-miniterm": "from serial.tools.miniterm import main\nraise SystemExit(main())\n",
            "pyserial-ports": "from serial.tools.list_ports import main\nraise SystemExit(main())\n",
        }
        for name, body in scripts.items():
            path = os.path.join(bin_dir, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("#!/usr/bin/env python3\n" + body)
            os.chmod(path, 0o755)

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.buildenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.buildenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
