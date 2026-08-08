#!/usr/bin/env python3
"""Conan recipe for abi-compliance-checker 2.3 — ABI compliance checking tool.

abi-compliance-checker is a Perl script tool for checking backward binary and
source-level compatibility of C/C++ software libraries. No compilation needed.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AbiComplianceConan(ConanFile):
    name = "abi-compliance"
    version = "2.3"
    description = "ABI Compliance Checker — tool for checking backward binary and source-level compatibility of C/C++ libraries"
    license = "LGPL-2.1-or-later"
    homepage = "https://lvc.github.io/abi-compliance-checker/"
    url = "https://github.com/lvc/abi-compliance-checker"
    package_type = "application"

    settings = "os", "arch"

    exports_sources = []

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # abi-compliance-checker is a Perl script — needs Perl runtime
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # No compilation needed — Perl script tool
        self.output.info("No compilation needed: Perl script tool")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        bindir = os.path.join(pkg, "bin")
        # NOTE: getModules() in abi-compliance-checker.pl searches
        # `../share/abi-compliance-checker/modules` (with -checker suffix).
        sharedir = os.path.join(pkg, "share", "abi-compliance-checker")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(sharedir, exist_ok=True)

        # Install main script
        main_script = os.path.join(src, "abi-compliance-checker.pl")
        if not os.path.isfile(main_script):
            raise ConanException(f"Main script not found: {main_script}")
        dest = os.path.join(bindir, "abi-compliance-checker")
        shutil.copy2(main_script, dest)
        os.chmod(dest, 0o755)
        # Fix shebang: #!/usr/bin/perl does not exist on OHOS;
        # resolve perl via PATH (conan package provides it).
        with open(dest, "r") as f:
            content = f.read()
        if content.startswith("#!/usr/bin/perl"):
            content = content.replace("#!/usr/bin/perl", "#!/usr/bin/env perl", 1)
            with open(dest, "w") as f:
                f.write(content)

        # Install modules
        modules_src = os.path.join(src, "modules")
        modules_dst = os.path.join(sharedir, "modules")
        if not os.path.isdir(modules_src):
            raise ConanException(f"Modules directory not found: {modules_src}")
        shutil.copytree(modules_src, modules_dst, dirs_exist_ok=True)

        # Install documentation
        doc_src = os.path.join(src, "doc")
        doc_dst = os.path.join(sharedir, "doc")
        if os.path.isdir(doc_src):
            shutil.copytree(doc_src, doc_dst, dirs_exist_ok=True)

        # Install LICENSE
        license_src = os.path.join(src, "LICENSE")
        if os.path.isfile(license_src):
            shutil.copy2(license_src, os.path.join(sharedir, "LICENSE"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []