import glob
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import save


class AcsccidTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 消费者验证（R34）：dlopen libacsccid.so 并校验 IFD 入口符号存在
        src = r"""
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>

/* pcscd 加载 IFD 驱动时提供宿主符号 log_msg/log_xxd（pcsc-lite ifdhandler 接口）。
 * 本测试程序模拟宿主，提供 stub 使 libacsccid.so 可被 dlopen 重定位。 */
void log_msg(const int priority, const char *fmt, ...) {
    (void)priority; (void)fmt;
}
void log_xxd(const int priority, const char *msg,
             const unsigned char *buffer, const int len) {
    (void)priority; (void)msg; (void)buffer; (void)len;
}

/* acsccid 是 pcsc-lite 的 IFD 驱动 bundle，pcscd 在运行期 dlopen 加载。
 * 消费者验证：dlopen 成功 + 关键 IFD 符号（IFDHCreateChannelByName /
 * IFDHControl / IFDHGetCapabilities / IFDHTransmitToICC）解析成功即链路正常。 */
int main(int argc, char **argv) {
    const char *path = (argc > 1) ? argv[1] : "libacsccid.so";
    void *h = dlopen(path, RTLD_NOW);
    if (!h) {
        printf("dlopen %s FAILED: %s\n", path, dlerror());
        return 1;
    }
    const char *syms[] = {
        "IFDHCreateChannelByName", "IFDHControl",
        "IFDHGetCapabilities", "IFDHTransmitToICC", "IFDHCloseChannel", NULL
    };
    int missing = 0;
    for (int i = 0; syms[i]; i++) {
        if (!dlsym(h, syms[i])) {
            printf("missing symbol: %s\n", syms[i]);
            missing++;
        }
    }
    dlclose(h);
    if (missing) {
        printf("acsccid 1.1.13 FAILED: %d IFD symbols missing\n", missing);
        return 1;
    }
    printf("acsccid 1.1.13 OK: dlopen + IFD symbols verified\n");
    return 0;
}
"""
        save(self, "test_acsccid.c", src)
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc_path = cc.get("c") or "clang"
        # -Wl,-E 导出 log_msg/log_xxd stub 到动态符号表，供 dlopen 重定位
        self.run('{cc} test_acsccid.c -o test_acsccid -ldl -Wl,-E'.format(cc=cc_path))

    def test(self):
        # 沙箱可直接运行 OHOS aarch64 二进制（同 profile 非真正交叉），
        # 不因 cross_building 跳过实质测试（R34/L1 要求 test() 实际执行）。
        # 定位包内 bundle 中的 libacsccid.so（安装到 usr/local/pcsc/drivers/ifd-acsccid.bundle/...）
        pkg = self.dependencies["acsccid"].package_folder
        candidates = glob.glob(os.path.join(pkg, "**", "libacsccid.so"), recursive=True)
        if not candidates:
            candidates = glob.glob(os.path.join(pkg, "**", "libacsccid.so.*"), recursive=True)
        if not candidates:
            print("libacsccid.so not found in package folder %s" % pkg)
            raise SystemExit(1)
        so_path = candidates[0]
        # dlopen libacsccid.so 需要其依赖的 libpcsclite.so.1/libusb-1.0.so.0，
        # 在命令内联 LD_LIBRARY_PATH（conan run env 列表在 OHOS 环境未生效）
        pcsc_libdir = os.path.join(self.dependencies["pcsc-lite"].package_folder, "lib")
        libusb_libdir = os.path.join(self.dependencies["libusb"].package_folder, "lib")
        self.run("LD_LIBRARY_PATH=%s:%s ./test_acsccid '%s'" % (pcsc_libdir, libusb_libdir, so_path))
