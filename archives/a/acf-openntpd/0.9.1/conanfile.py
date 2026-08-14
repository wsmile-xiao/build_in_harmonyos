
#!/usr/bin/env python3

"""Conan recipe for acf-openntpd 0.9.1."""



import os

import shutil



from conan import ConanFile

from conan.errors import ConanInvalidConfiguration

from conan.tools.files import (

    get,

    copy,

    apply_conandata_patches,

    export_conandata_patches,

)

from conan.tools.layout import basic_layout





class AcfOpenntpdConan(ConanFile):

    name = "acf-openntpd"

    version = "0.9.1"



    description = "Web-based system administration interface for OpenNTPD"

    license = "GPL-2.0-only"

    homepage = "https://gitlab.alpinelinux.org/acf/acf-openntpd"

    url = "https://gitlab.alpinelinux.org/acf/acf-openntpd"



    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"



    def export_sources(self):

        export_conandata_patches(self)



    def requirements(self):

        self.requires("acf-core/0.24.1")



    def validate(self):

        if str(self.settings.os) not in ("Linux", "OHOS"):

            raise ConanInvalidConfiguration(

                f"Unsupported OS: {self.settings.os}"

            )



    def layout(self):

        basic_layout(self)



    def source(self):

        get(

            self,

            **self.conan_data["sources"],

            strip_root=True,

        )



    def build(self):

        apply_conandata_patches(self)



    def package(self):

        appdir = os.path.join(

            self.package_folder,

            "share",

            "acf",

            "app",

            "openntpd",

        )

        os.makedirs(appdir, exist_ok=True)



        for name in sorted(os.listdir(self.source_folder)):

            if not name.startswith("openntpd"):

                continue



            src = os.path.join(self.source_folder, name)

            dst = os.path.join(appdir, name)



            if os.path.islink(src):

                target = os.readlink(src)

                if not os.path.lexists(dst):

                    os.symlink(target, dst)

            elif os.path.isfile(src):

                shutil.copy2(src, dst)



        copy(

            self,

            "README",

            src=self.source_folder,

            dst=os.path.join(self.package_folder, "licenses"),

            keep_path=False,

        )



    def package_info(self):

        self.cpp_info.libs = []

        self.cpp_info.includedirs = []

        self.cpp_info.libdirs = []

        self.cpp_info.bindirs = []

        self.cpp_info.resdirs = ["share/acf"]
