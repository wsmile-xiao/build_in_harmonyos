import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class AggregateConan(ConanFile):
    name = "aggregate"
    version = "1.6"
    description = "IPv4 CIDR prefix aggregation tool"
    license = "ISC"
    homepage = "https://ftp.isc.org/isc/aggregate/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "aggregate/1.6 currently supports only OHOS armv8"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        # basic_layout separates source_folder and build_folder; Autotools
        # keeps running ./configure from build_folder where it is absent, and
        # the build_script_folder kwarg is not honored on this conan 2 release.
        # Mirror the abcm2ps precedent: cd into source_folder for each command.
        # get(strip_root=True) unpacks the tarball one level down, so the
        # upstream configure lives under <build root>/aggregate-<version>/.
        # During build, self.build_folder resolves to .../b/build-release (the
        # basic_layout build_type subdir), so step up one level to reach the
        # real build root where strip_root dropped the aggregate-<version> dir.
        build_root = os.path.dirname(self.build_folder)
        src = os.path.join(build_root, f"aggregate-{self.version}")
        prefix = self.package_folder.replace("\\", "/")
        config_shell = os.environ.get("CONFIG_SHELL", "bash")
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        self.run(
            f"cd '{src}' && CC={cc} CXX={cxx} {config_shell} ./configure --prefix={prefix}",
            env="conanbuild",
        )
        self.run(f"cd '{src}' && CC={cc} CXX={cxx} make -j1", env="conanbuild")

    def package(self):
        # Built binaries live where make ran: build_root/aggregate-<version>/,
        # not build_folder (which resolves to the build-release subdir) nor
        # source_folder (which points at the recipe folder during package()).
        build_root = os.path.dirname(self.build_folder)
        src = os.path.join(build_root, f"aggregate-{self.version}")
        copy(self, "aggregate", src=src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "aggregate-ios", src=src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
