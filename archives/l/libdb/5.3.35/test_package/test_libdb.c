/*
 * libdb/5.3.35 consumer test — drives the real Berkeley DB C API against the
 * packaged artifact (a functional test, not a symbol probe).
 *
 * 断言分四段，全部落在可观测行为上：
 *   A. 版本同一性：db.h 的编译期宏 == 运行库字符串 == 5.3.35。
 *      db.h 由 dist/meson/gen_header.py 从 dist/meson/db_subs.json 渲染，而
 *      运行时的 db_version()/db_full_version()（src/env/env_open.c）返回的正是
 *      编译进库的同一批宏。两边都报 5.3.35，才说明「头文件与库本体出自同一次
 *      构建」，也就是本配方 patches/0001 真的生效了；未打补丁时 db_subs.json
 *      停在 5.3.29，这里必然报 29。
 *   B. 引擎可用：DbEnv(DB_INIT_LOCK|DB_INIT_MPOOL) + B-tree 增删查 + 游标全表
 *      枚举。BDB 的 latch/mutex 直接建立在 POSIX 线程之上（配方
 *      cpp_info.system_libs = ["pthread"]），DB_INIT_LOCK 会真正实例化锁表，
 *      所以 env 打开成功即证明 pthread 已随库正确链接进 OHOS 进程。
 *   C. 鸿蒙特有：DB_THREAD 下的多线程并发写入。OHOS 的 libc 把 pthread 合并
 *      进 libc（无独立 libpthread.so），库侧若少声明 system_libs=["pthread"]，
 *      静态库消费方链接期就会缺 pthread_* 符号、而动态库消费方则要到运行时才
 *      暴露；上游 Meson 注册的三个 tier（test_iso_anomaly 是单线程确定性调度
 *      器、lock_matrix 与 soak_resources 都单线程跑）没有一项做过多线程 API
 *      并发，这段断言补的就是这个缺口。并发写完后按游标计数校验零丢失。
 *   D. 持久化 + 错误路径确定性：关掉 DbEnv/DB 后重新打开文件，数据仍在，且
 *      文件在 OHOS 文件系统上真实存在、非空 —— 排除「只在进程内存里跑通」的
 *      假阳性；非法 open 标志组合必须返回确定的负错误码（EINVAL）而不是崩溃
 *      或静默继续。
 */
#include <db.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define DBPATH "libdb_probe.db"
#define NRECORDS 256
#define NTHREADS 4

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "FAIL: %s\n", (msg));                              \
            return 1;                                                          \
        }                                                                      \
        printf("ok - %s\n", (msg));                                            \
    } while (0)

static void make_dbt(DBT *dbt, const char *s)
{
    memset(dbt, 0, sizeof(*dbt));
    dbt->data = (void *)s;
    dbt->size = (u_int32_t)strlen(s) + 1;
}

/* one key/value pair, numbered */
static int put_record(DB *dbp, int i)
{
    char kb[32], vb[32];
    DBT key, data;

    snprintf(kb, sizeof(kb), "key-%03d", i);
    snprintf(vb, sizeof(vb), "value-%03d", i);
    make_dbt(&key, kb);
    make_dbt(&data, vb);
    return dbp->put(dbp, NULL, &key, &data, 0);
}

typedef struct {
    DB *dbp;
    int base;
    int count;
    int rc;
} thread_arg;

static void *writer(void *arg)
{
    thread_arg *t = (thread_arg *)arg;
    int i;

    t->rc = 0;
    for (i = 0; i < t->count; i++) {
        if (put_record(t->dbp, t->base + i) != 0) {
            t->rc = 1;
            break;
        }
    }
    return NULL;
}

int main(void)
{
    DB_ENV *env = NULL;
    DB *dbp = NULL, *nodir = NULL;
    DBC *cursor = NULL;
    DBT key, data;
    pthread_t th[NTHREADS];
    thread_arg ta[NTHREADS];
    struct stat st;
    const char *vs, *fs;
    int ret, major, minor, patch, family, rel, count, i;

    /* ---- A. 版本同一性 -------------------------------------------------- */
    CHECK(DB_VERSION_MAJOR == 5 && DB_VERSION_MINOR == 3 &&
              DB_VERSION_PATCH == 35,
          "compile-time macros report 5.3.35");
    CHECK(strstr(DB_VERSION_STRING, "5.3.35") != NULL,
          "DB_VERSION_STRING names the 5.3.35 release");

    major = minor = patch = 0;
    vs = db_version(&major, &minor, &patch);
    printf("info - db_version() -> %d.%d.%d / %s\n", major, minor, patch, vs);
    CHECK(major == 5 && minor == 3 && patch == 35,
          "db_version() agrees with the header at 5.3.35");
    CHECK(vs != NULL && strstr(vs, "5.3.35") != NULL,
          "db_version() returns the 5.3.35 version string");

    family = rel = 0;
    fs = db_full_version(&family, &rel, &major, &minor, &patch);
    printf("info - db_full_version() -> %dg R%d %d.%d.%d / %s\n", family, rel,
           major, minor, patch, fs);
    CHECK(family == 11 && rel == 2,
          "db_full_version() reports the 11g Release 2 family");
    CHECK(fs != NULL && strstr(fs, "11.2.5.3.35") != NULL,
          "db_full_version() carries the 5.3.35 patch level");

    /* ---- B. 引擎可用（pthread 已链接） ----------------------------------- */
    (void)remove(DBPATH);

    ret = db_env_create(&env, 0);
    CHECK(ret == 0 && env != NULL, "db_env_create returned an environment");

    ret = env->open(env, ".", DB_INIT_LOCK | DB_INIT_MPOOL | DB_THREAD |
                                     DB_CREATE | DB_PRIVATE,
                    0);
    CHECK(ret == 0, "DbEnv open with DB_INIT_LOCK succeeded (pthread linked)");

    ret = db_create(&dbp, env, 0);
    CHECK(ret == 0 && dbp != NULL, "db_create returned a handle");

    ret = dbp->open(dbp, NULL, DBPATH, NULL, DB_BTREE,
                    DB_CREATE | DB_THREAD, 0);
    CHECK(ret == 0, "DB->open created a B-tree database");

    for (i = 0; i < NRECORDS / 2; i++)
        if (put_record(dbp, i) != 0) {
            fprintf(stderr, "FAIL: put #%d returned an error\n", i);
            return 1;
        }
    printf("ok - stored %d records on the calling thread\n", NRECORDS / 2);

    /* ---- C. 鸿蒙特有：多线程并发写入 ------------------------------------- */
    for (i = 0; i < NTHREADS; i++) {
        ta[i].dbp = dbp;
        ta[i].base = NRECORDS / 2 + i * (NRECORDS / 2 / NTHREADS);
        ta[i].count = NRECORDS / 2 / NTHREADS;
        ta[i].rc = -1;
        ret = pthread_create(&th[i], NULL, writer, &ta[i]);
        if (ret != 0) {
            fprintf(stderr, "FAIL: pthread_create #%d failed\n", i);
            return 1;
        }
    }
    for (i = 0; i < NTHREADS; i++) {
        ret = pthread_join(th[i], NULL);
        CHECK(ret == 0, "concurrent writer thread joined");
    }
    for (i = 0; i < NTHREADS; i++)
        CHECK(ta[i].rc == 0,
              "concurrent writer thread committed its key range");
    printf("ok - %d threads x %d records written concurrently\n", NTHREADS,
           NRECORDS / 2 / NTHREADS);

    /* ---- 读回 + 游标枚举 ------------------------------------------------- */
    /* DB_THREAD 的库上 DB->get 必须给 data DBT 一个内存分配标志：
       src/db/db_iface.c 的 __dbt_ferr() 对 DB->get 的 data 参数带
       check_thread=1，而 DB_IS_THREADED(dbp) 为真时若标志里既没有
       DB_DBT_MALLOC/DB_DBT_REALLOC，也没有 DB_DBT_USERMEM/DB_DBT_USERCOPY/
       DB_DBT_READONLY，就直接 __db_errx() 报 DB_STR "0630/DB_THREAD mandates
       memory allocation flag on data DBT" 并返回 EINVAL —— 线程态下不许把
       指向库内部缓冲区的指针交回调用方。用 DB_DBT_MALLOC 让库自己拷一份，
       用完 free()。 */
    make_dbt(&key, "key-042");
    memset(&data, 0, sizeof(data));
    data.flags = DB_DBT_MALLOC;
    ret = dbp->get(dbp, NULL, &key, &data, 0);
    CHECK(ret == 0, "point lookup found key-042");
    CHECK(data.size == sizeof("value-042") &&
              memcmp(data.data, "value-042", data.size) == 0,
          "point lookup returned the exact stored value");
    free(data.data);

    /* 游标这条路不需要：__dbc_get_arg() 传给 __dbt_ferr() 的 check_thread
       是 0（key 与 data 都是），所以把标志清回 0，让游标按常规返回内部
       指针（下次游标操作前有效），避免逐条 malloc 造成泄漏。 */
    memset(&data, 0, sizeof(data));
    memset(&key, 0, sizeof(key));

    ret = dbp->cursor(dbp, NULL, &cursor, 0);
    CHECK(ret == 0 && cursor != NULL, "DB->cursor returned a cursor");

    count = 0;
    while ((ret = cursor->get(cursor, &key, &data, DB_NEXT)) == 0)
        count++;
    cursor->close(cursor);
    cursor = NULL;
    CHECK(ret == DB_NOTFOUND, "cursor walk ended at DB_NOTFOUND");
    CHECK(count == NRECORDS,
          "cursor enumerated every record written (none lost)");

    /* ---- D. 持久化到 OHOS 文件系统 --------------------------------------- */
    ret = dbp->close(dbp, 0);
    CHECK(ret == 0, "DB->close flushed the database");
    dbp = NULL;
    ret = env->close(env, 0);
    CHECK(ret == 0, "DbEnv close released the region");
    env = NULL;

    CHECK(stat(DBPATH, &st) == 0 && st.st_size > 0,
          "database file exists on disk with non-zero size");

    ret = db_env_create(&env, 0);
    CHECK(ret == 0, "second db_env_create succeeded");
    ret = env->open(env, ".",
                    DB_INIT_LOCK | DB_INIT_MPOOL | DB_CREATE | DB_PRIVATE, 0);
    CHECK(ret == 0, "second DbEnv open succeeded");

    ret = db_create(&dbp, env, 0);
    CHECK(ret == 0, "second db_create succeeded");
    ret = dbp->open(dbp, NULL, DBPATH, NULL, DB_BTREE, DB_RDONLY, 0);
    CHECK(ret == 0, "reopened the existing database read-only");

    make_dbt(&key, "key-200");
    memset(&data, 0, sizeof(data));
    ret = dbp->get(dbp, NULL, &key, &data, 0);
    CHECK(ret == 0 && data.size == sizeof("value-200") &&
              memcmp(data.data, "value-200", data.size) == 0,
          "reopened database still holds a thread-written record");

    make_dbt(&key, "key-does-not-exist");
    memset(&data, 0, sizeof(data));
    ret = dbp->get(dbp, NULL, &key, &data, 0);
    CHECK(ret == DB_NOTFOUND, "a missing key is reported as DB_NOTFOUND");

    ret = dbp->close(dbp, 0);
    CHECK(ret == 0, "second DB->close succeeded");
    dbp = NULL;

    /* 错误路径必须是确定的负错误码，不能崩溃或静默成功。非法标志组合由
       src/db/db_iface.c:__db_open_arg 的组合检查拦下并返回 EINVAL
       （DB_RDONLY 与 DB_CREATE 互斥），与文件系统状态无关，可确定性判定。 */
    ret = db_create(&nodir, env, 0);
    CHECK(ret == 0, "db_create for the negative path succeeded");
    ret = nodir->open(nodir, NULL, "illegal-flags.db", NULL, DB_BTREE,
                      DB_CREATE | DB_RDONLY, 0);
    CHECK(ret == EINVAL,
          "an illegal open flag combination is rejected with EINVAL");
    nodir->close(nodir, 0);
    nodir = NULL;

    ret = env->close(env, 0);
    CHECK(ret == 0, "second DbEnv close succeeded");
    env = NULL;

    (void)remove(DBPATH);

    printf("all libdb/5.3.35 consumer assertions passed\n");
    return 0;
}
