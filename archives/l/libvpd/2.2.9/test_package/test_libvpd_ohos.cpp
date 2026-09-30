/* libvpd 2.2.9 鸿蒙（HarmonyOS PC）专有测试
 *
 * 与 test_libvpd.c / test_libvpd_cxx.cpp 的区别：
 *   前两者是**上游 API 的通用消费者验证**（任何平台都该通过）；
 *   本文件只做**只在 OHOS 平台才有意义**的断言 —— 即把本次适配赖以成立
 *   的平台前提写成可执行判据，一旦平台假设不成立立即显形。
 *
 * 断言项（均为可判据，非打印充数）：
 *   1. 编译期：__OHOS__ 已定义（包 settings os=OHOS，仅面向鸿蒙 PC 构建；
 *      未定义说明工具链/平台选择错误，编译期即拦下）。
 *   2. 运行期平台身份：uname(2) 报 sysname == "HarmonyOS"、machine == "aarch64"。
 *      （aarch64-linux-ohos 二进制只可能在鸿蒙上执行，故此为强断言而非软打印。）
 *   3. libc++ 而非 libstdc++：OHOS sysroot 只提供 libc++，这正是本适配把上游
 *      Makefile.am 里 `-lstdc++` 改为 `-lc++` 的原因。此处以编译期宏
 *      `_LIBCPP_VERSION` 存在、`__GLIBCXX__` 不存在做实证 —— 若哪天链到
 *      libstdc++，说明该补丁失效，本项会失败。
 *   4. 真实调用公开 API（不依赖真机 VPD 数据）：
 *      C 侧  new_dataitem / calc_packed_length_dataitem / free_dataitem
 *      C++ 侧 lsvpd::System pack→unpack 往返一致
 *
 * ⚠️ 不走 dlopen：本配方 shared=False（R26，系统同名库静态），产物只有
 *    libvpd.a / libvpd_cxx.a，无 .so 可加载。故按**静态链接**方式直接调用，
 *    由链接器验证产物完整性与符号可用性。
 * ⚠️ 不使用 assert()：构建带 -DNDEBUG，断言会被整体移除；改用显式 CHECK 宏。
 */
#include <cstdio>
#include <cstring>
#include <sys/utsname.h>

/* ⚠️ 上游 C 头文件（dataitem.h 等）**没有 extern "C" 守卫**，从 C++ 直接
 *    #include 会让 new_dataitem() 等按 C++ 名字修饰去链接，运行期产物里
 *    只有未修饰的 C 符号 → 链接期 undefined symbol。
 *    故此处按规定做法用 extern "C" 包裹（不改上游源码，符合 R6/R8）。 */
extern "C" {
#include <libvpd-2/dataitem.h>
}

#include <libvpd-2/system.hpp>

static int g_checks = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        g_checks++;                                                         \
        if (!(cond)) {                                                      \
            fprintf(stderr, "  [FAIL] %s (line %d)\n", (msg), __LINE__);    \
            return 1;                                                       \
        }                                                                   \
    } while (0)

int main(void)
{
    /* ── 1. 编译期平台断言：__OHOS__ 必须已定义 ─────────────────── */
    int ohos_defined = 0;
#ifdef __OHOS__
    ohos_defined = 1;
#endif
    CHECK(ohos_defined, "编译期 __OHOS__ 未定义 —— 未按 OHOS 目标构建");
    printf("  [1] 编译期: __OHOS__ 已定义（os=OHOS 目标构建）\n");

    /* ── 2. 运行期平台身份：HarmonyOS / aarch64 ─────────────────── */
    struct utsname u;
    CHECK(uname(&u) == 0, "uname(2) 调用失败");
    printf("  [2] 运行期: sysname=%s release=%s machine=%s\n",
           u.sysname, u.release, u.machine);
    CHECK(strcmp(u.sysname, "HarmonyOS") == 0,
          "运行平台非 HarmonyOS（aarch64-linux-ohos 二进制应在鸿蒙执行）");
    CHECK(strcmp(u.machine, "aarch64") == 0, "机器架构非 aarch64");

    /* ── 3. libc++ 实证（本适配 -lstdc++ → -lc++ 补丁的判据）──────── */
#if defined(_LIBCPP_VERSION) && !defined(__GLIBCXX__)
    printf("  [3] 标准库: libc++ (_LIBCPP_VERSION=%d)，符合 OHOS sysroot 现状\n",
           _LIBCPP_VERSION);
#else
    fprintf(stderr, "  [FAIL] 标准库: 未使用 libc++ —— -lc++ 适配失效\n");
    return 1;
#endif

    /* ── 4. 真实调用公开 API（静态链接验证产物可用）─────────────── */
    /* C 侧：构造 → 打包长度 → 释放 */
    struct dataitem *di = new_dataitem();
    CHECK(di != NULL, "new_dataitem() 返回 NULL");
    di->ac        = strdup("MN");
    di->humanName = strdup("Model Name");
    di->dataValue = strdup("ohos-value");
    CHECK(di->ac && di->humanName && di->dataValue, "strdup 失败");
    /* 3 + len("MN") + len("Model Name") + len("ohos-value") = 3+2+10+10 = 25 */
    const int packed = calc_packed_length_dataitem(di);
    CHECK(packed == 25, "calc_packed_length_dataitem() 在 OHOS 上结果非 25");
    free_dataitem(di);   /* 内部会释放字段并遍历链，勿手动 free */
    printf("  [4] C API: new_dataitem + calc_packed_length + free 往返 ok (packed=%d)\n",
           packed);

    /* C++ 侧：System pack → unpack 往返一致 */
    lsvpd::System sys;
    void *buf = NULL;
    const unsigned int len = sys.pack(&buf);
    CHECK(buf != NULL, "System::pack() 未分配缓冲区");
    CHECK(len > 0, "System::pack() 返回长度为 0");

    lsvpd::System unpacked((const void *)buf);
    void *buf2 = NULL;
    const unsigned int len2 = unpacked.pack(&buf2);
    CHECK(buf2 != NULL, "unpack 后再 pack 未分配缓冲区");
    CHECK(len2 == len, "System pack/unpack 往返长度不一致");
    delete[] static_cast<char *>(buf);
    delete[] static_cast<char *>(buf2);
    printf("  [4] C++ API: lsvpd::System pack/unpack 往返一致 (%u bytes)\n", len);

    printf("  [OK] libvpd HarmonyOS-specific test passed（共 %d 项检查通过）\n",
           g_checks);
    return 0;
}
