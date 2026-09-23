// test_tinydir_harmonyos.c — HarmonyOS 专项测试 (tinydir 1.2.4)
//
// 目的：验证 tinydir 头文件库在 OHOS (aarch64) 目标上可编译、可运行，
// 并与 OHOS 平台 libc (dirent/stat/unistd) 接口集成使用 —— 覆盖上游
// file_open_test 未覆盖的"目录迭代/排序/子目录导航/扩展名提取"平台集成场景。
//
// OHOS 平台特征断言：
//   - 编译目标为 aarch64 (OHOS 唯一 arch) —— 编译期断言
//   - 使用 OHOS libc 的 mkdir/rmdir/getcwd/access 等接口
//
// 编译: clang -std=c11 -Wall -Wextra -I<prefix>/include test_tinydir_harmonyos.c -o test_tinydir_harmonyos
// 运行: ./test_tinydir_harmonyos   (需在 OHOS 设备/模拟环境执行)

#include <tinydir.h>

#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#if !defined(__aarch64__) && !defined(_M_ARM64)
#error "OHOS target must be aarch64"
#endif

static int failures = 0;
#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        if (cond) {                                                        \
            printf("  [PASS] %s\n", msg);                                  \
        } else {                                                           \
            printf("  [FAIL] %s (errno=%d)\n", msg, errno);                \
            ++failures;                                                    \
        }                                                                  \
    } while (0)

int main(void)
{
    char cwd[4096];
    char testdir[4096];
    char file_a[4096];
    char file_b[4096];

    printf("=== tinydir HarmonyOS 专项测试 ===\n");
    printf("cwd: %s\n", getcwd(cwd, sizeof(cwd)));

    /* 专项 1: 平台断言 —— OHOS libc 接口可用 */
    CHECK(getcwd(cwd, sizeof(cwd)) != NULL, "OHOS getcwd available");

    /* 专项 2: 构造测试目录与文件 */
    snprintf(testdir, sizeof(testdir), "%s/tinydir_ohos_%ld", cwd, (long)getpid());
    snprintf(file_a, sizeof(file_a), "%s/alpha.txt", testdir);
    snprintf(file_b, sizeof(file_b), "%s/Beta.dat", testdir);

    CHECK(mkdir(testdir, 0700) == 0 || errno == EEXIST, "OHOS mkdir works");
    CHECK(access(testdir, F_OK) == 0, "OHOS access works");

    FILE *fa = fopen(file_a, "w");
    FILE *fb = fopen(file_b, "w");
    if (fa) { fputs("alpha", fa); fclose(fa); }
    if (fb) { fputs("beta", fb); fclose(fb); }
    CHECK(access(file_a, F_OK) == 0, "created alpha.txt");
    CHECK(access(file_b, F_OK) == 0, "created Beta.dat");

    /* 专项 3: tinydir_open + 迭代（覆盖上游未测的目录枚举路径） */
    {
        tinydir_dir dir;
        int r = tinydir_open(&dir, testdir);
        CHECK(r == 0, "tinydir_open(testdir)");
        if (r == 0) {
            int count = 0;
            int found_alpha = 0, found_beta = 0;
            while (dir.has_next) {
                tinydir_file file;
                r = tinydir_readfile(&dir, &file);
                CHECK(r == 0, "tinydir_readfile");
                if (strcmp(file.name, "alpha.txt") == 0) found_alpha = 1;
                if (strcmp(file.name, "Beta.dat") == 0) found_beta = 1;
                printf("    entry: %s%s\n", file.name, file.is_dir ? "/" : "");
                ++count;
                tinydir_next(&dir);
            }
            tinydir_close(&dir);
            /* tinydir 1.2.4 不跳过 "." 与 ".."，共 4 个条目 */
            CHECK(count == 4, "iterated 4 entries (. .. alpha.txt Beta.dat)");
            CHECK(found_alpha == 1, "found alpha.txt");
            CHECK(found_beta == 1, "found Beta.dat");
        }
    }

    /* 专项 4: tinydir_open_sorted + readfile_n（排序读取） */
    {
        tinydir_dir dir;
        int r = tinydir_open_sorted(&dir, testdir);
        CHECK(r == 0, "tinydir_open_sorted(testdir)");
        if (r == 0) {
            int n = (int)dir.n_files;
            /* 同样包含 . 与 ..：Beta.dat 排在 index 2，alpha.txt 在 index 3 */
            CHECK(n == 4, "n_files == 4 (. .. Beta.dat alpha.txt)");
            if (n >= 4) {
                tinydir_file f0, f1, f2, f3;
                r = tinydir_readfile_n(&dir, &f0, 0);
                CHECK(r == 0 && strcmp(f0.name, ".") == 0, "sorted[0] is .");
                r = tinydir_readfile_n(&dir, &f1, 1);
                CHECK(r == 0 && strcmp(f1.name, "..") == 0, "sorted[1] is ..");
                r = tinydir_readfile_n(&dir, &f2, 2);
                CHECK(r == 0 && strcmp(f2.name, "Beta.dat") == 0,
                      "sorted[2] is Beta.dat");
                r = tinydir_readfile_n(&dir, &f3, 3);
                CHECK(r == 0 && strcmp(f3.name, "alpha.txt") == 0,
                      "sorted[3] is alpha.txt");
            }
            tinydir_close(&dir);
        }
    }

    /* 专项 5: tinydir_file_open —— 扩展名提取 */
    {
        tinydir_file file;
        int r = tinydir_file_open(&file, file_a);
        CHECK(r == 0, "tinydir_file_open(alpha.txt)");
        if (r == 0) {
            printf("    name=%s ext=%s\n", file.name, file.extension);
            CHECK(strcmp(file.name, "alpha.txt") == 0, "file name alpha.txt");
            CHECK(strcmp(file.extension, "txt") == 0, "extension txt");
            CHECK(file.is_dir == 0, "is_dir == 0");
        }
    }

    /* 专项 6: 子目录导航 open_subdir_n */
    {
        char subdir[4096];
        snprintf(subdir, sizeof(subdir), "%s/sub", testdir);
        CHECK(mkdir(subdir, 0700) == 0 || errno == EEXIST, "OHOS mkdir sub");
        tinydir_dir dir;
        int sub_idx = -1;
        if (tinydir_open_sorted(&dir, testdir) == 0) {
            int i;
            for (i = 0; i < (int)dir.n_files; ++i) {
                tinydir_file f;
                if (tinydir_readfile_n(&dir, &f, (size_t)i) == 0 && f.is_dir) {
                    sub_idx = i;
                    break;
                }
            }
            if (sub_idx >= 0) {
                int r = tinydir_open_subdir_n(&dir, (size_t)sub_idx);
                CHECK(r == 0, "tinydir_open_subdir_n(sub)");
                if (r == 0) {
                    printf("    subdir opened: %s\n", dir.path);
                }
            }
            tinydir_close(&dir);
            CHECK(sub_idx >= 0, "subdir found via open_sorted");
        }
        rmdir(subdir);
    }

    /* 清理 */
    unlink(file_a);
    unlink(file_b);
    rmdir(testdir);

    printf("\n结果: %s\n", failures == 0 ? "全部通过" : "存在失败");
    return failures == 0 ? 0 : 1;
}
