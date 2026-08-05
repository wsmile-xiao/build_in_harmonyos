#!/usr/bin/env python3
"""Conan recipe for abi-compliance-checker 2.3 — Perl ABI compliance checker tool.

abi-compliance-checker is a pure Perl tool for analyzing ABI changes
in C/C++ shared libraries. No C/C++ compilation is required.

The tool's Makefile.pl has Perl 5.42 compatibility issues (File::Spec
import and Getopt::Long single-dash options), so equivalent install
steps are performed directly in build().

A wrapper script in bin/ resolves its own path and calls the real
Perl script with a full $0, so getModules() can find the modules
directory (which uses dirname($0) to locate modules).

R32: settings.os must check in ("Linux", "OHOS").
R38: Command-line tool — commands.json declared at software level.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
    copy, load, save,
)
from conan.tools.layout import basic_layout


class AbiComplianceCheckerConan(ConanFile):
    name = "abi-compliance-checker"
    version = "2.3"
    description = "ABI Compliance Checker — analyze ABI changes in C/C++ libraries"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/lvc/abi-compliance-checker"
    url = ""
    package_type = "application"

    settings = "os", "arch"

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
        tool_sname = "abi-compliance-checker"
        script_file = os.path.join(src, f"{tool_sname}.pl")

        # Read script content and replace MODULES_INSTALL_PATH placeholder
        content = load(self, script_file)
        # Use absolute-style path; the wrapper ensures $0 has full path
        content = content.replace("MODULES_INSTALL_PATH",
                                  os.path.join("..", "share", tool_sname))

        # Install layout:
        #   share/abi-compliance-checker/abi-compliance-checker.pl  (real script)
        #   share/abi-compliance-checker/modules/                  (Perl modules)
        #   bin/abi-compliance-checker                            (wrapper)
        install_dir = os.path.join(self.build_folder, "install")
        share_tool_dir = os.path.join(install_dir, "share", tool_sname)
        os.makedirs(share_tool_dir, exist_ok=True)

        # Write the real script
        real_script = os.path.join(share_tool_dir, f"{tool_sname}.pl")
        save(self, real_script, content)
        os.chmod(real_script, 0o755)

        # Copy modules
        modules_src = os.path.join(src, "modules")
        modules_dst = os.path.join(share_tool_dir, "modules")
        if os.path.isdir(modules_src):
            shutil.copytree(modules_src, modules_dst, dirs_exist_ok=True)

        # Create wrapper script in bin/
        bin_dir = os.path.join(install_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, tool_sname)
        wrapper_content = (
            "#!/usr/bin/env bash\n"
            'script_dir="$(cd "$(dirname "$0")" && pwd)"\n'
            f'exec perl "$script_dir/../share/{tool_sname}/{tool_sname}.pl" "$@"\n'
        )
        save(self, wrapper, wrapper_content)
        os.chmod(wrapper, 0o755)

    def package(self):
        install_dir = os.path.join(self.build_folder, "install")

        copy(self, "*", src=os.path.join(install_dir, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*", src=os.path.join(install_dir, "share"),
             dst=os.path.join(self.package_folder, "share"), keep_path=True)

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
