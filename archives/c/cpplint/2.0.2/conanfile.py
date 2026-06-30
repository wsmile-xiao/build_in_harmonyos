#!/usr/bin/env python3
"""Conan recipe for cpplint 2.0.2 — Python command-line tool.

cpplint is a pure-Python C++ style checker. It is installed as a
Python module + entry-point script, not compiled from C/C++.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CpplintConan(ConanFile):
    name = "cpplint"
    version = "2.0.2"
    description = "Check C++ files configurably against Google's style guide"
    license = "BSD-3-Clause"
    homepage = "https://github.com/cpplint/cpplint"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # cpplint is a pure Python tool; no build system configuration needed
        pass

    def build(self):
        # Apply patches (even though cpplint has none, this satisfies the recipe check)
        apply_conandata_patches(self)
        # cpplint is a pure Python script; no compilation step needed
        pass

    def package(self):
        # Install cpplint.py as a Python module
        copy(self, "cpplint.py", src=self.source_folder, dst=os.path.join(self.package_folder, "lib", "python3", "site-packages"))
        # Install the entry-point script
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        script_path = os.path.join(bin_dir, "cpplint")
        script_content = (
            "#!/usr/bin/env python3\n"
            "# -*- coding: utf-8 -*-\n"
            "import re\n"
            "import sys\n"
            "from cpplint import main\n"
            "if __name__ == '__main__':\n"
            "    sys.argv[0] = re.sub(r'(-script\\.pyw|\\.exe)?$', '', sys.argv[0])\n"
            "    sys.exit(main())\n"
        )
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

    def package_info(self):
        # cpplint is a command-line tool, not a library
        # Set cpp_info.libs to empty — no C/C++ library to link
        self.cpp_info.libs = []
        # Provide the bin directory for the cpplint command
        self.cpp_info.bindirs = ["bin"]
        # Add Python path to help find the module
        self.cpp_info.libdirs = ["lib/python3/site-packages"]
