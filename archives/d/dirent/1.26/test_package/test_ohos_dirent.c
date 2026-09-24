/*
 * HarmonyOS 专项测试 — dirent 1.26 on OpenHarmony PC (arm64).
 *
 * 本用例独立于上游测试与通用消费者测试，针对 OHOS 运行环境验证 dirent
 * API 的真实语义：
 *   1. 在 TMPDIR 指向的可写目录（OHOS PC /tmp 为只读 erofs，必须用
 *      $TMPDIR）创建真实目录树：3 个文件、1 个子目录、1 个符号链接；
 *   2. opendir/readdir 枚举并断言条目数、d_type 分类（DT_REG/DT_DIR/DT_LNK）；
 *   3. scandir + alphasort 断言排序结果；
 *   4. telldir/seekdir 回跳断言；
 *   5. 全部通过后输出 PASS 并清理临时目录。
 *
 * 仅通过公开 dirent API 与 libc 系统调用（stat/lstat/mkdir/symlink），
 * 不包含库私有头文件、不调用内部符号。
 */
#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

static int failures = 0;

#define CHECK(cond, msg)                                       \
    do {                                                        \
        if (!(cond)) {                                          \
            fprintf(stderr, "FAIL: %s (errno=%d)\n", msg, errno); \
            failures++;                                         \
        }                                                       \
    } while (0)

/* 在 TMPDIR（回退 /tmp）下构造唯一测试目录 */
static int make_tmpdir(char *buf, size_t bufsz)
{
    const char *base = getenv("TMPDIR");
    if (base == NULL || *base == '\0')
        base = "/tmp";
    for (int i = 0; i < 100; i++) {
        snprintf(buf, bufsz, "%s/ohos-dirent-test-%d-%d",
                 base, (int) getpid(), i);
        if (mkdir(buf, 0700) == 0)
            return 0;
        if (errno != EEXIST)
            return -1;
    }
    return -1;
}

int main(void)
{
    char root[512];
    char path[600];
    FILE *fp;

    /* ── 准备真实目录树 ─────────────────────────────────── */
    CHECK(make_tmpdir(root, sizeof(root)) == 0, "create TMPDIR test dir");
    if (failures)
        return 1;

    snprintf(path, sizeof(path), "%s/alpha.txt", root);
    fp = fopen(path, "w");
    CHECK(fp != NULL, "create alpha.txt");
    if (fp) { fputs("alpha\n", fp); fclose(fp); }

    snprintf(path, sizeof(path), "%s/beta.bin", root);
    fp = fopen(path, "w");
    CHECK(fp != NULL, "create beta.bin");
    if (fp) { fputs("\x00\x01\x02", fp); fclose(fp); }

    snprintf(path, sizeof(path), "%s/subdir", root);
    CHECK(mkdir(path, 0755) == 0, "create subdir");

    snprintf(path, sizeof(path), "%s/alpha.txt", root);
    char link[600];
    snprintf(link, sizeof(link), "%s/link_to_alpha", root);
    CHECK(symlink(path, link) == 0, "create symlink link_to_alpha");

    /* ── 1. opendir/readdir 枚举 + d_type 分类 ───────────── */
    DIR *dp = opendir(root);
    CHECK(dp != NULL, "opendir(root)");
    if (!dp)
        return 1;

    int n_reg = 0, n_dir = 0, n_lnk = 0;
    struct dirent *de;
    while ((de = readdir(dp)) != NULL) {
        if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0)
            continue;
        if (de->d_type == DT_REG)
            n_reg++;
        else if (de->d_type == DT_DIR)
            n_dir++;
        else if (de->d_type == DT_LNK)
            n_lnk++;
    }
    CHECK(n_reg == 2, "readdir sees 2 regular files (alpha.txt, beta.bin)");
    CHECK(n_dir == 1, "readdir sees 1 subdirectory (subdir)");
    CHECK(n_lnk == 1, "readdir sees 1 symlink (link_to_alpha)");
    closedir(dp);

    /* ── 2. scandir + alphasort 排序断言 ─────────────────── */
    struct dirent **list = NULL;
    int n = scandir(root, &list, NULL, alphasort);
    CHECK(n > 0, "scandir returns > 0 entries");
    if (n > 0) {
        char *names[8];
        int k = 0;
        for (int i = 0; i < n && k < 8; i++) {
            if (strcmp(list[i]->d_name, ".") == 0 ||
                strcmp(list[i]->d_name, "..") == 0)
                continue;
            names[k++] = strdup(list[i]->d_name);
        }
        CHECK(k == 4, "scandir collected 4 non-dot entries");
        if (k == 4) {
            CHECK(strcmp(names[0], "alpha.txt") == 0,
                  "alphasort[0] = alpha.txt");
            CHECK(strcmp(names[1], "beta.bin") == 0,
                  "alphasort[1] = beta.bin");
            CHECK(strcmp(names[2], "link_to_alpha") == 0,
                  "alphasort[2] = link_to_alpha");
            CHECK(strcmp(names[3], "subdir") == 0,
                  "alphasort[3] = subdir");
        }
        for (int i = 0; i < n; i++)
            free(list[i]);
        free(list);
    }

    /* ── 3. telldir/seekdir 回跳断言 ─────────────────────── */
    dp = opendir(root);
    CHECK(dp != NULL, "opendir for telldir test");
    if (dp) {
        long p0 = telldir(dp);
        CHECK(p0 >= 0, "telldir initial position");
        /* 记录读取 beta.bin 之前的目录位置 */
        long p_beta = p0;
        while ((de = readdir(dp)) != NULL) {
            if (strcmp(de->d_name, "beta.bin") == 0)
                break;
            p_beta = telldir(dp);
        }
        CHECK(de != NULL && strcmp(de->d_name, "beta.bin") == 0,
              "found beta.bin while scanning");
        /* 回跳到 beta.bin 之前的位置, 下一个 readdir 应重新读到 beta.bin
         * （POSIX: telldir 返回下一次 readdir 将读取条目的位置） */
        errno = 0;
        seekdir(dp, p_beta);
        CHECK(errno == 0, "seekdir back");
        de = readdir(dp);
        CHECK(de != NULL && strcmp(de->d_name, "beta.bin") == 0,
              "seekdir lands back on beta.bin");
        closedir(dp);
    }

    /* ── 清理 ────────────────────────────────────────────── */
    unlink(link);
    unlink(path); /* path = root/alpha.txt */
    snprintf(path, sizeof(path), "%s/beta.bin", root);
    unlink(path);
    snprintf(path, sizeof(path), "%s/subdir", root);
    rmdir(path);
    rmdir(root);

    if (failures) {
        fprintf(stderr, "FAILED: %d assertion(s)\n", failures);
        return 1;
    }
    printf("PASS: HarmonyOS dirent special test ok\n");
    return 0;
}