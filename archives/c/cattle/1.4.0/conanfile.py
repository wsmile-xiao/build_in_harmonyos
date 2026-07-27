import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CattleConan(ConanFile):
    name = "cattle"
    version = "1.4.0"
    description = "GObject-based Brainfuck language toolkit"
    license = "GPL-2.0-or-later"
    homepage = "https://kiyuko.org/software/cattle"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("brainfuck", "glib", "gobject", "interpreter")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        self.requires("glib/2.84.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cattle is supported on Linux and OHOS only"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        library_args = (
            ["--enable-shared", "--disable-static"]
            if self.options.shared
            else ["--disable-shared", "--enable-static"]
        )
        tc.configure_args.extend(
            library_args + ["--disable-introspection", "--disable-gtk-doc"]
        )
        if self.settings.os == "OHOS":
            # Cattle 1.4.0 bundles 2018 GNU config scripts, which predate
            # HarmonyOS. The build is native aarch64, so this portable
            # triplet avoids the obsolete config.guess probe.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()
        PkgConfigDeps(self).generate()

    def build(self):
        autotools = Autotools(self)
        glib_pc_dir = os.path.join(
            self.dependencies["glib"].package_folder, "lib", "pkgconfig"
        )
        original_pkg_config_path = os.environ.get("PKG_CONFIG_PATH")
        os.environ["PKG_CONFIG_PATH"] = (
            glib_pc_dir
            if not original_pkg_config_path
            else glib_pc_dir + os.pathsep + original_pkg_config_path
        )
        try:
            autotools.configure(build_script_folder=self.source_folder)
            autotools.make()

            # Upstream's check-local only invokes gtester when it is installed.
            # Run its test programs directly as well, so all five real upstream
            # test executables are verified on the OHOS build host.
            autotools.make(target="check")
            for test_name in ("buffer", "interpreter", "program", "references", "tape"):
                self.run(f'"{self.build_folder}/tests/{test_name}"')
        finally:
            if original_pkg_config_path is None:
                os.environ.pop("PKG_CONFIG_PATH", None)
            else:
                os.environ["PKG_CONFIG_PATH"] = original_pkg_config_path

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", self.source_folder, f"{self.package_folder}/licenses")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cattle")
        self.cpp_info.set_property("cmake_target_name", "cattle::cattle")
        self.cpp_info.set_property("pkg_config_name", "cattle-1.0")
        self.cpp_info.libs = ["cattle-1.0"]
        self.cpp_info.includedirs = ["include/cattle-1.0"]
