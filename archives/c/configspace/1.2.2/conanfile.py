import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, get


class ConfigSpaceConan(ConanFile):
    name = "configspace"
    version = "1.2.2"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/automl/ConfigSpace"
    description = "Creation and manipulation of parameter configuration spaces"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        source = dict(self.conan_data["sources"])
        local_archive = os.environ.get("CONFIGSPACE_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve()
            if not archive.is_file():
                raise FileNotFoundError("CONFIGSPACE_SOURCE_ARCHIVE not found: %s" % archive)
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def export_sources(self):
        # Keep the recipe self-contained when the archive has no local patches.
        pass

    def build(self):
        apply_conandata_patches(self)
        self.output.info("ConfigSpace is pure Python; no compilation step is required")

    def package(self):
        site = os.path.join(self.package_folder, "python", "site-packages")
        copy(self, "ConfigSpace/**", src=os.path.join(self.source_folder, "src"), dst=site)
        Path(site, ".configspace-conan-package").write_text("configspace/1.2.2\n", encoding="utf-8")
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        site = os.path.join(self.package_folder, "python", "site-packages")
        self.cpp_info.libs = []
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.runenv_info.append_path("PYTHONPATH", site)
