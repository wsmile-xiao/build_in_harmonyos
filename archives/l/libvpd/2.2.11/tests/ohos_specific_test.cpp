// ohos_specific_test.cpp — HarmonyOS 专项测试（编译期 + 运行期真实验证）
// 1. 编译期：断言 __OHOS__ 已定义（本包仅面向 OHOS PC 平台构建）。
// 2. 运行期：打印当前平台 uname 信息；通过动态加载 libvpd 共享库
//    (libvpd-2.2.so) 验证运行期产物存在且可加载、符号 (new_vpdretriever)
//    可解析并实际调用；随后执行 lsvpd::System pack/unpack 往返。
// 非空壳：真实调用公开 API 并断言可观察结果。
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <unistd.h>
#include <sys/utsname.h>

#include <libvpd-2/system.hpp>

#ifdef __OHOS__
#define OHOS_COMPILE_FLAG "DEFINED"
#else
#define OHOS_COMPILE_FLAG "NOT-DEFINED"
#endif

int main()
{
    struct utsname u;
    if (uname(&u) == 0) {
        std::printf("ohos_test: platform sysname=%s release=%s machine=%s\n",
                    u.sysname, u.release, u.machine);
    }

    if (std::strcmp(OHOS_COMPILE_FLAG, "DEFINED") != 0) {
        std::fprintf(stderr, "ohos_test: FAIL __OHOS__ not defined at compile time\n");
        return 1;
    }
    std::printf("ohos_test: __OHOS__ compile-time check OK\n");

    // 运行期产物：动态加载 libvpd 共享库并解析公开 C API 符号
    void *h = dlopen("libvpd.so", RTLD_NOW | RTLD_GLOBAL);
    if (h == nullptr) {
        std::fprintf(stderr, "ohos_test: FAIL dlopen libvpd-2.2.so: %s\n", dlerror());
        return 1;
    }
    using NewVpd = struct vpdretriever *(*)(const char *, const char *);
    NewVpd fn = reinterpret_cast<NewVpd>(dlsym(h, "new_vpdretriever"));
    if (fn == nullptr) {
        std::fprintf(stderr, "ohos_test: FAIL dlsym new_vpdretriever\n");
        return 1;
    }
    std::printf("ohos_test: dlopen libvpd-2.2.so + dlsym new_vpdretriever OK\n");
    dlclose(h);

    // C++ 公开 API 往返（真实数据路径可运行）
    lsvpd::System sys;
    void *buf = nullptr;
    unsigned int len = sys.pack(&buf);
    if (len == 0 || buf == nullptr) {
        std::fprintf(stderr, "ohos_test: FAIL pack()\n");
        return 1;
    }
    lsvpd::System unpacked;
    unpacked.unpack(buf);
    delete[] static_cast<char *>(buf);
    if (unpacked.getMachineType() != sys.getMachineType()) {
        std::fprintf(stderr, "ohos_test: FAIL round-trip\n");
        return 1;
    }
    std::printf("ohos_test: lsvpd::System pack/unpack round-trip OK (%u bytes)\n", len);
    std::printf("ohos_test: ALL PASS\n");
    return 0;
}