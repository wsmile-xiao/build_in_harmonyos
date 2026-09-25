/* test_package 探针：验证交付的 tpm2-tss 共享库可被加载且导出 gnupg 所需符号。
 * 用 dlopen+dlsym 而非链接期断言，检查的是「运行时真实可用」而非文件存在性（R34 反空壳）。
 * 断言按**符号实际归属的库**分组——Esys_* 在 libtss2-esys，Tss2_TctiLdr_* 在
 * libtss2-tctildr，Tss2_RC_Decode 在 libtss2-rc（初始版本曾把它们都当成 esys 的导出，
 * 属错误断言）。 */
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>

struct check {
    const char *lib;
    const char *sym;
};

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <libdir>\n", argv[0]);
        return 2;
    }
    const char *libdir = argv[1];

    /* gnupg 的 configure 用 AC_SEARCH_LIBS([Esys_Initialize],[tss2-esys]) 探测 libtss，
     * 且链接 -ltss2-esys -ltss2-mu -ltss2-rc -ltss2-tctildr，故这 4 个库都必须在。 */
    const struct check checks[] = {
        {"libtss2-esys.so",    "Esys_Initialize"},
        {"libtss2-esys.so",    "Esys_Finalize"},
        {"libtss2-esys.so",    "Esys_GetTcti"},
        {"libtss2-esys.so",    "Esys_Startup"},
        {"libtss2-mu.so",      "Tss2_MU_UINT32_Marshal"},
        {"libtss2-rc.so",      "Tss2_RC_Decode"},
        {"libtss2-tctildr.so", "Tss2_TctiLdr_Initialize"},
        {"libtss2-tcti-device.so", "Tss2_Tcti_Device_Init"},
    };
    const unsigned n = sizeof(checks) / sizeof(checks[0]);

    int bad = 0;
    for (unsigned i = 0; i < n; i++) {
        char path[1024];
        snprintf(path, sizeof path, "%s/%s", libdir, checks[i].lib);
        void *h = dlopen(path, RTLD_NOW);
        if (!h) {
            printf("  %-24s %-26s LOAD-FAIL (%s)\n", checks[i].lib, checks[i].sym,
                   dlerror());
            bad++;
            continue;
        }
        void *s = dlsym(h, checks[i].sym);
        printf("  %-24s %-26s %s\n", checks[i].lib, checks[i].sym, s ? "OK" : "MISSING");
        if (!s)
            bad++;
        dlclose(h);
    }
    printf("RESULT: %s (%u checks, %d failures)\n", bad ? "FAIL" : "PASS", n, bad);
    return bad ? 1 : 0;
}
