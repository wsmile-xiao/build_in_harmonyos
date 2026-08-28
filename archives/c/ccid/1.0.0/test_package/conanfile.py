import glob
import os

from conan import ConanFile


class CcidTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libusb/1.0.27")

    def build(self):
        # 消费者验证：编译 test_ccid.c（静态源文件，非动态生成）
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc_path = cc.get("c") or "clang"
        # -Wl,-E 导出 log_msg/log_xxd stub 到动态符号表，供 dlopen 重定位
        self.run('{cc} test_ccid.c -o test_ccid -ldl -Wl,-E'.format(cc=cc_path))

    def test(self):
        # 沙箱可直接运行 OHOS aarch64 二进制（同 profile 非真正交叉），
        # 不因 cross_building 跳过实质测试（L1 要求 test() 实际执行）。
        pkg = self.dependencies["ccid"].package_folder
        candidates = glob.glob(os.path.join(pkg, "**", "libccid.so"), recursive=True)
        if not candidates:
            candidates = glob.glob(os.path.join(pkg, "**", "libccid.so.*"), recursive=True)
        if not candidates:
            print("libccid.so not found in package folder %s" % pkg)
            raise SystemExit(1)
        so_path = candidates[0]
        # dlopen libccid.so 需要其依赖的 libpcsclite.so.1/libusb.so/libusb-1.0.so，
        # 在命令内联 LD_LIBRARY_PATH（conan run env 列表在 OHOS 环境未生效）
        pcsc_libdir = os.path.join(self.dependencies["pcsc-lite"].package_folder, "lib")
        compat_libdir = os.path.join(self.dependencies["libusb-compat"].package_folder, "lib")
        libusb_libdir = os.path.join(self.dependencies["libusb"].package_folder, "lib")
        self.run("LD_LIBRARY_PATH=%s:%s:%s ./test_ccid '%s'" % (pcsc_libdir, compat_libdir, libusb_libdir, so_path))
