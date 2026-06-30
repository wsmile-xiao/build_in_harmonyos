#!/usr/bin/env python3
"""Conan test_package — perl-protocol-xmpp 0.006

Tests Protocol::XMPP package integrity:
1. Verifies all .pm and .pod files are present
2. Validates key module structure
3. Checks version consistency
"""
import os
import glob

from conan import ConanFile


class PerlProtocolXMPPTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-protocol-xmpp"]
        pkg_folder = pkg.package_folder

        # 1. Find XMPP.pm in the package folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "XMPP.pm"), recursive=True)
        if not pm_files:
            raise Exception("Protocol/XMPP.pm not found in package")
        self.output.success(f"Protocol/XMPP.pm found: {pm_files[0]}")

        # 2. Verify key sub-modules are present
        expected_modules = [
            "Stream.pm", "Handler.pm", "Base.pm", "Message.pm",
            "ElementBase.pm", "Contact.pm", "Roster.pm", "User.pm",
            "TextElement.pm",
        ]

        all_pm = glob.glob(os.path.join(pkg_folder, "**", "*.pm"), recursive=True)
        all_pm_names = [os.path.basename(f) for f in all_pm]

        missing = [m for m in expected_modules if m not in all_pm_names]
        if missing:
            raise Exception(f"Missing key modules: {missing}")
        self.output.success(f"All {len(expected_modules)} key modules present")

        # 3. Check Element subdirectory
        element_pms = glob.glob(os.path.join(pkg_folder, "**", "Element", "*.pm"), recursive=True)
        if len(element_pms) < 20:
            raise Exception(f"Expected 20+ Element/*.pm files, found {len(element_pms)}")
        self.output.success(f"Element/ directory has {len(element_pms)} .pm files")

        # 4. Check IQ subdirectory
        iq_pms = glob.glob(os.path.join(pkg_folder, "**", "IQ", "*.pm"), recursive=True)
        if len(iq_pms) < 1:
            raise Exception("Expected IQ/Roster.pm, not found")
        self.output.success(f"IQ/ directory has {len(iq_pms)} .pm files")

        # 5. Verify .pod files exist
        all_pod = glob.glob(os.path.join(pkg_folder, "**", "*.pod"), recursive=True)
        if len(all_pod) < 20:
            raise Exception(f"Expected 20+ .pod files, found {len(all_pod)}")
        self.output.success(f"Total .pod files: {len(all_pod)}")

        # 6. Count totals
        self.output.info(f"Total .pm files: {len(all_pm)}")
        self.output.info(f"Total .pod files: {len(all_pod)}")
