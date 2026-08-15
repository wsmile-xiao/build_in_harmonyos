import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class BragConan(ConanFile):
    name = "brag"
    version = "1.4.3"
    description = "Collect and assemble multipart binary attachments from newsgroups"
    license = "GPL-2.0-or-later"
    homepage = "https://brag.sourceforge.net/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "brag recipe currently supports Linux and OHOS only"
            )

    def requirements(self):
        self.requires("tcl/8.6.14", run=True)
        self.requires("uudeview/0.5.20", run=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        # brag is a pure Tcl script, no compilation needed
        apply_conandata_patches(self)

    def package(self):
        # Copy brag executable script
        copy(self, "brag", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # Ensure executable and fix tclsh reference (tcl 8.6 provides tclsh8.6)
        brag_bin = os.path.join(self.package_folder, "bin", "brag")
        if os.path.isfile(brag_bin):
            os.chmod(brag_bin, 0o755)
            with open(brag_bin, "r") as f:
                content = f.read()
            content = content.replace("exec tclsh", "exec tclsh8.6")
            with open(brag_bin, "w") as f:
                f.write(content)

        # Copy man page
        copy(self, "brag.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

        # Copy documentation
        for doc_file in ("CHANGES", "LICENSE", "README"):
            copy(self, doc_file, src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "brag"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
