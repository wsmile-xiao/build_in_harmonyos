
#!/usr/bin/env python3

"""Conan test_package for acf-openntpd 0.9.1."""



import os

import shutil



from conan import ConanFile





class AcfOpenntpdTestConan(ConanFile):

    settings = "os", "compiler", "build_type", "arch"



    def requirements(self):

        self.requires(self.tested_reference_str)



    def test(self):

        pkg_folder = self.dependencies["acf-openntpd"].package_folder



        bash = (

            os.environ.get("CONFIG_SHELL")

            or shutil.which("bash")

            or "/data/service/hnp/bin/bash"

        )



        script = os.path.join(

            self.source_folder,

            "test_openntpd.sh",

        )



        self.run(

            f'"{bash}" "{script}" "{pkg_folder}"',

            env="conanrun",

        )
