/* test_package 端到端消费者用例（鸿蒙特有测试）— genht 1.1.3 / HarmonyOS PC.
 *
 * 这是**完整消费者用例**，不是断言集合：构造输入 → 真实执行 → 产出结果 → 校验内容
 *
 *   1) 构造输入：内嵌 13 行访问日志语料（user / path / bytes），固定不变；
 *   2) 真实执行：以 genht 为索引引擎跑完整条流水线 ——
 *        · htsi ×2 ：path→累计字节、path→命中次数（读改写累加）
 *        · htss    ：user→最近访问路径（覆盖写，表示"最新状态"）
 *        · htpp    ：驻留后的 user 名指针→struct user（指针键索引，流水线热路径
 *                    的每次用户查找都走它，不是旁路装饰）
 *        · htip    ：请求 id(long)→struct request（注册表）
 *        · siphash24：整段语料的确定性校验码
 *      随后执行真实运维动作：下线一个资源（含幂等二次删除）、再灌入 2000 条
 *      合成路径触发多轮扩容、按下标删一半，并用 length/get 复核最终状态。
 *   3) 产出结果：显式排序（qsort，不依赖哈希序）生成确定性文本报告；
 *   4) 校验内容：报告与内嵌参考输出 GOLDEN 逐字节比对，并复核语义不变量
 *      （唯一路径数、总字节、每用户命中数/最近路径等），GOLDEN 由独立实现
 *      按同一语料预算得出，不是程序自输出回填。
 *
 * 任何一项不符即退出非零（conan create 随之失败）。
 * 断言使用自定义 CHECK 宏而非 <cassert>/assert()：CI profile 为 Release，
 * -DNDEBUG 会把 assert() 预处理剔除，测试会退化成恒返回 0 的空壳。
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "genht/hash.h"
#include "genht/htip.h"
#include "genht/htpp.h"
#include "genht/htsi.h"
#include "genht/htss.h"
#include "genht/siphash24.h"

/* ── 1) 构造输入：固定语料 ────────────────────────────────────────── */
static const char *const CORPUS[] = {
    "alice /index.html 1200",
    "bob /index.html 800",
    "alice /about.html 640",
    "carol /index.html 1500",
    "bob /img/logo.png 20480",
    "alice /about.html 700",
    "dave /index.html 300",
    "carol /img/logo.png 20480",
    "bob /index.html 900",
    "alice /index.html 500",
    "dave /doc/spec.pdf 4096",
    "carol /about.html 350",
    "alice /img/logo.png 20480",
};
#define NREQ    ((int)(sizeof(CORPUS) / sizeof(CORPUS[0])))
#define NSYNTH  2000
#define SYNTHP  "/gen/"

/* ── 3) 参考输出：由独立实现按同一语料预算得出 ────────────────────── */
static const char GOLDEN[] =
    "genht consumer e2e report\n"
    "users=4 requests=13 real_paths=3\n"
    "total_bytes=68330\n"
    "path /about.html hits=3 bytes=1690\n"
    "path /img/logo.png hits=3 bytes=61440\n"
    "path /index.html hits=6 bytes=5200\n"
    "user alice hits=5 last=/img/logo.png\n"
    "user bob hits=3 last=/index.html\n"
    "user carol hits=3 last=/about.html\n"
    "user dave hits=2 last=/doc/spec.pdf\n"
    "req_first id=0 user=alice path=/index.html bytes=1200\n"
    "req_last id=12 user=alice path=/img/logo.png bytes=20480\n"
    "decommission popped_bytes=4096 has_after=0 second_popentry_null=1\n"
    "load inserted=2000 length_after_insert=2003 length_after_half_pop=1003\n"
    "load spot_0000=0 spot_0001=1 spot_1998=0 spot_1999=1999\n"
    "after_user_pop hlast_has_bob=0 hlast_length=3\n"
    "fingerprint_stable=1\n";

static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                                           \
    do {                                                                      \
        checks++;                                                             \
        if (!(cond)) {                                                        \
            failures++;                                                       \
            fprintf(stderr, "CHECK FAILED: %s (test_consumer.c:%d)\n", #cond, \
                    __LINE__);                                                \
        }                                                                     \
    } while (0)

/* ── 对象与索引 ───────────────────────────────────────────────────── */
struct user {
    const char *name;      /* 语料副本里的 token，驻留后作为 htpp 的键 */
    unsigned hits;
    const char *last_path;
};

struct request {
    long id;
    const char *user;
    const char *path;
    int bytes;
};

static struct user users[8];
static int users_n = 0;

/* 两级索引：hname 做字符串→槽位驻留（内容匹配），huser 做指针键→对象索引。
 * 热路径每次都走这两张表，不是旁路装饰。 */
struct idx {
    htsi_t *hname;   /* user 名 → 槽位号+1（0 表示未驻留） */
    htpp_t *huser;   /* 驻留后的规范名指针 → struct user* */
};

static struct user *user_lookup(struct idx *ix, const char *name, int create)
{
    htsi_entry_t *e = htsi_getentry(ix->hname, name);

    if (e == NULL) {
        if (!create || users_n >= (int)(sizeof(users) / sizeof(users[0])))
            return NULL;
        users[users_n].name = name;      /* 首次出现的 token 即规范名（驻留） */
        users[users_n].hits = 0;
        users[users_n].last_path = NULL;
        htsi_set(ix->hname, (char *)name, users_n + 1);
        htpp_set(ix->huser, (void *)users[users_n].name, &users[users_n]);
        return &users[users_n++];
    }
    /* 已驻留：经指针键索引取对象 */
    return (struct user *)htpp_get(ix->huser, users[e->value - 1].name);
}

static void acc_metric(htsi_t *ht, const char *key, int delta)
{
    htsi_entry_t *e = htsi_getentry(ht, key);

    if (e != NULL)
        e->value += delta;              /* 命中已有条目：读改写 */
    else
        htsi_set(ht, (char *)key, delta);
}

static char *next_tok(char **cursor)
{
    char *s = *cursor;
    char *start;

    while (*s == ' ' || *s == '\t' || *s == '\n')
        s++;
    if (*s == '\0') {
        *cursor = s;
        return NULL;
    }
    start = s;
    while (*s != '\0' && *s != ' ' && *s != '\t' && *s != '\n')
        s++;
    if (*s != '\0')
        *s++ = '\0';
    *cursor = s;
    return start;
}

static int cmp_str(const void *a, const void *b)
{
    return strcmp(*(const char *const *)a, *(const char *const *)b);
}

int main(void)
{
    static char corpus[1024];
    static char synth[NSYNTH][24];
    static const char *keys[NSYNTH + 8];
    static const char *ukeys[8];
    char report[8192];
    size_t corpus_len, rlen = 0;
    char *w, *cursor, *utok, *ptok, *btok;
    int i, nkeys, nreal, nuser, total_bytes, spec_bytes;
    int len_after_insert = 0, len_after_half = 0, stable = 0;
    struct request reqs[NREQ];
    static const uint8_t sipkey[16] = { 0x01, 0x23, 0x45, 0x67, 0x89, 0xab,
                                        0xcd, 0xef, 0x10, 0x32, 0x54, 0x76,
                                        0x98, 0xba, 0xdc, 0xfe };
    htsi_t *hbytes, *hhits;
    htss_t *hlast;
    struct idx ix;
    htip_t *hreq;

    hbytes = htsi_alloc(strhash, strkeyeq);   /* path -> 累计字节 */
    hhits  = htsi_alloc(strhash, strkeyeq);   /* path -> 命中次数 */
    hlast  = htss_alloc(strhash, strkeyeq);   /* user -> 最近访问 */
    ix.hname = htsi_alloc(strhash, strkeyeq); /* user 名驻留表（内容键） */
    ix.huser = htpp_alloc(ptrhash, ptrkeyeq); /* 规范名指针 -> struct（指针键） */
    hreq   = htip_alloc(longhash, longkeyeq); /* 请求 id -> struct */

    CHECK(hbytes != NULL && hhits != NULL && hlast != NULL);
    CHECK(ix.hname != NULL && ix.huser != NULL && hreq != NULL);
    if (!(hbytes && hhits && hlast && ix.hname && ix.huser && hreq))
        return 1;

    /* 语料拼成可写副本：解析出的 token 即后续所有表的键，生命周期稳定 */
    w = corpus;
    for (i = 0; i < NREQ; i++) {
        size_t n = strlen(CORPUS[i]);

        memcpy(w, CORPUS[i], n);
        w += n;
        *w++ = '\n';
    }
    *w = '\0';
    corpus_len = (size_t)(w - corpus);

    /* ── 2a) 真实执行：整条流水线 ─────────────────────────────────── */
    cursor = corpus;
    for (i = 0; i < NREQ; i++) {
        struct user *u;
        int bytes;

        utok = next_tok(&cursor);
        ptok = next_tok(&cursor);
        btok = next_tok(&cursor);
        CHECK(utok != NULL && ptok != NULL && btok != NULL);
        if (utok == NULL || ptok == NULL || btok == NULL)
            return 1;
        bytes = atoi(btok);

        u = user_lookup(&ix, utok, 1);     /* 驻留 + 指针键索引查找 */
        CHECK(u != NULL);
        if (u == NULL)
            return 1;
        u->hits++;
        u->last_path = ptok;

        acc_metric(hbytes, ptok, bytes);   /* path 维度累计字节 */
        acc_metric(hhits, ptok, 1);        /* path 维度命中次数 */
        htss_set(hlast, (char *)utok, (char *)ptok);  /* 最新状态 */

        reqs[i].id = (long)i;
        reqs[i].user = utok;
        reqs[i].path = ptok;
        reqs[i].bytes = bytes;
        htip_set(hreq, (long)i, &reqs[i]); /* 注册表 */
    }

    /* ── 2b) 真实运维动作：下线资源 + 幂等删除 ───────────────────── */
    spec_bytes = htsi_pop(hbytes, "/doc/spec.pdf");
    CHECK(spec_bytes == 4096);
    CHECK(htsi_getentry(hbytes, "/doc/spec.pdf") == NULL);
    CHECK(htsi_popentry(hhits, "/doc/spec.pdf") != NULL);
    CHECK(htsi_popentry(hhits, "/doc/spec.pdf") == NULL);  /* 二次删除应为空 */

    /* ── 2c) 负载灌入（触发多轮扩容）后按下标删一半 ─────────────── */
    for (i = 0; i < NSYNTH; i++) {
        snprintf(synth[i], sizeof(synth[i]), SYNTHP "%04d", i);
        acc_metric(hbytes, synth[i], i);
        acc_metric(hhits, synth[i], 1);
    }
    len_after_insert = (int)htsi_length(hbytes);
    CHECK(len_after_insert == 3 + NSYNTH);
    for (i = 0; i < NSYNTH; i += 2)
        htsi_pop(hbytes, synth[i]);
    len_after_half = (int)htsi_length(hbytes);
    CHECK(len_after_half == 3 + NSYNTH / 2);

    /* ── 2d) 状态变更（用户索引）────────────────────────────────── */
    CHECK(htss_popentry(hlast, "bob") != NULL);

    /* ── 2e) 二进制指纹（确定性校验码）──────────────────────────── */
    {
        uint64_t fp1 = siphash((const uint8_t *)corpus, corpus_len, sipkey);
        uint64_t fp2 = siphash((const uint8_t *)corpus, corpus_len, sipkey);

        stable = (fp1 == fp2 && fp1 != 0);
        CHECK(stable);
    }

    /* ── 3) 产出结果：确定性报告（显式排序，不依赖哈希序）────────── */
    nkeys = 0;
    {
        htsi_entry_t *e;

        for (e = htsi_first(hbytes); e != NULL; e = htsi_next(hbytes, e))
            if (nkeys < (int)(sizeof(keys) / sizeof(keys[0])))
                keys[nkeys++] = e->key;
    }
    qsort(keys, (size_t)nkeys, sizeof(keys[0]), cmp_str);

    nreal = 0;
    total_bytes = 0;
    for (i = 0; i < nkeys; i++) {
        if (strncmp(keys[i], SYNTHP, sizeof(SYNTHP) - 1) != 0) {
            nreal++;
            total_bytes += htsi_get(hbytes, keys[i]);
        }
    }

    nuser = 0;
    for (i = 0; i < users_n; i++)
        ukeys[nuser++] = users[i].name;
    qsort(ukeys, (size_t)nuser, sizeof(ukeys[0]), cmp_str);

    rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                             "genht consumer e2e report\n");
    rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                             "users=%d requests=%d real_paths=%d\n",
                             users_n, NREQ, nreal);
    rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                             "total_bytes=%d\n", total_bytes);
    for (i = 0; i < nkeys; i++) {
        if (strncmp(keys[i], SYNTHP, sizeof(SYNTHP) - 1) == 0)
            continue;                    /* 合成负载不入报告 */
        rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                                 "path %s hits=%d bytes=%d\n", keys[i],
                                 htsi_get(hhits, keys[i]),
                                 htsi_get(hbytes, keys[i]));
    }
    for (i = 0; i < nuser; i++) {
        struct user *u = (struct user *)htpp_get(ix.huser, ukeys[i]);

        rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                                 "user %s hits=%u last=%s\n", ukeys[i],
                                 u != NULL ? u->hits : 0u,
                                 (u != NULL && u->last_path != NULL)
                                     ? u->last_path : "-");
    }
    {
        struct request *r0 = (struct request *)htip_get(hreq, 0L);
        struct request *rl = (struct request *)htip_get(hreq, (long)(NREQ - 1));

        CHECK(r0 != NULL && rl != NULL);
        rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                                 "req_first id=%ld user=%s path=%s bytes=%d\n",
                                 r0 != NULL ? r0->id : -1L,
                                 r0 != NULL ? r0->user : "-",
                                 r0 != NULL ? r0->path : "-",
                                 r0 != NULL ? r0->bytes : 0);
        rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                                 "req_last id=%ld user=%s path=%s bytes=%d\n",
                                 rl != NULL ? rl->id : -1L,
                                 rl != NULL ? rl->user : "-",
                                 rl != NULL ? rl->path : "-",
                                 rl != NULL ? rl->bytes : 0);
    }
    rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                             "decommission popped_bytes=%d has_after=%d "
                             "second_popentry_null=%d\n",
                             spec_bytes,
                             htsi_has(hbytes, "/doc/spec.pdf") ? 1 : 0,
                             htsi_popentry(hhits, "/doc/spec.pdf") == NULL);
    rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                             "load inserted=%d length_after_insert=%d "
                             "length_after_half_pop=%d\n",
                             NSYNTH, len_after_insert, len_after_half);
    rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                             "load spot_0000=%d spot_0001=%d spot_1998=%d "
                             "spot_1999=%d\n",
                             htsi_get(hbytes, SYNTHP "0000"),
                             htsi_get(hbytes, SYNTHP "0001"),
                             htsi_get(hbytes, SYNTHP "1998"),
                             htsi_get(hbytes, SYNTHP "1999"));
    rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                             "after_user_pop hlast_has_bob=%d hlast_length=%u\n",
                             htss_has(hlast, "bob") ? 1 : 0,
                             htss_length(hlast));
    rlen += (size_t)snprintf(report + rlen, sizeof(report) - rlen,
                             "fingerprint_stable=%d\n", stable);

    /* ── 4) 校验内容：与参考输出逐字节比对 ───────────────────────── */
    CHECK(strcmp(report, GOLDEN) == 0);
    if (strcmp(report, GOLDEN) != 0) {
        size_t k;

        for (k = 0; report[k] != '\0' && GOLDEN[k] != '\0'; k++)
            if (report[k] != GOLDEN[k])
                break;
        fprintf(stderr,
                "E2E MISMATCH at byte %zu:\n  actual: %.70s\n  golden: %.70s\n",
                k, report + k, GOLDEN + k);
    }

    /* 语义不变量（独立预算值）*/
    CHECK(users_n == 4);
    CHECK(nreal == 3);
    CHECK(total_bytes == 68330);
    CHECK((int)htsi_length(hbytes) == 3 + NSYNTH / 2);
    CHECK(htsi_get(hbytes, "/index.html") == 5200);
    CHECK(htsi_get(hbytes, "/img/logo.png") == 61440);
    CHECK(htsi_get(hbytes, "/about.html") == 1690);
    CHECK(htsi_get(hhits, "/index.html") == 6);
    CHECK(htsi_get(hbytes, SYNTHP "0001") == 1);

    htsi_free(hbytes);
    htsi_free(hhits);
    htsi_free(ix.hname);
    htss_free(hlast);
    htpp_free(ix.huser);
    htip_free(hreq);

    printf("genht e2e consumer: %d checks, %d failures\n", checks, failures);
    if (failures > 0) {
        fprintf(stderr, "FAILED: %d/%d checks failed\n", failures, checks);
        return 1;
    }
    printf("PASS: end-to-end pipeline output matches reference\n");
    return 0;
}
