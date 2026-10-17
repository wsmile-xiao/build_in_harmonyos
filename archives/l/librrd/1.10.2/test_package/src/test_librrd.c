// test_librrd.c — 消费者视角验证 librrd API，覆盖被适配修改的核心路径：
//   rrd_create()  -> 0004 补丁（rrd_create.c 无 glib 最小 GList + 0005 pcre 正则校验）
//   rrd_update()  -> 0007 补丁（rrd_update.c GTree 缓存条件化，无 glib 直接读文件）
//   rrd_fetch()   -> 验证写入的数据可读回（覆盖库核心读写链路）
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <rrd.h>

#define TEST_RRD "test_librrd.rrd"

static int check_error(const char *step) {
    if (rrd_test_error()) {
        printf("  ✗ %s 失败: %s\n", step, rrd_get_error());
        rrd_clear_error();
        return 1;
    }
    printf("  ✓ %s\n", step);
    return 0;
}

int main() {
    int passed = 0, failed = 0;
    printf("librrd Test Suite\n");
    printf("================\n\n");

    /* Test 1: rrd_strversion() — 获取版本号验证库已加载 */
    printf("Test 1: rrd_strversion\n");
    const char *ver = rrd_strversion();
    if (ver != NULL && ver[0] != '\0') {
        printf("  ✓ librrd version: %s\n", ver);
        passed++;
    } else {
        printf("  ✗ rrd_strversion returned NULL/empty\n");
        failed++;
    }

    /* Test 2: rrd_version() — 数值版本号 */
    printf("Test 2: rrd_version\n");
    double num_ver = rrd_version();
    if (num_ver > 0.0) {
        printf("  ✓ librrd numeric version: %.2f\n", num_ver);
        passed++;
    } else {
        printf("  ✗ rrd_version returned %f\n", num_ver);
        failed++;
    }

    /* Test 3: rrd_create() — 实际创建 RRD 文件
     * 走 rrd_create.c 的 sources 链表（0004 最小 GList 替代 glib GList）
     * 和 DS 定义正则校验（0005 pcre 分支，无 glib 时用 pcre_compile） */
    printf("Test 3: rrd_create\n");
    remove(TEST_RRD);
    const char *create_argv[] = {
        "create", TEST_RRD,
        "--start", "1000000000",
        "--step", "300",
        "DS:temp:GAUGE:600:0:100",
        "RRA:AVERAGE:0.5:1:12",
    };
    int rc = rrd_create(8, create_argv);
    if (rc == 0 && !rrd_test_error()) {
        printf("  ✓ rrd_create 创建 RRD 文件成功\n");
        passed++;
    } else {
        printf("  ✗ rrd_create 失败 rc=%d: %s\n", rc, rrd_get_error());
        rrd_clear_error();
        failed++;
    }

    /* Test 4: rrd_update() — 写入一个数据点
     * 走 rrd_update.c 的模板缓存路径（0007 无 glib 时跳过 GTree 直接读文件） */
    printf("Test 4: rrd_update\n");
    const char *update_argv[] = {
        "update", TEST_RRD,
        "1000000300:25",   /* start(1000000000) + step(300) = 第一个 PDP 时间点 */
    };
    rc = rrd_update(3, update_argv);
    if (rc == 0 && !rrd_test_error()) {
        printf("  ✓ rrd_update 写入数据成功\n");
        passed++;
    } else {
        printf("  ✗ rrd_update 失败 rc=%d: %s\n", rc, rrd_get_error());
        rrd_clear_error();
        failed++;
    }

    /* Test 5: rrd_fetch() — 读回数据验证写入生效 */
    printf("Test 5: rrd_fetch\n");
    time_t start, end;
    unsigned long step, ds_cnt, i;
    rrd_value_t *data = NULL;
    char **ds_namv = NULL;
    const char *fetch_argv[] = {
        "fetch", TEST_RRD, "AVERAGE",
        "--start", "1000000000",
        "--end", "1000000300",
    };
    rc = rrd_fetch(7, fetch_argv, &start, &end, &step, &ds_cnt, &ds_namv, &data);
    if (rc == 0 && !rrd_test_error() && ds_cnt > 0 && data != NULL) {
        /* 找第一个非 NaN 的数据点（应为写入的 25） */
        rrd_value_t found = 0.0;
        int found_flag = 0;
        long n = (long)((end - start) / step) + 1;
        if (n < 1) n = 1;
        for (i = 0; i < (unsigned long)n * ds_cnt; i++) {
            if (!isnan(data[i])) {
                found = data[i];
                found_flag = 1;
                break;
            }
        }
        if (found_flag) {
            printf("  ✓ rrd_fetch 读回数据: ds=%s 值=%.1f (期望 25.0)\n",
                   ds_namv[0], (double)found);
            if ((double)found > 24.0 && (double)found < 26.0) {
                passed++;
            } else {
                printf("  ✗ rrd_fetch 数据值不符: %.1f\n", (double)found);
                failed++;
            }
        } else {
            printf("  ✗ rrd_fetch 未读到有效数据点\n");
            failed++;
        }
        for (i = 0; i < ds_cnt; i++)
            free(ds_namv[i]);
        free(ds_namv);
        free(data);
    } else {
        printf("  ✗ rrd_fetch 失败 rc=%d: %s\n", rc, rrd_get_error());
        rrd_clear_error();
        failed++;
    }

    remove(TEST_RRD);

    printf("\n========== Summary ==========\n");
    printf("Tests: %d passed, %d failed\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
