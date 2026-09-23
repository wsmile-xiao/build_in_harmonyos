#!/usr/bin/env python3
"""Conan recipe for tinyusb 0.18.0 on HarmonyOS.

tinyusb is a *source* library: it ships no standalone build system and every
compile-time decision comes from the consumer's tusb_config.h.  Upstream's only
build entry points are the CMake helper `add_tinyusb()` in src/CMakeLists.txt
and src/tinyusb.mk, both of which assume the application has already picked an
MCU family and supplied a real controller driver.

OHOS PC has neither: tinyusb 0.18.0 ships no Linux/OHOS controller backend under
src/portable/ (only the vendor-neutral `template` pair), and OHOS is not one of
the four OSAL ports (FreeRTOS / Mynewt / Zephyr / RT-Thread).  This recipe
therefore compiles against the template ports with CFG_TUSB_MCU=OPT_MCU_NONE and
CFG_TUSB_OS=OPT_OS_NONE, producing a linkable libtinyusb.a.

The two template ports are *not* symmetric, and that decides the shape of the
shipped default config:

    src/portable/template/dcd_template.c:  dcd_init() { return true;  }   // usable no-op
    src/portable/template/hcd_template.c:  hcd_init() { return false; }   // skeleton to fill in

So the device role can be initialized on a bare OHOS build, while the host role
cannot: with CFG_TUH_ENABLED=1, tusb_init() dies on
`TU_ASSERT(hcd_init(rhport, rh_init))` in usbh.c and returns false for the whole
call even though the device stack came up fine.  The packaged tusb_config.h
therefore enables the device stack only (CFG_TUH_ENABLED=0).  The complete source
tree is shipped alongside the archive, so a consumer that implements an HCD for
OHOS (or points CFG_TUSB_MCU at a real MCU port) can recompile from the package.

Upstream unit tests: test/unit-test/ is a Ceedling 0.31.1 project (vendored Ruby
gem under test/unit-test/vendor/ceedling) driving Unity + CMock.  Two of its
four test files -- test_common_func.c and test_fifo.c -- use no CMock mocks, so
they are compiled here against the sources' vendored Unity and actually run.
The other two (device/usbd, device/msc) #include CMock-generated mock_*.h and
cannot be built without the Ruby toolchain.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# Upstream src/CMakeLists.txt add_tinyusb() 的 23 个源文件，外加 2 个
# template 端口文件（上游把它们留给应用自己的 MCU port 提供；OHOS 没有可用的
# 控制器 port，故显式编入 template 版，见 conanfile 顶部说明）。
# class/bth/bth_device.c 与 class/cdc/cdc_rndis_host.c 不在上游 CMake 列表内，
# 与 Conan/CMake 两条构建路径保持一致，本包同样不编。
#
# 列表保持与上游一致，但包内默认 tusb_config.h 只开设备侧，因此下面 src/host/
# 与 *_host.c 这些 TU 在默认配置下都编译成空对象（它们整体被 CFG_TUH_ENABLED
# 包住）。留着是为了让"有 HCD 的使用者"改一个宏就能从包内源码重编出主机栈，
# 也让本列表与上游 add_tinyusb() 逐行对得上。
TINYUSB_SOURCES = [
    # common
    "src/tusb.c",
    "src/common/tusb_fifo.c",
    # device
    "src/device/usbd.c",
    "src/device/usbd_control.c",
    "src/class/audio/audio_device.c",
    "src/class/cdc/cdc_device.c",
    "src/class/dfu/dfu_device.c",
    "src/class/dfu/dfu_rt_device.c",
    "src/class/hid/hid_device.c",
    "src/class/midi/midi_device.c",
    "src/class/msc/msc_device.c",
    "src/class/net/ecm_rndis_device.c",
    "src/class/net/ncm_device.c",
    "src/class/usbtmc/usbtmc_device.c",
    "src/class/vendor/vendor_device.c",
    "src/class/video/video_device.c",
    # host
    "src/host/usbh.c",
    "src/host/hub.c",
    "src/class/cdc/cdc_host.c",
    "src/class/hid/hid_host.c",
    "src/class/msc/msc_host.c",
    "src/class/vendor/vendor_host.c",
    # typec
    "src/typec/usbc.c",
    # OHOS：OPT_MCU_NONE 的 template 端口（上游 CMake 列表不含，由 MCU port 提供）
    "src/portable/template/dcd_template.c",
    "src/portable/template/hcd_template.c",
]

# 上游 Ceedling 用例与它们的 runner（runner 见 files/，见 notes.md 第 5 节）。
# device/usbd 与 device/msc 两个用例文件依赖 CMock 生成的 mock_*.h，无法脱离
# Ceedling/Ruby 构建，故不在此列。
UNITY_TESTS = [
    ("test_common_func", "test/test_common_func.c"),
    ("test_fifo", "test/test_fifo.c"),
]


class TinyusbConan(ConanFile):
    name = "tinyusb"
    version = "0.18.0"
    description = "TinyUSB - an open source cross-platform USB stack for embedded systems"
    license = "MIT"
    homepage = "https://www.tinyusb.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    exports_sources = "files/*"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _toolchain(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar")
        if not ar:
            compiler_dir = os.path.dirname(cc) if os.path.sep in cc else ""
            candidate = os.path.join(compiler_dir, "llvm-ar") if compiler_dir else ""
            ar = candidate if candidate and os.path.isfile(candidate) else "llvm-ar"
        return cc, ar

    def _optimization_flags(self):
        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        return build_type_flags.get(str(self.settings.build_type), "-O2")

    def build(self):
        cc, ar = self._toolchain()
        optimization_flags = self._optimization_flags()

        # files/ 必须先于 src/：tinyusb 的每个 TU 都从 tusb_option.h 里
        # #include "tusb_config.h"，而源码树里没有这个文件（上游把它交给应用
        # 提供）。本包的默认配置就是 files/tusb_config.h。
        config_inc = os.path.join(self.source_folder, "files")
        src_inc = os.path.join(self.source_folder, "src")
        flags = f"{optimization_flags} -fPIC -std=gnu11"
        includes = f'-I"{config_inc}" -I"{src_inc}"'

        objects = []
        for name in TINYUSB_SOURCES:
            obj = os.path.join(
                self.build_folder, name.replace("/", "_").replace(".c", ".o")
            )
            self.run(
                '"{}" {} {} -c "{}" -o "{}"'.format(
                    cc, flags, includes, os.path.join(self.source_folder, name), obj
                )
            )
            objects.append(obj)

        archive = os.path.join(self.build_folder, "libtinyusb.a")
        self.run(
            '"{}" rcs "{}" {}'.format(
                ar, archive, " ".join('"{}"'.format(o) for o in objects)
            )
        )

        self._run_upstream_tests(cc, optimization_flags, flags, includes, archive)

    def _src_include_dirs(self):
        """src/ 及其全部子目录的 -I 列表。

        Ceedling 的 project.yml 写的是 `:source: ../../src/**`，会把 src/ 下每个
        子目录都塞进 include 搜索路径，上游用例因此写 `#include "tusb_fifo.h"`
        而不是 `"common/tusb_fifo.h"`。库自身的 .c 一律写相对 src/ 的全路径，
        用不到这些；只有跑上游用例时需要，故单独成方法。
        """
        src = os.path.join(self.source_folder, "src")
        dirs = {src}
        for dirpath, _dirnames, _filenames in os.walk(src):
            dirs.add(dirpath)
        return " ".join('-I"{}"'.format(d) for d in sorted(dirs))

    def _run_upstream_tests(self, cc, optimization_flags, flags, includes, archive):
        """编译并运行两个无 mock 的上游 Unity 用例。

        上游 test/unit-test 是 Ceedling 工程；Ceedling 会为每个 test_*.c 生成一个
        runner（main），并额外生成 CMock 桩。test_common_func.c 与 test_fifo.c
        不使用任何 mock，所以这里用源码树内自带的 Unity（vendor/ceedling/vendor/
        unity/src）加上 files/ 里两个等价的最小 runner 直接构建，无需 Ruby。
        构建产物只在本阶段使用，不进包。
        """
        unity_dir = os.path.join(
            self.source_folder, "test", "unit-test", "vendor", "ceedling",
            "vendor", "unity", "src",
        )
        unittest_dir = os.path.join(self.source_folder, "test", "unit-test")

        unity_obj = os.path.join(self.build_folder, "unity.o")
        self.run(
            '"{}" {} {} -c "{}" -o "{}"'.format(
                cc, flags, f'-I"{unity_dir}"',
                os.path.join(unity_dir, "unity.c"), unity_obj,
            ),
            env="conanbuild",
        )

        test_includes = f'{includes} {self._src_include_dirs()} -I"{unity_dir}"'
        for name, rel_source in UNITY_TESTS:
            source = os.path.join(unittest_dir, rel_source)
            runner = os.path.join(
                self.source_folder, "files", f"unity_runner_{name}.c"
            )
            binary = os.path.join(self.build_folder, name)
            self.run(
                '"{}" {} {} "{}" "{}" "{}" "{}" -o "{}"'.format(
                    cc, flags, test_includes,
                    source, runner, unity_obj, archive, binary,
                ),
                env="conanbuild",
            )
            if can_run(self):
                # Unity 的 runner 以失败用例数作为进程退出码：0 表示全绿。
                self.run('"{}"'.format(binary), env="conanrun")
                self.output.info(f"upstream {name} passed")
            else:
                self.output.info(
                    f"upstream {name} skipped: cannot run target binaries on the "
                    "build host (cross build)"
                )

        self.output.info(
            "upstream device/usbd + device/msc excluded: they #include "
            "CMock-generated mock_dcd.h / mock_msc_device.h, which requires the "
            "Ceedling 0.31.1 Ruby toolchain (no Ruby on the OHOS build worker)"
        )
        self.output.info(
            "upstream test/fuzz (libFuzzer harnesses) and test/hil (Python, "
            "needs a physical USB device) excluded: neither can run on the "
            "OHOS CI worker"
        )

    def package(self):
        # tinyusb 是源码库：头文件之间是相对包含（"common/tusb_common.h" 等），
        # 因此整棵 src/ 树都要进 include/，消费侧只需 -I<package>/include。
        # 一并发运 .c 源文件，让有真实控制器 port 的使用者能用自己的
        # tusb_config.h 重新编译。
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "tusb_config.h",
            src=os.path.join(self.source_folder, "files"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libtinyusb.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["tinyusb"]
        self.cpp_info.set_property("cmake_file_name", "tinyusb")
        self.cpp_info.set_property("cmake_target_name", "tinyusb::tinyusb")
        self.cpp_info.set_property("pkg_config_name", "tinyusb")
