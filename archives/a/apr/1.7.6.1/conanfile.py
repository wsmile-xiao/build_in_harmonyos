import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AprConan(ConanFile):
    name = "apr"
    version = "1.7.6.1"
    description = "Apache Portable Runtime"
    license = "Apache-2.0"
    homepage = "https://apr.apache.org/"
    url = "https://github.com/apache/apr"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("APR recipe is currently validated for OHOS only")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("APR recipe is currently validated for OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend([
            "--enable-static" if not self.options.shared else "--disable-static",
            "--enable-shared" if self.options.shared else "--disable-shared",
        ])
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            configure = os.path.join(self.source_folder, "configure")
            args = [
                f"--prefix={self.package_folder}",
                "--enable-static" if not self.options.shared else "--disable-static",
                "--enable-shared" if self.options.shared else "--disable-shared",
                "--build=aarch64-unknown-linux-ohos",
            ]
            scripts = [
                "build/mkdir.sh",
                "build/get-version.sh",
                "build/ltmain.sh",
                "build/install.sh",
                "build/buildcheck.sh",
                "build/config.guess",
                "build/PrintPath",
            ]
            script_list = " ".join(f'"{os.path.join(self.source_folder, item)}"' for item in scripts)
            self.run(
                f"sed -i '1d' {script_list}",
                cwd=self.source_folder,
                env="conanbuild",
            )
            with open(configure, "r", encoding="utf-8") as handle:
                configure_content = handle.read()
            configure_content = configure_content.replace(
                'get_version="$apr_builders/get-version.sh"',
                f'get_version="{shell} $apr_builders/get-version.sh"',
            ).replace(
                'mkdir_p="$apr_builders/mkdir.sh"',
                f'mkdir_p="{shell} $apr_builders/mkdir.sh"',
            )
            with open(configure, "w", encoding="utf-8") as handle:
                handle.write(configure_content)
            self.run(
                f'"{shell}" "{configure}" ' + " ".join(args),
                cwd=self.build_folder,
                env="conanbuild",
            )
            self.run(f'make -j2 SHELL="{shell}"', cwd=self.build_folder, env="conanbuild")
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        if self.settings.os == "OHOS":
            shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'make install SHELL="{shell}"', cwd=self.build_folder, env="conanbuild")
        else:
            Autotools(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["apr-1"]
        # APR installs public headers directly below the package include root.
        self.cpp_info.includedirs = ["include", "include/apr-1"]
        self.cpp_info.set_property("cmake_file_name", "apr")
        self.cpp_info.set_property("cmake_target_name", "apr::apr")
        self.cpp_info.set_property("pkg_config_name", "apr-1")
