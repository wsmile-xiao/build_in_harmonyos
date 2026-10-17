import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, copy, get, replace_in_file, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GlobusCommonConan(ConanFile):
    name = "globus-common"
    version = "18.15"
    package_type = "library"
    license = "Apache-2.0"
    homepage = "https://github.com/gridcf/gct"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )

    @staticmethod
    def _ohos_triplet(arch):
        triplet = {
            "armv8": "aarch64-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }.get(str(arch))
        if triplet is None:
            raise ConanInvalidConfiguration("Unsupported OHOS architecture")
        return triplet

    @staticmethod
    def _build_triplet(arch):
        triplet = {
            "armv8": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }.get(str(arch))
        if triplet is None:
            raise ConanInvalidConfiguration("Unsupported build architecture")
        return triplet

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Keep build and host distinct.  The CI worker can execute its GNU
            # ABI tools but cannot run binaries linked for the OHOS target.
            # Using the OHOS triplet for both makes Autoconf treat this as a
            # native build and fail while probing a compiled target program.
            tc.configure_args.extend(
                [
                    "--build={}".format(
                        self._build_triplet(self.settings_build.arch)
                    ),
                    "--host={}".format(self._ohos_triplet(self.settings.arch)),
                ]
            )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "GLOBUS_LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = [lib for lib in libs if lib == "globus_common"] or ["globus_common"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "GlobusCommon")
        self.cpp_info.set_property("cmake_target_name", "Globus::Common")
        self.cpp_info.set_property("pkg_config_name", "globus-common")
        if str(self.settings.os) in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs.extend(["pthread", "dl"])
