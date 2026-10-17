#!/usr/bin/env python3
"""Conan recipe for KiCad project and worksheet templates 10.0.5."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class KicadLibraryTemplatesConan(ConanFile):
    name = "kicad-library-templates"
    version = "10.0.5"
    description = "Official KiCad project and worksheet templates"
    license = "CC-BY-SA-4.0"
    homepage = "https://gitlab.com/kicad/libraries/kicad-templates"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"

    _resource_dir = os.path.join("share", "kicad", "template")
    _expected_project_dirs = {
        "API_Series-500",
        "Arduino_Mega",
        "Arduino_Micro",
        "Arduino_Nano",
        "Arduino_Pro_Mini",
        "Arduino_Uno",
        "BeagleBone-Black-Cape",
        "Edgeberry_Cartridge",
        "EuroCard160mmX100mm",
        "Hammond_1593K_Enclosure",
        "KiCad_MR_diagrams_large_parts",
        "KiCad_MR_diagrams_small_parts",
        "RaspberryPi-HAT",
        "RaspberryPi-uHAT",
        "STM32_Nucleo-64_Morpho",
        "STM32H7_DevEBox",
        "TI-LaunchPad-BoosterPack-20pin",
        "TI-LaunchPad-BoosterPack-40pin",
        "stm32f100-discovery-shield",
    }
    _expected_source_files = 184
    _expected_resource_files = 177
    _expected_resource_extensions = {
        ".FCStd": 1,
        ".html": 19,
        ".jpg": 1,
        ".kicad_mod": 9,
        ".kicad_pcb": 19,
        ".kicad_prl": 2,
        ".kicad_pro": 19,
        ".kicad_sch": 19,
        ".kicad_sym": 1,
        ".kicad_wks": 36,
        ".pdf": 2,
        ".png": 39,
        ".step": 1,
        ".svg": 2,
        "": 7,
    }

    def export_sources(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        source_root = self.source_folder
        projects_root = os.path.join(source_root, "Projects")
        worksheets_root = os.path.join(source_root, "Worksheets")
        if not os.path.isdir(projects_root) or not os.path.isdir(worksheets_root):
            raise ConanInvalidConfiguration(
                "kicad-library-templates 10.0.5: missing Projects or Worksheets"
            )

        source_files = []
        for source_dir in (".github", "CMakeModules", "Projects", "Worksheets"):
            source_path = os.path.join(source_root, source_dir)
            source_files.extend(
                os.path.join(root, filename)
                for root, _, files in os.walk(source_path)
                for filename in files
            )
        source_files.extend(
            os.path.join(source_root, filename)
            for filename in (".gitignore", "CMakeLists.txt", "LICENSE.md", "README.md")
            if os.path.isfile(os.path.join(source_root, filename))
        )
        if len(source_files) != self._expected_source_files:
            raise ConanInvalidConfiguration(
                "kicad-library-templates 10.0.5 source inventory drift: "
                f"expected {self._expected_source_files}, got {len(source_files)}"
            )

        actual_projects = {
            entry for entry in os.listdir(projects_root)
            if os.path.isdir(os.path.join(projects_root, entry))
        }
        if actual_projects != self._expected_project_dirs:
            missing = sorted(self._expected_project_dirs - actual_projects)
            extra = sorted(actual_projects - self._expected_project_dirs)
            raise ConanInvalidConfiguration(
                "kicad-library-templates project inventory drift: "
                f"missing={missing}, extra={extra}"
            )

        resource_roots = (projects_root, worksheets_root)
        resource_files = [
            os.path.join(root, filename)
            for resource_root in resource_roots
            for root, _, files in os.walk(resource_root)
            for filename in files
        ]
        if len(resource_files) != self._expected_resource_files:
            raise ConanInvalidConfiguration(
                "kicad-library-templates resource inventory drift: "
                f"expected {self._expected_resource_files}, got {len(resource_files)}"
            )

        extension_counts = {}
        for path in resource_files:
            extension = os.path.splitext(path)[1]
            extension_counts[extension] = extension_counts.get(extension, 0) + 1
        if extension_counts != self._expected_resource_extensions:
            raise ConanInvalidConfiguration(
                "kicad-library-templates extension inventory drift: "
                f"expected {self._expected_resource_extensions}, "
                f"got {extension_counts}"
            )

    def package(self):
        projects_root = os.path.join(self.source_folder, "Projects")
        worksheets_root = os.path.join(self.source_folder, "Worksheets")
        resource_root = os.path.join(self.package_folder, self._resource_dir)
        copy(self, "*", src=projects_root,
             dst=os.path.join(resource_root, "Projects"), keep_path=True)
        copy(self, "*.kicad_wks", src=worksheets_root,
             dst=resource_root, keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.runenv_info.define_path(
            "KICAD_TEMPLATE_DIR", os.path.join(self.package_folder, self._resource_dir)
        )

    def package_id(self):
        self.info.clear()
