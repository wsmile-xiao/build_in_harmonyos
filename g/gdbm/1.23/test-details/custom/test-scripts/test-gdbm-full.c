/* test-gdbm-full.c - 完整的 GDBM 功能测试 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gdbm.h>

int main(void)
{
    GDBM_FILE dbf;
    datum key, value, result;
    const char *db_path = "/storage/Users/currentUser/build/gdbm/test_full.db";
    
    printf("=== GDBM Full Function Test ===\n\n");

    /* 测试 1: 打开/创建数据库 */
    printf("Test 1: Create/Open database... ");
    dbf = gdbm_open(db_path, 0, GDBM_WRCREAT | GDBM_NEWDB, 0644, NULL);
    if (dbf) {
        printf("PASS\n");
    } else {
        printf("FAIL (%s)\n", gdbm_strerror(gdbm_errno));
        return 1;
    }

    /* 测试 2: 存储多个键值对 */
    printf("Test 2: Store multiple key-value pairs... ");
    int store_count = 0;
    for (int i = 0; i < 10; i++) {
        char kbuf[32], vbuf[32];
        snprintf(kbuf, sizeof(kbuf), "key_%d", i);
        snprintf(vbuf, sizeof(vbuf), "value_%d", i * 100);
        
        key.dptr = kbuf;
        key.dsize = strlen(kbuf) + 1;
        value.dptr = vbuf;
        value.dsize = strlen(vbuf) + 1;
        
        if (gdbm_store(dbf, key, value, GDBM_REPLACE) == 0) {
            store_count++;
        }
    }
    if (store_count == 10) {
        printf("PASS (stored %d pairs)\n", store_count);
    } else {
        printf("FAIL (only stored %d pairs)\n", store_count);
    }

    /* 测试 3: 读取键值对 */
    printf("Test 3: Fetch values... ");
    int fetch_count = 0;
    for (int i = 0; i < 10; i++) {
        char kbuf[32];
        snprintf(kbuf, sizeof(kbuf), "key_%d", i);
        
        key.dptr = kbuf;
        key.dsize = strlen(kbuf) + 1;
        
        result = gdbm_fetch(dbf, key);
        if (result.dptr) {
            fetch_count++;
            free(result.dptr);
        }
    }
    if (fetch_count == 10) {
        printf("PASS (fetched %d pairs)\n", fetch_count);
    } else {
        printf("FAIL (only fetched %d pairs)\n", fetch_count);
    }

    /* 测试 4: 验证值内容 */
    printf("Test 4: Verify value content... ");
    key.dptr = "key_5";
    key.dsize = strlen(key.dptr) + 1;
    result = gdbm_fetch(dbf, key);
    if (result.dptr && strcmp(result.dptr, "value_500") == 0) {
        printf("PASS (key_5 = %s)\n", result.dptr);
    } else {
        printf("FAIL (got: %s)\n", result.dptr ? result.dptr : "(null)");
    }
    if (result.dptr) free(result.dptr);

    /* 测试 5: 删除键值对 */
    printf("Test 5: Delete a key... ");
    key.dptr = "key_3";
    key.dsize = strlen(key.dptr) + 1;
    if (gdbm_delete(dbf, key) == 0) {
        result = gdbm_fetch(dbf, key);
        if (result.dptr == NULL) {
            printf("PASS (key_3 deleted)\n");
        } else {
            printf("FAIL (key still exists)\n");
            free(result.dptr);
        }
    } else {
        printf("FAIL (delete returned error)\n");
    }

    /* 测试 6: 遍历所有键 */
    printf("Test 6: Iterate all keys... ");
    int key_count = 0;
    key = gdbm_firstkey(dbf);
    while (key.dptr) {
        key_count++;
        datum next = gdbm_nextkey(dbf, key);
        free(key.dptr);
        key = next;
    }
    if (key_count == 9) {  // 10 - 1 deleted = 9
        printf("PASS (found %d keys)\n", key_count);
    } else {
        printf("FAIL (found %d keys, expected 9)\n", key_count);
    }

    /* 测试 7: 检查键是否存在 */
    printf("Test 7: Check key existence... ");
    key.dptr = "key_0";
    key.dsize = strlen(key.dptr) + 1;
    if (gdbm_exists(dbf, key)) {
        printf("PASS (key_0 exists)\n");
    } else {
        printf("FAIL (key_0 not found)\n");
    }

    /* 测试 8: 关闭数据库 */
    printf("Test 8: Close database... ");
    gdbm_close(dbf);
    printf("PASS\n");

    /* 测试 9: 重新打开只读 */
    printf("Test 9: Reopen read-only... ");
    dbf = gdbm_open(db_path, 0, GDBM_READER, 0444, NULL);
    if (dbf) {
        printf("PASS\n");
        
        /* 测试 10: 只读模式下读取 */
        printf("Test 10: Read from read-only database... ");
        key.dptr = "key_0";
        key.dsize = strlen(key.dptr) + 1;
        result = gdbm_fetch(dbf, key);
        if (result.dptr && strcmp(result.dptr, "value_0") == 0) {
            printf("PASS\n");
        } else {
            printf("FAIL\n");
        }
        if (result.dptr) free(result.dptr);
        
        gdbm_close(dbf);
    } else {
        printf("FAIL (%s)\n", gdbm_strerror(gdbm_errno));
    }

    /* 清理测试文件 */
    remove(db_path);

    printf("\n=== All tests completed ===\n");
    return 0;
}