/* test-gdbm-api.c - 测试 GDBM 库的核心 API */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gdbm.h>

int main(void)
{
    GDBM_FILE dbf;
    datum key, value, result;
    int test_passed = 0;
    int test_failed = 0;

    printf("Testing GDBM API functions...\n");

    /* 测试 1: 打开/创建数据库 */
    printf("  Test 1: Open database... ");
    dbf = gdbm_open("/tmp/test_gdbm_api.db", 0, GDBM_WRCREAT, 0644, NULL);
    if (dbf) {
        printf("PASS\n");
        test_passed++;
    } else {
        printf("FAIL (%s)\n", gdbm_strerror(gdbm_errno));
        test_failed++;
        return 1;
    }

    /* 测试 2: 存储键值对 */
    printf("  Test 2: Store key-value pair... ");
    key.dptr = "test_key";
    key.dsize = strlen(key.dptr) + 1;
    value.dptr = "test_value";
    value.dsize = strlen(value.dptr) + 1;

    if (gdbm_store(dbf, key, value, GDBM_INSERT) == 0) {
        printf("PASS\n");
        test_passed++;
    } else {
        printf("FAIL\n");
        test_failed++;
    }

    /* 测试 3: 读取键值对 */
    printf("  Test 3: Fetch value by key... ");
    result = gdbm_fetch(dbf, key);
    if (result.dptr != NULL) {
        printf("PASS\n");
        test_passed++;
    } else {
        printf("FAIL\n");
        test_failed++;
    }

    /* 测试 4: 验证值内容 */
    printf("  Test 4: Verify value content... ");
    if (result.dptr && strcmp(result.dptr, "test_value") == 0) {
        printf("PASS\n");
        test_passed++;
    } else {
        printf("FAIL (got: %s)\n", result.dptr ? result.dptr : "(null)");
        test_failed++;
    }

    /* 释放结果 */
    if (result.dptr) {
        free(result.dptr);
    }

    /* 测试 5: 关闭数据库 */
    printf("  Test 5: Close database... ");
    gdbm_close(dbf);
    printf("PASS\n");
    test_passed++;

    /* 清理测试文件 */
    remove("/tmp/test_gdbm_api.db");

    /* 输出结果 */
    printf("\nResults: %d passed, %d failed\n", test_passed, test_failed);

    if (test_failed == 0) {
        printf("All API tests passed!\n");
        return 0;
    } else {
        printf("Some tests failed!\n");
        return 1;
    }
}