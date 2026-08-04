import os
import shutil
import sys

from conan import ConanFile


class P5IoCompressLzmaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        perl_lib = os.path.join(package_folder, "lib", "perl5")
        script = os.path.join(self.recipe_folder, "test_p5_io_compress_lzma.py")
        self.run(f'"{sys.executable}" "{script}" "{package_folder}" "{perl_lib}"', env="conanrun")

        upstream_root = os.path.join(self.build_folder, "upstream")
        if os.path.isdir(upstream_root):
            shutil.rmtree(upstream_root)
        shutil.copytree(perl_lib, os.path.join(upstream_root, "lib"))
        shutil.copytree(
            os.path.join(package_folder, "share", "p5-io-compress-lzma", "t"),
            os.path.join(upstream_root, "t"),
        )
        shutil.copytree(
            os.path.join(package_folder, "share", "p5-io-compress-lzma", "examples"),
            os.path.join(upstream_root, "examples"),
        )

        ordered_libs = [
            os.path.join(package_folder, "lib", "perl5"),
            os.path.join(self.dependencies["p5-io-compress"].package_folder, "lib", "perl5"),
            os.path.join(self.dependencies["p5-compress-raw-lzma"].package_folder, "lib", "perl5"),
            os.path.join(self.dependencies["p5-compress-raw-bzip2"].package_folder, "lib", "perl5"),
        ]
        perl5lib = ":".join(ordered_libs)
        perl_bin = os.path.join(self.dependencies["perl"].package_folder, "bin", "perl")
        prove = os.path.join(self.dependencies["perl"].package_folder, "bin", "prove")
        self.run(f'PERL5LIB="{perl5lib}:$PERL5LIB" "{perl_bin}" "{prove}" -lr t', cwd=upstream_root, env="conanrun")
