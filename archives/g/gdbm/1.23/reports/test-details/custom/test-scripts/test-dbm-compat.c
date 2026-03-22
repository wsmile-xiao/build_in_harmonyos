/* test-dbm-compat.c - 测试 GDBM 兼容库 (dbm/ndbm 接口) */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <ndbm.h>  /* 兼容库头文件 */

int main(void)
{
    DBM *db;
    datum key, value, result;
    const char *db_path = "/storage/Users/currentUser/build/gdbm/test_dbm";
    
    printf("=== DBM/NDBM Compatibility Test ===\n\n");

    /* 测试 1: 打开/创建数据库 */
    printf("Test 1: dbm_open/create... ");
    db = dbm_open(db_path, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (db) {
        printf("PASS\n");
    } else {
        printf("FAIL\n");
        return 1;
    }

    /* 测试 2: 存储键值对 */
    printf("Test 2: dbm_store... ");
    int store_ok = 1;
    for (int i = 0; i < 5; i++) {
        char kbuf[32], vbuf[32];
        snprintf(kbuf, sizeof(kbuf), "ndbm_key_%d", i);
        snprintf(vbuf, sizeof(vbuf), "ndbm_value_%d", i * 10);
        
        key.dptr = kbuf;
        key.dsize = strlen(kbuf);
        value.dptr = vbuf;
        value.dsize = strlen(vbuf);
        
        if (dbm_store(db, key, value, DBM_INSERT) != 0) {
            store_ok = 0;
        }
    }
    printf("%s\n", store_ok ? "PASS" : "FAIL");

    /* 测试 3: 读取键值对 */
    printf("Test 3: dbm_fetch... ");
    key.dptr = "ndbm_key_2";
    key.dsize = strlen(key.dptr);
    result = dbm_fetch(db, key);
    if (result.dptr && strncmp(result.dptr, "ndbm_value_20", result.dsize) == 0) {
        printf("PASS\n");
    } else {
        printf("FAIL\n");
    }

    /* 测试 4: 删除键值对 */
    printf("Test 4: dbm_delete... ");
    key.dptr = "ndbm_key_1";
    key.dsize = strlen(key.dptr);
    if (dbm_delete(db, key) == 0) {
        result = dbm_fetch(db, key);
        if (result.dptr == NULL) {
            printf("PASS\n");
        } else {
            printf("FAIL (key still exists)\n");
        }
    } else {
        printf("FAIL (delete error)\n");
    }

    /* 测试 5: 遍历键 */
    printf("Test 5: dbm_firstkey/dbm_nextkey... ");
    int count = 0;
    for (key = dbm_firstkey(db); key.dptr; key = dbm_nextkey(db)) {
        count++;
    }
    printf("%s (found %d keys, expected 4)\n", count == 4 ? "PASS" : "FAIL", count);

    /* 测试 6: 错误处理 */
    printf("Test 6: dbm_error/dbm_clearerr... ");
    if (dbm_error(db) == 0) {
        printf("PASS (no errors)\n");
    } else {
        dbm_clearerr(db);
        printf("WARN (errors cleared)\n");
    }

    /* 测试 7: 关闭数据库 */
    printf("Test 7: dbm_close... ");
    dbm_close(db);
    printf("PASS\n");

    /* 测试 8: 以只读模式重新打开 */
    printf("Test 8: dbm_open read-only... ");
    db = dbm_open(db_path, O_RDONLY, 0);
    if (db) {
        key.dptr = "ndbm_key_0";
        key.dsize = strlen(key.dptr);
        result = dbm_fetch(db, key);
        if (result.dptr) {
            printf("PASS\n");
        } else {
            printf("FAIL (can't read)\n");
        }
        dbm_close(db);
    } else {
        printf("FAIL (can't open read-only)\n");
    }

    /* 清理 */
    char path_buf[256];
    snprintf(path_buf, sizeof(path_buf), "%s.dir", db_path);
    remove(path_buf);
    snprintf(path_buf, sizeof(path_buf), "%s.pag", db_path);
    remove(path_buf);

    printf("\n=== DBM compatibility tests completed ===\n");
    return 0;
}