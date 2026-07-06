// _tkinter 运行期加载自检：dlopen(_tkinter.so, RTLD_NOW) —— 真加载 .so 并解析全部符号
// （Py 由 libpython、Tcl/Tk 由 libtcl/libtk 提供，NEEDED 齐则解析成功）。
//
// 加载者是本文件现编的 test_probe（clang 链接器自签的 adhoc 可执行）——这类进程在鸿蒙 CI 域可 dlopen
// 自签 .so（tcl 的 test_probe 实证）；而 SDK 签名的 python3 不行（故不用 python3 import）。
// 完整的运行期 import _tkinter（会调 PyInit__tkinter）在真机 HiShell 域验证。
#include <dlfcn.h>
#include <stdio.h>
#include <unistd.h>

#ifndef TARGET_SO
#define TARGET_SO "_tkinter.so"
#endif

int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror());
        return 1;
    }
    printf("dlopen OK: %s (Py/Tcl/Tk 符号全解析)\n", TARGET_SO);
    fflush(stdout);
    // 不 dlclose、直接 _exit(0)：没初始化解释器就卸载 _tkinter/libpython，其 fini/atexit 清理会 crash。
    // 我们只验「加载 + 符号解析」成功，到此已达成。
    _exit(0);
}
