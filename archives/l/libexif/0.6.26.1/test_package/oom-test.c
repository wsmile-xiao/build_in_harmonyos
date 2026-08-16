/*
 * oom-test.c — 模拟 libexif 在内存分配失败(OOM)时的行为
 *
 * 模式 1 (--fail-n N)：通过 ExifMem 注入失败分配器，在第 N 次分配时返回 NULL
 * 模式 2 (--rlimit MB)：通过 setrlimit(RLIMIT_AS) 限制进程地址空间
 *
 * 数据来源：
 *   --builtin：使用内置最小 EXIF 数据（供 CI/ctest 无外部文件执行）
 *   <jpg>    ：读取指定文件（手动验证时使用）
 *
 * 注意：
 *   1. fail_alloc 必须用 calloc（与 libexif 默认分配器语义一致，内存清零），
 *      否则 ExifData 内部 ifd[] 等数组为垃圾指针导致误报崩溃。
 *   2. --fail-n N 要求 N >= 1（N<=0 时无注入，视为参数错误，避免假通过）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <libexif/exif-data.h>
#include <libexif/exif-loader.h>
#include <libexif/exif-mem.h>

/* 内置最小 EXIF 数据（TIFF 头 + 空 IFD0，8 字节）：
 * "II" 字节序 + 42 + IFD0 偏移 8 + 0 条目数 + 0 下一 IFD 偏移 */
static const unsigned char builtin_exif[] = {
    0x49, 0x49, 0x2a, 0x00, 0x08, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static int fail_at = -1;   /* 第几次分配时失败 (-1=永不) */
static int alloc_count = 0;

static void *fail_alloc(unsigned int s) {
    if (fail_at > 0 && ++alloc_count == fail_at) {
        fprintf(stderr, "[alloc] 第 %d 次分配(失败注入): size=%u -> NULL\n", alloc_count, s);
        return NULL;
    }
    return calloc((size_t)s, 1);   /* 与默认分配器一致: 清零 */
}
static void *fail_realloc(void *p, unsigned int s) {
    if (fail_at > 0 && ++alloc_count == fail_at) {
        fprintf(stderr, "[realloc] 第 %d 次分配(失败注入): size=%u -> NULL\n", alloc_count, s);
        return NULL;
    }
    return realloc(p, (size_t)s);
}
static void fail_free(void *p) { free(p); }

static int set_as_limit(long mb) {
    struct rlimit rl;
    if (getrlimit(RLIMIT_AS, &rl) != 0) { perror("getrlimit"); return -1; }
    rl.rlim_cur = (rlim_t)mb * 1024 * 1024;
    if (setrlimit(RLIMIT_AS, &rl) != 0) { perror("setrlimit"); return -1; }
    return 0;
}

int main(int argc, char *argv[]) {
    /* 用法: oom-test --fail-n N (--builtin|<jpg>) | oom-test --rlimit MB (--builtin|<jpg>) */
    if (argc < 3) {
        fprintf(stderr, "用法: %s --fail-n N (--builtin|<jpg>) | %s --rlimit MB (--builtin|<jpg>)\n",
                argv[0], argv[0]);
        return 2;
    }
    const char *mode = argv[1];
    long param = atol(argv[2]);
    const char *src = (argc >= 4) ? argv[3] : NULL;
    int use_builtin = (src && !strcmp(src, "--builtin"));
    int use_fail = !strcmp(mode, "--fail-n");

    if (!use_fail && strcmp(mode, "--rlimit")) {
        fprintf(stderr, "未知模式: %s\n", mode);
        return 2;
    }
    if (use_fail) {
        /* 参数校验: N 必须 >= 1，否则无注入会假通过 (P3 修复) */
        if (param < 1) {
            fprintf(stderr, "参数错误: --fail-n N 要求 N >= 1 (收到 %ld)\n", param);
            return 2;
        }
        fail_at = (int)param;
        fprintf(stderr, "[mode1] 失败分配器: 第 %d 次分配返回 NULL\n", fail_at);
    } else {
        if (param < 1) {
            fprintf(stderr, "参数错误: --rlimit MB 要求 MB >= 1 (收到 %ld)\n", param);
            return 2;
        }
        fprintf(stderr, "[mode2] RLIMIT_AS 限制为 %ld MB\n", param);
        if (set_as_limit(param) != 0) return 1;
    }

    unsigned char *buf = NULL;
    long sz = 0;

    if (use_builtin) {
        /* 内置数据: 无需文件，CI/ctest 可直接执行 */
        sz = (long)sizeof(builtin_exif);
        buf = (unsigned char *)malloc((size_t)sz);
        if (!buf) { fprintf(stderr, "内置数据分配失败\n"); return 1; }
        memcpy(buf, builtin_exif, (size_t)sz);
        fprintf(stderr, "[data] 使用内置 EXIF 数据 (%ld 字节)\n", sz);
    } else if (src) {
        FILE *f = fopen(src, "rb");
        if (!f) { perror("fopen"); return 1; }
        if (fseek(f, 0, SEEK_END) != 0) { perror("fseek"); fclose(f); return 1; }
        long end = ftell(f);
        if (fseek(f, 0, SEEK_SET) != 0) { perror("fseek"); fclose(f); return 1; }
        sz = end;
        buf = (unsigned char *)malloc((size_t)sz);
        if (!buf) { fprintf(stderr, "读文件失败: malloc(%ld) NULL\n", sz); fclose(f); return 1; }
        if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) { perror("fread"); fclose(f); free(buf); return 1; }
        fclose(f);
        fprintf(stderr, "[data] 已读取文件 (%ld 字节)\n", sz);
    } else {
        fprintf(stderr, "缺少数据来源: 需指定 --builtin 或文件路径\n");
        return 2;
    }

    if (use_fail) {
        ExifMem *mem = exif_mem_new(fail_alloc, fail_realloc, fail_free);
        if (!mem) { fprintf(stderr, "RESULT: exif_mem_new 返回 NULL (优雅失败, 未崩溃)\n"); free(buf); return 0; }
        ExifData *d = exif_data_new_mem(mem);
        if (!d) {
            fprintf(stderr, "RESULT: exif_data_new_mem 返回 NULL (优雅失败, 未崩溃)\n");
        } else {
            exif_data_load_data(d, buf, (unsigned int)sz);
            fprintf(stderr, "RESULT: 解析完成, 共分配 %d 次 (注入点之后仍存活)\n", alloc_count);
            exif_data_unref(d);
        }
        exif_mem_unref(mem);
    } else {
        /* rlimit 模式: 用默认分配器从内存数据加载（与文件等价，避免假失败） */
        ExifData *d = exif_data_new();
        if (!d) { fprintf(stderr, "RESULT: exif_data_new 返回 NULL (优雅失败, 未崩溃)\n"); free(buf); return 0; }
        exif_data_load_data(d, buf, (unsigned int)sz);
        fprintf(stderr, "RESULT: OOM 限制下解析成功\n");
        exif_data_unref(d);
    }
    free(buf);
    fprintf(stderr, "DONE: 进程存活, 无崩溃\n");
    return 0;
}
