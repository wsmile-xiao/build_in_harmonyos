import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class Abcm2psConan(ConanFile):
    name = "abcm2ps"
    version = "8.14.15"
    description = "ABC music notation to PostScript and SVG converter"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/lewdlime/abcm2ps"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "abcm2ps/c currently supports only OHOS armv8"
            )

        config_shell = os.environ.get("CONFIG_SHELL", "bash")
        prefix = self.package_folder.replace("\\", "/")
        src = self.source_folder.replace("\\", "/")
        # Upstream configure defaults to gcc; the OHOS sysroot only ships clang.
        # Export CC/CXX so configure + make pick clang without probing gcc.
        cc_env = os.environ.get("CC", "clang")
        cxx_env = os.environ.get("CXX", "clang++")
        self.run(
            f"cd '{src}' && CC={cc_env} CXX={cxx_env} {config_shell} ./configure --prefix={prefix}",
            env="conanbuild",
        )
        self.run(f"cd '{src}' && CC={cc_env} CXX={cxx_env} make -j1", env="conanbuild")
        self.run(f"cd '{src}' && make test", env="conanbuild")
        # Upstream Makefile hard-calls /usr/bin/install; the OHOS sysroot has no
        # standalone install binary, and the INSTALL env var is not read by the
        # generated Makefile. Install the binary manually with shutil so the
        # package step does not depend on /usr/bin/install.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy(
            os.path.join(src, "abcm2ps"),
            os.path.join(bin_dir, "abcm2ps"),
        )
        # Preserve the mode (configure + make produced an executable).
        shutil.copymode(os.path.join(src, "abcm2ps"), os.path.join(bin_dir, "abcm2ps"))

    def package_info(self):
        self.buildenv_info.define_path("PATH", os.path.join(self.package_folder, "bin"))
