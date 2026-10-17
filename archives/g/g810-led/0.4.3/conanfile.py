#!/usr/bin/env python3
"""Conan recipe for g810-led 0.4.3 — Logitech RomerG/GX keyboard LED control (CLI + shared lib).

- Build system: 官方 GNU makefile（无 configure），C++ gnu++11
- 产物: bin/g810-led(CLI) + lib/libg810-led.so.0.4.3(共享库) + 公开头文件
- 依赖: hidapi（默认 hidraw 后端 -> -lhidapi-hidraw）+ 传递依赖 libudev-zero(-ludev)
- OHOS 要点:
  * 官方 makefile 的 CPPFLAGS/LIBS 是条件赋值，环境变量无法注入；CXXFLAGS 的
    `+=` 追加对命令行传入值不生效（会丢 -DVERSION）。因此 CXX 用 Conan conf 注入，
    CPPFLAGS/LDFLAGS/LIBS 全部作为 make 命令行参数传入，CXXFLAGS 不传、
    让 makefile 的 `?=` 默认值与 `+=` 追加（-std=gnu++11 -DVERSION=\"0.4.3\"）生效。
  * 不使用官方 `install`/`setup` 目标（依赖 udevadm/systemctl，OHOS 不可用），
    package() 手工拷贝产物。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class G810LedConan(ConanFile):
    name = "g810-led"
    version = "0.4.3"
    description = "Control the backlight of Logitech RomerG/GX mechanical keyboards (G213/G410/G413/G512/G513/G610/G810/G815/G910/GPro)"
    license = "GPL-3.0-only"
    homepage = "https://github.com/MatMoul/g810-led"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # hidraw 后端（官方 makefile 默认 LIB=hidapi，-lhidapi-hidraw）
        self.requires("hidapi/0.12.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器必须取自 Conan conf。字典型 conf 不能按子键直读
        # （self.conf.get("...:cpp") 会报 does not exist），先取整个 dict。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        hidapi = self.dependencies["hidapi"]
        udev = self.dependencies["libudev-zero"]
        hid_inc = os.path.join(hidapi.package_folder, "include")
        hid_lib = os.path.join(hidapi.package_folder, "lib")
        udev_lib = os.path.join(udev.package_folder, "lib")
        make_cmd = (
            f"make -C {self.source_folder} -j1 "
            f"CXX={cxx} "
            f"CPPFLAGS='-Dhidapi -I{hid_inc}' "
            f"LDFLAGS='-L{hid_lib} -L{udev_lib}' "
            f"LIBS='-lhidapi-hidraw -ludev'"
        )
        self.run(make_cmd)

    def package(self):
        # keep_path=False：官方 makefile 产物自带 bin/、lib/ 前缀，
        # 保留路径会拷成 pkg/bin/bin/、pkg/lib/lib/ 嵌套目录且软链悬空。
        copy(self, "bin/g810-led", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "lib/libg810-led.so.0.4.3", self.source_folder, os.path.join(self.package_folder, "lib"), keep_path=False)
        # 官方 makefile 生成 libg810-led.so -> libg810-led.so.0.4.3 符号链接，
        # conan copy 不保证保留软链，这里显式重建保证 -lg810-led 可链接。
        os.symlink(
            "libg810-led.so.0.4.3",
            os.path.join(self.package_folder, "lib", "libg810-led.so"),
        )
        copy(
            self,
            "*.h",
            os.path.join(self.source_folder, "src", "classes"),
            os.path.join(self.package_folder, "include", "g810-led"),
        )
        copy(
            self,
            "*",
            os.path.join(self.source_folder, "sample_profiles"),
            os.path.join(self.package_folder, "share", "g810-led", "samples"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["g810-led"]
        self.cpp_info.includedirs = ["include"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))