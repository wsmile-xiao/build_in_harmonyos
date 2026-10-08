/* mmlib 鸿蒙特有测试：平台 ABI 实测 + OHOS 加载器运行时验证（真实执行器）
 *
 * argv[1] = 包内 libmmlib.so 的绝对路径。不链接 mmlib，只经 dlopen 加载，
 * 复现消费者运行时路径。逐用例 TEST PASS/FAIL + 末行 TEST SUMMARY；
 * 任一失败 exit(1)。
 */
#include <dlfcn.h>
#include <elf.h>
#include <link.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

static int g_checks = 0;
static int g_fails = 0;

#define CHECK(cond, what)                                                      \
    do {                                                                       \
        g_checks++;                                                            \
        if (cond) {                                                            \
            printf("  CHECK PASS: %s\n", (what));                              \
        } else {                                                               \
            printf("  CHECK FAIL: %s (%s:%d)\n", (what), __FILE__, __LINE__);  \
            g_fails++;                                                         \
        }                                                                      \
    } while (0)

static void case_done(const char *name, int fails_before)
{
    if (g_fails == fails_before) {
        printf("TEST PASS: %s\n", name);
    } else {
        printf("TEST FAIL: %s\n", name);
    }
}

static void test_elf_abi(const char *path)
{
    int f0 = g_fails;
    printf("TEST CASE: ELF 平台 ABI（包内产物实测）\n");
    FILE *f = fopen(path, "rb");
    CHECK(f != NULL, "打开包内 libmmlib.so");
    if (f == NULL) {
        case_done("ELF 平台 ABI（包内产物实测）", f0);
        return;
    }
    unsigned char ident[EI_NIDENT];
    size_t n = fread(ident, 1, sizeof ident, f);
    CHECK(n == sizeof ident, "读取 ELF ident（16 字节）");
    CHECK(ident[EI_MAG0] == 0x7f && ident[EI_MAG1] == 'E'
          && ident[EI_MAG2] == 'L' && ident[EI_MAG3] == 'F',
          "ELF magic 0x7f454c46");
    CHECK(ident[EI_CLASS] == ELFCLASS64, "ELFCLASS64");
    CHECK(ident[EI_DATA] == ELFDATA2LSB, "ELFDATA2LSB（小端）");
    Elf64_Ehdr eh;
    fseek(f, 0, SEEK_SET);
    n = fread(&eh, 1, sizeof eh, f);
    CHECK(n == sizeof eh, "读取 Elf64_Ehdr");
    CHECK(eh.e_type == ET_DYN, "e_type == ET_DYN（共享对象）");
    CHECK(eh.e_machine == EM_AARCH64, "e_machine == EM_AARCH64");
    int has_dynamic = 0;
    unsigned loads = 0;
    if (fseek(f, (long)eh.e_phoff, SEEK_SET) == 0) {
        for (unsigned i = 0; i < eh.e_phnum && i < 64; i++) {
            Elf64_Phdr ph;
            if (fread(&ph, 1, sizeof ph, f) != sizeof ph) {
                break;
            }
            if (ph.p_type == PT_DYNAMIC) {
                has_dynamic = 1;
            }
            if (ph.p_type == PT_LOAD) {
                loads++;
            }
        }
    }
    CHECK(has_dynamic, "PT_DYNAMIC 段存在");
    CHECK(loads >= 1, "PT_LOAD 段 >= 1");
    fclose(f);
    case_done("ELF 平台 ABI（包内产物实测）", f0);
}

static void test_loader(const char *path)
{
    int f0 = g_fails;
    printf("TEST CASE: OHOS 加载器 dlopen/dlsym（消费者运行时路径）\n");
    void *h = dlopen(path, RTLD_NOW);
    CHECK(h != NULL, "dlopen(RTLD_NOW) 成功解析全部符号");
    if (h == NULL) {
        const char *err = dlerror();
        printf("  dlopen error: %s\n", err != NULL ? err : "(null)");
        case_done("OHOS 加载器 dlopen/dlsym（消费者运行时路径）", f0);
        return;
    }
    const char *syms[] = {"mm_gettime", "mm_aligned_alloc", "mm_thr_mutex_init",
                          "mm_setenv", "mm_unlink", "mm_log"};
    for (size_t i = 0; i < sizeof syms / sizeof syms[0]; i++) {
        char what[128];
        snprintf(what, sizeof what, "dlsym(%s) 非 NULL", syms[i]);
        CHECK(dlsym(h, syms[i]) != NULL, what);
    }
    int (*gettime_fn)(int, void *) = NULL;
    *(void **)(&gettime_fn) = dlsym(h, "mm_gettime");
    unsigned char tsbuf[64];
    memset(tsbuf, 0, sizeof tsbuf);
    CHECK(gettime_fn != NULL && gettime_fn(CLOCK_MONOTONIC, tsbuf) == 0,
          "经 loader 符号调用 mm_gettime(CLOCK_MONOTONIC) 返回 0");
    if (gettime_fn != NULL) {
        Dl_info info;
        memset(&info, 0, sizeof info);
        CHECK(dladdr((void *)gettime_fn, &info) != 0 && info.dli_fname != NULL
              && strstr(info.dli_fname, "libmmlib.so") != NULL,
              "dladdr 确认符号来自 libmmlib.so");
    }
    dlclose(h);
    case_done("OHOS 加载器 dlopen/dlsym（消费者运行时路径）", f0);
}

int main(int argc, char **argv)
{
    printf("== mmlib OHOS platform test ==\n");
    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-libmmlib.so>\n", argv[0]);
        return 1;
    }
    test_elf_abi(argv[1]);
    test_loader(argv[1]);
    printf("TEST SUMMARY: %d checks, %d failed -> %s\n",
           g_checks, g_fails, g_fails == 0 ? "ALL PASS" : "FAILURES PRESENT");
    return g_fails == 0 ? 0 : 1;
}
