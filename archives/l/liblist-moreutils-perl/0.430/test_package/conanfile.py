import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # List::MoreUtils 依赖 Exporter::Tiny（perl -I 需含依赖的
            # lib/perl5——实测 'Can't locate Exporter/Tiny.pm'）——PERL5LIB
            # 遍历所有依赖的 lib/perl5
            perl5_dirs = []
            for dep_name, dep in self.dependencies.items():
                p = os.path.join(dep.package_folder, "lib", "perl5")
                if os.path.isdir(p):
                    perl5_dirs.append(p)
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_list_moreutils_perl.py")
            env = f'PERL5LIB="{os.pathsep.join(perl5_dirs)}"'
            self.run(f'{env} {sys.executable} "{test_script}" '
                     f'"{self.dependencies["liblist-moreutils-perl"].package_folder}"',
                     env="conanrun")
