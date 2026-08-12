import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GettextConan(ConanFile):
    name = "gettext"
    version = "0.22.5"
    description = "GNU internationalization runtime library"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gnu.org/software/gettext/"
    url = "https://savannah.gnu.org/projects/gettext"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        staged = os.path.expanduser("~/gettext-0.22.5.tar.gz")
        source = self.conan_data["sources"]
        if os.path.isfile(staged):
            source = {"url": f"file://{staged}", "sha256": source["sha256"]}
        get(self, **source, strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # gettext-runtime/configure 在交叉编译 + musl target 下用 -fPIC 链接
            # 检测程序会失败（C compiler works... no）。禁用 fPIC 避免该检测失败。
            toolchain.fpic = False
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-musl",
                    "--host=aarch64-unknown-linux-musl",
                ]
            )
        toolchain.configure_args.extend(
            [
                "--enable-static",
                "--disable-shared",
                "--disable-java",
                "--disable-c++",
                "--disable-openmp",
                "--without-emacs",
            ]
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        temp = os.path.join(self.build_folder, "tmp")
        os.makedirs(temp, exist_ok=True)
        os.environ["TMPDIR"] = temp
        if self.settings.os == "OHOS":
            for root, _, files in os.walk(self.source_folder):
                if "configure" in files:
                    replace_in_file(
                        self,
                        os.path.join(root, "configure"),
                        "umask 077",
                        "umask 022",
                    )
        autotools = Autotools(self)
        autotools.configure()
        if self.settings.os == "OHOS":
            replace_in_file(
                self,
                os.path.join(
                    self.build_folder,
                    "gettext-runtime",
                    "intl",
                    "libtool",
                ),
                '*) my_xabs=`pwd`"/$my_xlib" ;;',
                '*) my_xabs="$PWD/$my_xlib" ;;',
            )
        intl = os.path.join(self.build_folder, "gettext-runtime", "intl")
        self.run("make -j1", cwd=intl)
        self.run("make check -j1", cwd=intl)

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-C", "gettext-runtime/intl"])
        rm(self, "libintl.la", os.path.join(self.package_folder, "lib"))
        rm(self, "locale.alias", os.path.join(self.package_folder, "share", "locale"))
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gettext")
        self.cpp_info.set_property("cmake_target_name", "gettext::libintl")
        self.cpp_info.set_property("pkg_config_name", "libintl")
        self.cpp_info.libs = ["intl"]
        if self.settings.os == "OHOS":
            self.cpp_info.system_libs = ["pthread"]
