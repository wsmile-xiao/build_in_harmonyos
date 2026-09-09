import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class NetsurfBuildsystemConan(ConanFile):
    name = "netsurf-buildsystem"
    version = "1.10"
    version = "1.10"
    description = "NetSurf shared makefile build system"
    license = "MIT"
    homepage = "https://www.netsurf-browser.org/"
    url = "https://git.netsurf-browser.org/buildsystem.git/"
    topics = ("netsurf", "build-system", "make")
    package_type = "build-scripts"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # The release declares a real test target even though it is intentionally
        # a no-op; running it keeps the upstream entry point in the build record.
        self.run(f'make -C "{self.source_folder}" test')

    def package(self):
        shared = os.path.join(self.package_folder, "share", "netsurf-buildsystem")
        source = self.source_folder
        for subdir in ("makefiles", "testtools", "citools"):
            copy(self, "*", src=os.path.join(source, subdir),
                 dst=os.path.join(shared, subdir))
        copy(self, "COPYING", src=source,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src=source,
             dst=os.path.join(self.package_folder, "share", "doc",
                              "netsurf-buildsystem"))

        # Keep the script modes required by downstream make/test invocations.
        if os.name == "posix":
            for relative in (
                "testtools/testrunner.pl",
                "citools/jenkins-build.sh",
            ):
                path = os.path.join(shared, relative)
                os.chmod(path, os.stat(path).st_mode | 0o111)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        shared = os.path.join(self.package_folder, "share",
                              "netsurf-buildsystem")
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.builddirs = ["share/netsurf-buildsystem"]
        self.buildenv_info.define_path("NSSHARED", shared)
        self.runenv_info.define_path("NSSHARED", shared)
