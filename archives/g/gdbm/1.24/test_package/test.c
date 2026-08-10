/* gdbm 1.24 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 存取得对。这里真的建一个数据库文件、
 * 写入、读回、删除、再确认删掉了，全程逐字节对账。
 *
 * 覆盖：① 存取往返 ② INSERT 拒绝覆盖 / REPLACE 生效 ③ 遍历计数
 *      ④ 删除后确实取不到 ⑤ 取不存在的键返回空且不崩溃
 *      ⑥ 关闭后重开复验 —— 数据必须真的落盘，只在内存里对不算数
 *
 * ⚠️ 资源清理：gdbm_fetch 返回的 datum.dptr 是 malloc 出来的，调用方必须 free。
 * 所有出口（含错误路径）统一走 fail 标签，避免漏释放 —— 早先版本在 5 条错误
 * 返回路径上直接 return，泄漏了 dptr，也没关库、没删临时文件（MR 检视实撞）。
 * free(NULL) 由 C 标准保证安全，无需判空。
 */
#include <gdbm.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PATH "gdbm_test_tmp.db"

static datum mk(const char *s)
{
    datum d;
    d.dptr = (char *)s;
    d.dsize = (int)strlen(s);
    return d;
}

static int eq(datum d, const char *s)
{
    return d.dptr && d.dsize == (int)strlen(s) && memcmp(d.dptr, s, d.dsize) == 0;
}

int main(void)
{
    GDBM_FILE db = NULL;
    datum v = {NULL, 0};
    int rc = 1;                 /* 默认失败，只有走到最后才置 0 */

    remove(PATH);
    db = gdbm_open(PATH, 0, GDBM_NEWDB, 0644, NULL);
    if (!db) {
        printf("FAIL gdbm_open(NEWDB) 失败: %s\n", gdbm_strerror(gdbm_errno));
        goto fail;
    }

    /* ① 存取往返 */
    if (gdbm_store(db, mk("alpha"), mk("first"), GDBM_INSERT) != 0) {
        printf("FAIL store alpha: %s\n", gdbm_strerror(gdbm_errno));
        goto fail;
    }
    if (gdbm_store(db, mk("beta"), mk("second"), GDBM_INSERT) != 0) {
        printf("FAIL store beta: %s\n", gdbm_strerror(gdbm_errno));
        goto fail;
    }
    v = gdbm_fetch(db, mk("alpha"));
    if (!eq(v, "first")) {
        printf("FAIL fetch alpha = [%.*s]，期望 first\n", v.dsize, v.dptr ? v.dptr : "");
        goto fail;
    }
    free(v.dptr); v.dptr = NULL;

    /* ② INSERT 不得覆盖已有键；REPLACE 才可以 */
    if (gdbm_store(db, mk("alpha"), mk("nope"), GDBM_INSERT) != 1) {
        printf("FAIL INSERT 对已存在的键应返回 1（拒绝覆盖）\n");
        goto fail;
    }
    if (gdbm_store(db, mk("alpha"), mk("updated"), GDBM_REPLACE) != 0) {
        printf("FAIL REPLACE alpha 失败\n");
        goto fail;
    }
    v = gdbm_fetch(db, mk("alpha"));
    if (!eq(v, "updated")) {
        printf("FAIL REPLACE 后 alpha = [%.*s]，期望 updated\n",
               v.dsize, v.dptr ? v.dptr : "");
        goto fail;
    }
    free(v.dptr); v.dptr = NULL;

    /* ③ 遍历必须拿到两个键 */
    {
        int n = 0;
        datum k = gdbm_firstkey(db);
        while (k.dptr) {
            datum nk = gdbm_nextkey(db, k);
            free(k.dptr);
            k = nk;
            ++n;
        }
        if (n != 2) {
            printf("FAIL 遍历得到 %d 个键，期望 2\n", n);
            goto fail;
        }
    }

    /* ④ 删除后确实取不到 */
    if (gdbm_delete(db, mk("beta")) != 0) {
        printf("FAIL delete beta 失败\n");
        goto fail;
    }
    v = gdbm_fetch(db, mk("beta"));
    if (v.dptr) {
        printf("FAIL beta 已删除却仍能取到\n");
        goto fail;
    }

    /* ⑤ 取不存在的键：返回空指针，不得崩溃也不得假装成功 */
    v = gdbm_fetch(db, mk("no_such_key_9f3a"));
    if (v.dptr) {
        printf("FAIL 取不存在的键竟然返回了数据\n");
        goto fail;
    }

    gdbm_close(db);
    db = NULL;

    /* ⑥ 重开只读复验 —— 数据必须真的落盘，只在内存里对不算数 */
    db = gdbm_open(PATH, 0, GDBM_READER, 0644, NULL);
    if (!db) {
        printf("FAIL 重新打开失败: %s\n", gdbm_strerror(gdbm_errno));
        goto fail;
    }
    v = gdbm_fetch(db, mk("alpha"));
    if (!eq(v, "updated")) {
        printf("FAIL 重开后 alpha = [%.*s]，期望 updated（数据没落盘）\n",
               v.dsize, v.dptr ? v.dptr : "");
        goto fail;
    }

    printf("gdbm OK: 存取往返/INSERT 拒覆盖/REPLACE/遍历/删除/错误路径/落盘复验 共 7 组；版本 %s\n",
           gdbm_version);
    rc = 0;

fail:
    free(v.dptr);               /* free(NULL) 安全，无需判空 */
    if (db) gdbm_close(db);
    remove(PATH);
    return rc;
}
