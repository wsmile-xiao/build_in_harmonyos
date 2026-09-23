/*
 * libinklevel 0.9.7 鸿蒙 PC 平台特有测试（HarmonyOS PC / aarch64）
 *
 * 上游 0.9.7 没有测试套件（Makefile.am 无 TESTS / check_PROGRAMS）。test.c 覆盖通用
 * 消费者契约；本文件补充**平台特有**断言，全部通过公共头 inklevel.h 真实调用被测库，
 * 不使用桩函数，也不依赖真实打印机：
 *
 *   TC-OHOS1 鸿蒙动态链接器按 SONAME 解析完整依赖链（读 /proc/self/maps 实证，
 *            对应 SKILL 记录的平台风险：$ORIGIN/../lib 相对解析在鸿蒙上不稳定）
 *   TC-OHOS2 鸿蒙 PC 无 USB 打印机/无设备权限时，探测必须有界快速失败且可重复
 *            （不得挂起——受限 USB 环境下阻塞是平台典型故障形态）
 *   TC-OHOS3 鸿蒙默认 UTF-8 locale 下多字节（中文）设备名的健壮性，
 *            含超长 UTF-8 设备名边界
 *   TC-OHOS4 产物为 aarch64 64 位 OHOS ELF（交叉构建目标正确性）
 *
 * 实现说明：鸿蒙上 /proc/self/maps 记录的映射路径是 HMDFS 底层真实路径
 * （如 /data/service/el2/.../hmdfs/...），进程侧 open() 可能因权限语义不可达，
 * 因此 TC-OHOS4 直接从映射起始地址读取 ELF 头（只读映射），不重复 open 文件。
 */

#include <elf.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "inklevel.h"

#define PROBE_TIMEOUT_SEC 5.0   /* 单轮探测时延上界（秒） */
#define PROBE_ROUNDS      3     /* 重复探测轮数：验证可重复、无状态泄漏 */

struct maps_entry {
    unsigned long start;        /* 映射起始地址 */
    char          perms[8];
    char          path[512];
};

static int         failures = 0;
static struct maps_entry lib_entry;   /* TC-OHOS1 命中的 libinklevel 映射 */

static void check(const char *name, int cond)
{
    printf("[%s] %s\n", cond ? "PASS" : "FAIL", name);
    if (!cond) {
        failures++;
    }
}

/*
 * 在 /proc/self/maps 中查找基名以 soname 开头的首个映射。
 * 返回 1=命中、0=未命中、-1=/proc 不可读（鸿蒙上属环境异常，不能算“已解析”）。
 */
static int maps_lookup(const char *soname, struct maps_entry *out)
{
    FILE *fp;
    char  line[1024];
    size_t n = strlen(soname);
    int   found = 0;

    fp = fopen("/proc/self/maps", "r");
    if (fp == NULL) {
        return -1;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        unsigned long start, end, offset, inode;
        unsigned int  dev_major, dev_minor;
        char          perms[8];
        char          path[512];
        char         *base;

        if (sscanf(line, "%lx-%lx %7s %lx %x:%x %lu %511[^\n]",
                   &start, &end, perms, &offset,
                   &dev_major, &dev_minor, &inode, path) < 8) {
            continue;                   /* 匿名映射行（无路径）跳过 */
        }
        base = strrchr(path, '/');
        base = (base != NULL) ? base + 1 : path;
        if (strncmp(base, soname, n) == 0 &&
            (base[n] == '\0' || base[n] == '.')) {
            found = 1;
            if (out != NULL) {
                memset(out, 0, sizeof(*out));
                out->start = start;
                snprintf(out->perms, sizeof(out->perms), "%s", perms);
                snprintf(out->path, sizeof(out->path), "%s", path);
            }
            break;
        }
    }
    fclose(fp);
    return found;
}

/*
 * 库目录是否来自运行时搜索路径（LD_LIBRARY_PATH 条目）。
 * 两侧均做 realpath 归一；此外鸿蒙 HMDFS 下 /proc/self/maps 记录的是挂载底层
 * 路径（/data/service/el2/<uid>/hmdfs/account/files/Docs/...，进程内不可访问），
 * 而进程可见路径以 $HOME 为前缀，故二者视作同一根再比剩余相对路径。
 * 返回 1=是、0=否、-1=环境未设置 LD_LIBRARY_PATH。
 */
static int dir_in_runpath(const char *dir)
{
    const char *ld   = getenv("LD_LIBRARY_PATH");
    const char *home = getenv("HOME");
    size_t      home_len;
    const char *s;
    char        real_dir[PATH_MAX];
    size_t      real_dir_len;

    if (ld == NULL || ld[0] == '\0') {
        return -1;
    }
    if (realpath(dir, real_dir) == NULL) {
        snprintf(real_dir, sizeof(real_dir), "%s", dir);
    }
    real_dir_len = strlen(real_dir);
    home_len = (home != NULL) ? strlen(home) : 0;

    s = ld;
    while (*s != '\0') {
        const char *e = strchr(s, ':');
        size_t      len = (e != NULL) ? (size_t)(e - s) : strlen(s);
        char        cand[PATH_MAX];
        char        real_cand[PATH_MAX];

        if (len > 0 && len < sizeof(cand)) {
            const char *rel = NULL;
            size_t      rel_len;

            memcpy(cand, s, len);
            cand[len] = '\0';
            if (realpath(cand, real_cand) != NULL &&
                strcmp(real_dir, real_cand) == 0) {
                return 1;
            }
            if (home_len > 0 && strncmp(cand, home, home_len) == 0) {
                rel = cand + home_len;          /* 以 '/' 开头的相对部分 */
            }
            if (rel != NULL && rel[0] == '/') {
                rel_len = strlen(rel);
                if (rel_len <= real_dir_len &&
                    strcmp(real_dir + (real_dir_len - rel_len), rel) == 0) {
                    return 1;
                }
            }
        }
        if (e == NULL) {
            break;
        }
        s = e + 1;
    }
    return 0;
}

static double elapsed_sec(const struct timespec *a, const struct timespec *b)
{
    return (double)(b->tv_sec - a->tv_sec) +
           (double)(b->tv_nsec - a->tv_nsec) / 1000000000.0;
}

int main(void)
{
    struct ink_level level;
    char  zh_uri[] = "打印机@客厅.local";
    char  long_uri[2048];
    int   rc, rc_maps, rc_path, i;
    int   rounds_ok = 1, bounded_ok = 1;
    int   elf_class = 0, elf_data = 0;
    unsigned int machine = 0;

    /* ---- TC-OHOS1: 运行时按 SONAME 解析，依赖链完整 ---- */
    rc_maps = maps_lookup("libinklevel.so.5", &lib_entry);
    check("TC-OHOS1 /proc/self/maps 可读（鸿蒙进程映射表）", rc_maps >= 0);
    check("TC-OHOS1 运行时映射含 libinklevel.so.5（按 SONAME 解析成功）",
          rc_maps == 1);

    /* 断言无条件执行：条件式跳过会让断言总数随环境变化，无法作为固定口径复现 */
    rc_path = 0;
    if (rc_maps == 1) {
        char *slash = strrchr(lib_entry.path, '/');

        printf("       libinklevel 映射 = %s\n", lib_entry.path);
        printf("       LD_LIBRARY_PATH = %s\n",
               getenv("LD_LIBRARY_PATH") ? getenv("LD_LIBRARY_PATH") : "(未设置)");
        if (slash != NULL) {
            char   dir[512];
            size_t len = (size_t)(slash - lib_entry.path);

            if (len >= sizeof(dir)) {
                len = sizeof(dir) - 1;
            }
            memcpy(dir, lib_entry.path, len);
            dir[len] = '\0';
            rc_path = dir_in_runpath(dir);
            if (rc_path < 0) {
                printf("       LD_LIBRARY_PATH 未设置：消费者运行时环境契约不满足\n");
            }
        }
    }
    check("TC-OHOS1 库目录来自运行时搜索路径（非 $ORIGIN 相对解析）",
          rc_path == 1);
    check("TC-OHOS1 依赖链完整：libusb-1.0.so.0 已映射",
          maps_lookup("libusb-1.0.so.0", NULL) == 1);
    check("TC-OHOS1 依赖链完整：libxml2.so.16 已映射",
          maps_lookup("libxml2.so.16", NULL) == 1);

    /* ---- TC-OHOS2: 无 USB 设备/权限时有界快速失败且可重复 ---- */
    for (i = 0; i < PROBE_ROUNDS; i++) {
        struct timespec t0, t1;
        double          dt;

        memset(&level, 0, sizeof(level));
        clock_gettime(CLOCK_MONOTONIC, &t0);
        rc = get_ink_level(USB, NULL, 0, &level);
        clock_gettime(CLOCK_MONOTONIC, &t1);
        dt = elapsed_sec(&t0, &t1);
        printf("       probe#%d get_ink_level(USB) = %d, elapsed = %.3fs\n",
               i + 1, rc, dt);
        if (rc >= 0) {
            rounds_ok = 0;
        }
        if (dt >= PROBE_TIMEOUT_SEC) {
            bounded_ok = 0;
        }
    }
    check("TC-OHOS2 无 USB 设备/权限时每轮探测均返回负值", rounds_ok == 1);
    check("TC-OHOS2 探测有界快速失败（每轮 < 5s，不挂起）", bounded_ok == 1);

    /* ---- TC-OHOS3: UTF-8 多字节设备名健壮性 ---- */
    memset(&level, 0, sizeof(level));
    rc = get_ink_level(CUSTOM_BJNP, zh_uri, 0, &level);
    printf("       get_ink_level(CUSTOM_BJNP, \"%s\") = %d\n", zh_uri, rc);
    check("TC-OHOS3 中文（UTF-8）设备名返回负值且不崩溃", rc < 0);

    memset(long_uri, 0, sizeof(long_uri));
    for (i = 0; i < 100; i++) {         /* 100×9 = 900 字节 UTF-8，远超常规缓冲 */
        strcat(long_uri, "打印机");
    }
    strcat(long_uri, ".local");
    memset(&level, 0, sizeof(level));
    rc = get_ink_level(CUSTOM_BJNP, long_uri, 0, &level);
    printf("       get_ink_level(CUSTOM_BJNP, 900B UTF-8 设备名) = %d\n", rc);
    check("TC-OHOS3 超长 UTF-8 设备名无越界崩溃且返回负值", rc < 0);

    /* ---- TC-OHOS4: 交叉构建目标正确性（aarch64 OHOS ELF） ---- */
    /* 两条断言无条件执行：映射不可读时用哨兵值判负并打印原因，断言数保持恒定 */
    elf_class = 0;
    elf_data = 0;
    machine = 0;
    if (rc_maps == 1 && lib_entry.perms[0] == 'r') {
        const unsigned char *eh =
            (const unsigned char *)(uintptr_t)lib_entry.start;   /* 只读映射起始处 */

        elf_class = eh[EI_CLASS];
        elf_data = eh[EI_DATA];
        machine = (unsigned int)eh[18] | ((unsigned int)eh[19] << 8);
        printf("       ELF class=%d data=%d machine=%u（映射权限 %s）\n",
               elf_class, elf_data, machine, lib_entry.perms);
    } else {
        printf("       无法读取映射 ELF 头（rc_maps=%d，映射权限 %s）\n",
               rc_maps, rc_maps == 1 ? lib_entry.perms : "n/a");
    }
    check("TC-OHOS4 产物为 64 位小端 ELF",
          elf_class == ELFCLASS64 && elf_data == ELFDATA2LSB);
    check("TC-OHOS4 e_machine == EM_AARCH64（aarch64 OHOS 目标）",
          machine == EM_AARCH64);

    if (failures == 0) {
        printf("ALL CHECKS PASSED\n");
        return 0;
    }
    printf("%d CHECK(S) FAILED\n", failures);
    return 1;
}
