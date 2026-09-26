import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JdayConan(ConanFile):
    name = "jday"
    version = "2.4"
    description = (
        "Julian date calculator: jday/j2d/dbd command line tools plus libjday, "
        "a library converting between calendar dates and Julian dates"
    )
    license = "BSD-3-Clause"
    homepage = "https://jday.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("julian-date", "calendar", "date-conversion", "command-line")

    # 固定静态：上游 configure.ac 自注 "default will be to build static library
    # since it is so tiny"，随包 libtool 1.5.6 也没有 linux-ohos 的共享库规则。
    # 因此不提供 shared 选项，package_type 直接声明为 static-library。
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jday/2.4 only supports Linux and OHOS (POSIX time/termios APIs)"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 上游 configure.ac 注释："default will be to build static library since
        # it is so tiny"。随包的 libtool 1.5.6 (2004) 也没有 linux-ohos 的共享库
        # 规则，因此固定为静态库形态。
        tc.configure_args.extend(["--enable-static", "--disable-shared"])
        if str(self.settings.os) == "OHOS":
            if str(self.settings.arch) != "armv8":
                raise ConanInvalidConfiguration(
                    "jday/2.4 on OHOS currently supports armv8 only"
                )
            # profile 的 host/build 同为 OHOS，conan 不认为是交叉编译，
            # 因此不会自动注入三元组。显式给出 --host，配合
            # patches/0002-config.sub.patch 让 2004 年的 config.sub 接受
            # linux-ohos；build 三元组交由已打补丁的 config.guess 探测，
            # 从而在 x86 交叉构建机与 aarch64 原生构建机上行为一致。
            tc.configure_args.append("--host=aarch64-linux-ohos")
        tc.generate()

        # E074/E525: HMDFS 不支持 mkfifo，GNU Make 的 FIFO jobserver 会以
        # "jobserver mkfifo: Operation not permitted" 失败并放弃读取 Makefile。
        # 用 MAKEFLAGS 串行化，连嵌套 make 一起覆盖。
        env = Environment()
        env.define("MAKEFLAGS", "-j1")
        env.vars(self).save_script("conan_make_serial")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        Autotools(self).install(args=["-j1"])
        # libtool 存根文件对 Conan 消费者无用，且会把构建机路径带进包里
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["jday"]
        # 包内同时交付 jday / j2d / dbd 三个命令行工具，显式声明 bindirs
        # 与软件级 commands.json（R38）对应。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "jday")
