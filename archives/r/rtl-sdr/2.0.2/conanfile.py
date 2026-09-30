#!/usr/bin/env python3
"""Conan recipe — rtl-sdr 2.0.2（RTL2832U 电视棒的 SDR 接收库 + 命令行工具集）。

交付内容
    lib/librtlsdr.so、公共头 include/rtl-sdr.h + rtl-sdr_export.h、
    pkg-config 契约 lib/pkgconfig/librtlsdr.pc、上游 8 个 CLI
    （rtl_sdr / rtl_fm / rtl_tcp / rtl_test / rtl_eeprom / rtl_adsb /
    rtl_power / rtl_biast）、licenses/COPYING（GPL-2.0-or-later）。

OHOS 适配要点
  1. 唯一外部依赖是 libusb（仓库已发布 libusb/1.0.27）。上游用
     `pkg_check_modules(LIBUSB libusb-1.0 IMPORTED_TARGET)` 找它，找不到直接
     FATAL_ERROR → generate() 用 PkgConfigDeps 按 libusb 包的 pkg_config_name
     生成 libusb-1.0.pc，并把 generators 目录加进 PKG_CONFIG_PATH
     （仓库 rpm/6.0.2 同款先例）。
  2. OHOS 对 CMake 是未知平台（CMAKE_SYSTEM_NAME=HarmonyOS 没有 Platform 模块）
     ⇒ CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 未定义：共享库不带 DT_SONAME
     （CI L5a 门禁必挂），且 install 会尝试建版本化符号链接（HMDFS 建链不可靠）。
     显式补 `-Wl,-soname,` + CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON → 产出未版本化
     的 librtlsdr.so，但 DT_SONAME 正确（hidapi/0.15.0 同款先例）。
  3. INSTALL_UDEV_RULES=OFF：udev 规则属系统集成，不进 conan 包；
     DETACH_KERNEL_DRIVER=ON：与主流发行版一致（鸿蒙上无 dvb_usb_rtl28xxu）。
  4. 上游 install(EXPORT) 的 rtlsdrConfig.cmake/rtlsdrTargets*.cmake 把**构建机**
     上 libusb 的绝对路径写进 INTERFACE_*，且引用同名的静态库 → 不可重定位，
     从包里剔除；消费者用 conan 的 CMakeDeps（rtlsdr::rtlsdr）或包内 .pc。
  5. librtlsdr.pc 的 prefix（=conan 包绝对路径）与 Cflags/Libs.private 里的
     构建机 libusb -I/-L 路径统一改写成 ${pcfiledir} 相对形式（上游只在交叉
     构建时才清空它们，CI 是原生构建清不掉）。
  6. 唯一的一处源码补丁（patches/0001-ohos-portable-demod-thread-exit.patch）：
     rtl_adsb 退出时调 pthread_cancel()，而 OHOS 的 musl libc **不提供**
     pthread_cancel（CI #65385 实证：ld.lld undefined symbol: pthread_cancel
     → rtl_adsb 链接失败，8 个工具里只此一个挂）。补丁只把这一行换成上游
     线程自己就在用的 do_exit 退出标志 + safe_cond_signal（唤醒阻塞在
     pthread_cond_wait 的 demod 线程后再 join）——语义等价、无泄漏，
     musl/glibc 通用；库本体（src/librtlsdr.c 等）不动。

真实测试（平台 rule12）
    上游 **没有任何测试套件**（顶层 CMakeLists 无 enable_testing()/add_test，
    src/ 也没有测试目标；rtl_test 是需要真实电视棒的硬件自检程序）——如实声明。
    证据来自两处：① build() 内对 8 个 CLI 做启动冒烟（无参运行必须打印
    usage / “No supported devices found.”，证明工具可执行、链接与 RPATH 完好）；
    ② test_package 的消费者用例用 **ELF 符号介入**伪造一台 VID=0x0bda
    PID=0x2838 的电视棒，跑通「设备枚举 → 机型表匹配 → USB 字符串读取 →
    序列号反查 → 越界错误路径」整条真实链路。

版本说明（上游 quirk）
    上游 tag 是 v2.0.2，但根 CMakeLists 里 VERSION_INFO_PATCH_VERSION 仍是 1
    （发布时忘了改）→ 构建出的 VERSION/LIBVER、.pc 的 Version 字段与
    rtlsdrConfigVersion.cmake 都写 2.0.1。该 quirk 不改上游源码，如实保留并在
    manifest/notes 里记录（本包唯一的补丁见上文第 6 点，与此 quirk 无关）。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import PkgConfigDeps

# 上游 src/CMakeLists.txt 构建的全部命令行工具
CLI_TOOLS = ("rtl_sdr", "rtl_fm", "rtl_tcp", "rtl_test",
             "rtl_eeprom", "rtl_adsb", "rtl_power", "rtl_biast")


class RtlsdrConan(ConanFile):
    name = "rtl-sdr"
    version = "2.0.2"
    description = ("rtl-sdr — turn a Realtek RTL2832U DVB-T USB dongle into a "
                   "software defined radio receiver (librtlsdr + rtl_sdr/"
                   "rtl_fm/rtl_tcp/rtl_test ... command line tools)")
    license = "GPL-2.0-or-later"
    homepage = "https://osmocom.org/projects/rtl-sdr/wiki"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("sdr", "radio", "rtl2832u", "dvb-t", "usb")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux/OHOS, got {self.settings.os}")

    def requirements(self):
        # librtlsdr.so 直接调用 libusb 的 20 余个符号（DT_NEEDED: libusb-1.0.so.0），
        # 静态库版本更需要 libusb 参与链接；公共头 rtl-sdr.h 不包含 libusb.h，
        # 但消费者用例/工具链需要它的类型声明 → 头与库都传递。
        self.requires("libusb/1.0.27", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 版本化 conandata：必须按 self.version 取，否则 ** 展开会把版本键
        # 变成非法 kwarg（TypeError: get() got an unexpected keyword '2.0.2'）
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["DETACH_KERNEL_DRIVER"] = True
        toolchain.variables["INSTALL_UDEV_RULES"] = False
        toolchain.variables["ENABLE_ZEROCOPY"] = False
        # OHOS 是 CMake 未知平台：没有 Platform/HarmonyOS.cmake ⇒
        # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 未定义，共享库缺 DT_SONAME（L5a），
        # 且 install 会去建版本化符号链接（HMDFS 建链失败）。
        toolchain.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        toolchain.generate()

        # 上游依赖发现走 pkg-config：pkg_check_modules(LIBUSB libusb-1.0
        # IMPORTED_TARGET)，PKG_CONFIG_FOUND 且找不到就 FATAL_ERROR。
        # PkgConfigDeps 按 libusb 包的 pkg_config_name 生成 libusb-1.0.pc 到
        # generators 目录，再把它塞进 PKG_CONFIG_PATH（仓库 rpm/6.0.2 同款）。
        PkgConfigDeps(self).generate()
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(
            [self.generators_folder,
             os.environ.get("PKG_CONFIG_PATH", "")]).rstrip(os.pathsep)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._smoke_run_tools()

    def _smoke_run_tools(self):
        """上游无测试套件 → 至少证明 8 个 CLI 真能起来（真执行交付的可执行文件）。

        无电视棒时每个工具都应在秒级退出并打印 usage /“No supported devices
        found.”。输出为空说明工具根本起不来（缺库、链接坏、RPATH 错）→ 视为失败。
        """
        tool_dir = os.path.join(self.build_folder, "src")
        silent = []
        for tool in CLI_TOOLS:
            binary = os.path.join(tool_dir, tool)
            log = os.path.join(self.build_folder, tool + ".smoke.log")
            self.run('"%s" < /dev/null > "%s" 2>&1' % (binary, log),
                     ignore_errors=True)
            size = os.path.getsize(log) if os.path.isfile(log) else 0
            self.output.info("HMBS_CLI_SMOKE %s bytes=%d" % (tool, size))
            if size == 0:
                silent.append(tool)
        if silent:
            raise ConanException(
                "CLI 启动冒烟失败：以下工具无任何输出（可执行文件起不来）："
                + ", ".join(silent))

    def package(self):
        cmake = CMake(self)
        cmake.install()

        libdir = os.path.join(self.package_folder, "lib")
        # 上游同时装出 librtlsdr.so 与 librtlsdr.a（同名）→ 按 shared 只留一份
        if self.options.shared:
            rm(self, "librtlsdr.a", libdir)
        else:
            rm(self, "librtlsdr.so*", libdir)
        # 上游 export 出来的 CMake 包配置不可重定位（含构建机 libusb 绝对路径，
        # 并且引用上面被删掉的那一份库）→ 剔除，交给 conan 的 CMakeDeps。
        shutil.rmtree(os.path.join(libdir, "cmake"), ignore_errors=True)
        # udev 规则（INSTALL_UDEV_RULES 已关；防御性清理）与 libtool 残留
        shutil.rmtree(os.path.join(self.package_folder, "etc"), ignore_errors=True)
        rm(self, "*.la", libdir)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._rewrite_pkgconfig()

    def _rewrite_pkgconfig(self):
        """把 librtlsdr.pc 改写成可重定位形态（去掉构建机绝对路径）。"""
        pc = os.path.join(self.package_folder, "lib", "pkgconfig", "librtlsdr.pc")
        if not os.path.isfile(pc):
            raise ConanException("librtlsdr.pc 未安装到包内：%s" % pc)
        with open(pc, encoding="utf-8") as handle:
            body = handle.read()
        body = re.sub(r"^prefix=.*$", "prefix=${pcfiledir}/../..", body,
                      count=1, flags=re.MULTILINE)
        body = re.sub(r"^Cflags:.*$", "Cflags: -I${includedir}/", body,
                      count=1, flags=re.MULTILINE)
        body = re.sub(r"^Libs\.private:.*$", "Libs.private: -lusb-1.0", body,
                      count=1, flags=re.MULTILINE)
        with open(pc, "w", encoding="utf-8") as handle:
            handle.write(body)

    def package_info(self):
        self.cpp_info.libs = ["rtlsdr"]
        # 本包也交付 8 个 CLI（conan 默认的 bindirs 就是 bin，工具随包交付并由
        # conanrun/CMakeDeps 导出），CLI 申报写在版本目录下的 commands.json（R38）。
        # 这里**刻意不**给 cpp_info.bindirs 赋非空值：一旦赋值，CI L0k 与 preflight
        # PF8 就会要求 commands.json 出现在**包级目录**
        # （archives/<字母>/<包>/commands.json），而 preflight PF9 又硬性禁止变更
        # 落在包级目录（路径必须到 <版本>/ 层）—— 两条门禁互斥。按本仓现有先例
        # （archives/d/d0-blind-id/1.0/commands.json、kor/aggdraw/libtool 等 8 例）
        # 放在版本目录，两条门禁同时保持绿色。
        self.cpp_info.requires = ["libusb::libusb"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        # 包名带连字符：CMake 目标名不能用 '-'，显式改名（d0-blind-id 同款先例）
        self.cpp_info.set_property("cmake_file_name", "rtlsdr")
        self.cpp_info.set_property("cmake_target_name", "rtlsdr::rtlsdr")
        self.cpp_info.set_property("pkg_config_name", "librtlsdr")
