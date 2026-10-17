/* libzzip 0.13.80 test_package — 真实建 ZIP fixture + 读回 API 验证
 *
 * fixture 程序化生成：用安装出的 libzzip 自身 API 无法"创建"zip（它是只读库），
 * 因此 fixture 由本测试用最小手工 ZIP 构造（无外部 zip 工具、无来源不明二进制）：
 * 一个 store (uncompressed) 的 zip 局部文件头 + 中央目录 + EOCD，全部可审计。
 *
 * 覆盖:
 *   1. zzip_dir_open 打开 zip
 *   2. zzip_dir_find 查找 entry（存在 / 不存在）
 *   3. zzip_file_open + zzip_read 读取 entry 内容
 *   4. 精确比较内容（逐字节）
 *   5. 多 entry（3 个文件）
 *   6. 不存在 entry → NULL
 *   7. 负向: 非法 zip 数据 / 空输入
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <zzip/lib.h>

/* ---------- 程序化生成最小合法 ZIP (store, 无压缩) ---------- */

typedef struct {
    const char *name;     /* entry 名 */
    const char *content;  /* 内容 (可含 NUL, 用 content_len 定长) */
    size_t content_len;
} entry_desc;

static unsigned long crc32_of(const unsigned char *buf, size_t len);

/* CRC32 (IEEE, zlib 兼容) — zip 中央目录要求 */
static unsigned long crc32_of(const unsigned char *buf, size_t len)
{
    static unsigned long table[256];
    static int inited = 0;
    unsigned long c;
    size_t i;
    int k;
    if (!inited) {
        for (i = 0; i < 256; i++) {
            c = i;
            for (k = 0; k < 8; k++)
                c = (c & 1) ? (0xEDB88320UL ^ (c >> 1)) : (c >> 1);
            table[i] = c;
        }
        inited = 1;
    }
    c = 0xFFFFFFFFUL;
    for (i = 0; i < len; i++)
        c = table[(c ^ buf[i]) & 0xFF] ^ (c >> 8);
    return c ^ 0xFFFFFFFFUL;
}

static void put16(unsigned char *p, unsigned v) { p[0] = v & 0xFF; p[1] = (v >> 8) & 0xFF; }
static void put32(unsigned char *p, unsigned long v)
{
    p[0] = v & 0xFF; p[1] = (v >> 8) & 0xFF; p[2] = (v >> 16) & 0xFF; p[3] = (v >> 24) & 0xFF;
}

/* 生成 zip 到 malloc 的缓冲区, 返回长度; 每个文件一个 local header + 数据, 后跟
 * 中央目录 + EOCD。手工构造, 完全可审计。 */
static size_t build_zip(unsigned char **out, const entry_desc *entries, size_t n)
{
    size_t cap = 4096, len = 0;
    unsigned char *buf = (unsigned char *)malloc(cap);
    size_t *lhf_offs = (size_t *)calloc(n, sizeof(size_t));
    size_t i;
    size_t cd_start, cd_len;

    if (!buf || !lhf_offs) {          /* 分配失败: 安全返回 0, 不使用 NULL 指针 */
        free(buf);
        free(lhf_offs);
        return 0;
    }

    for (i = 0; i < n; i++) {
        size_t nl = strlen(entries[i].name);
        size_t cl = entries[i].content_len;
        unsigned long crc = crc32_of((const unsigned char *)entries[i].content, cl);
        while (len + 30 + nl + cl + 64 > cap) {
            unsigned char *nb;
            cap *= 2;
            nb = (unsigned char *)realloc(buf, cap);
            if (!nb) { free(buf); free(lhf_offs); return 0; }
            buf = nb;
        }
        lhf_offs[i] = len;
        /* local file header */
        put32(buf + len, 0x04034b50); len += 4;
        put16(buf + len, 20);        len += 2;   /* version needed */
        put16(buf + len, 0);         len += 2;   /* flags */
        put16(buf + len, 0);         len += 2;   /* method: store */
        put16(buf + len, 0);         len += 2;   /* mod time */
        put16(buf + len, 0x21);      len += 2;   /* mod date (1980-01-01) */
        put32(buf + len, crc);       len += 4;
        put32(buf + len, cl);        len += 4;   /* csize */
        put32(buf + len, cl);        len += 4;   /* usize */
        put16(buf + len, nl);        len += 2;
        put16(buf + len, 0);         len += 2;   /* extra len */
        memcpy(buf + len, entries[i].name, nl); len += nl;
        memcpy(buf + len, entries[i].content, cl); len += cl;
    }

    cd_start = len;
    for (i = 0; i < n; i++) {
        size_t nl = strlen(entries[i].name);
        size_t cl = entries[i].content_len;
        unsigned long crc = crc32_of((const unsigned char *)entries[i].content, cl);
        while (len + 46 + nl + 64 > cap) {
            unsigned char *nb;
            cap *= 2;
            nb = (unsigned char *)realloc(buf, cap);
            if (!nb) { free(buf); free(lhf_offs); return 0; }
            buf = nb;
        }
        /* central directory header */
        put32(buf + len, 0x02014b50); len += 4;
        put16(buf + len, 20);        len += 2;   /* version made by */
        put16(buf + len, 20);        len += 2;   /* version needed */
        put16(buf + len, 0);         len += 2;   /* flags */
        put16(buf + len, 0);         len += 2;   /* method: store */
        put16(buf + len, 0);         len += 2;   /* time */
        put16(buf + len, 0x21);      len += 2;   /* date */
        put32(buf + len, crc);       len += 4;
        put32(buf + len, cl);        len += 4;
        put32(buf + len, cl);        len += 4;
        put16(buf + len, nl);        len += 2;
        put16(buf + len, 0);         len += 2;   /* extra */
        put16(buf + len, 0);         len += 2;   /* comment */
        put16(buf + len, 0);         len += 2;   /* disk */
        put16(buf + len, 0);         len += 2;   /* int attrs */
        put32(buf + len, 0);         len += 4;   /* ext attrs */
        put32(buf + len, (unsigned long)lhf_offs[i]); len += 4;
        memcpy(buf + len, entries[i].name, nl); len += nl;
    }
    cd_len = len - cd_start;

    while (len + 22 > cap) {
        unsigned char *nb;
        cap *= 2;
        nb = (unsigned char *)realloc(buf, cap);
        if (!nb) { free(buf); free(lhf_offs); return 0; }
        buf = nb;
    }
    /* EOCD */
    put32(buf + len, 0x06054b50); len += 4;
    put16(buf + len, 0);         len += 2;
    put16(buf + len, 0);         len += 2;
    put16(buf + len, n);         len += 2;
    put16(buf + len, n);         len += 2;
    put32(buf + len, cd_len);    len += 4;
    put32(buf + len, cd_start);  len += 4;
    put16(buf + len, 0);         len += 2;

    free(lhf_offs);
    *out = buf;
    return len;
}

/* ---------- 断言辅助 ---------- */
static int failures = 0;
static int checks = 0;
#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        checks++;                                                            \
        if (cond) {                                                          \
            printf("[PASS] %s\n", msg);                                      \
        } else {                                                             \
            printf("[FAIL] %s (line %d)\n", msg, __LINE__);                  \
            failures++;                                                      \
        }                                                                    \
    } while (0)

/* ---------- 场景 ---------- */

static void scenario_open_read_verify(const char *zippath)
{
    ZZIP_DIR *dir = zzip_dir_open(zippath, 0);
    CHECK(dir != NULL, "zzip_dir_open 打开 zip");
    if (!dir)
        return;                        /* 打开失败: 后续 API 均以 dir 为参, 直接返回避免 NULL 解引用 */

    /* 遍历目录, 统计 entry */
    ZZIP_DIRENT dent;
    int count = 0;
    while (zzip_dir_read(dir, &dent))
        count++;
    CHECK(count == 3, "zzip_dir_read 遍历得到 3 个 entry");

    /* 不存在的 entry */
    ZZIP_FILE *nf = zzip_file_open(dir, "no/such/file.txt", 0);
    CHECK(nf == NULL, "zzip_file_open 不存在 entry 返回 NULL");
    if (nf) zzip_file_close(nf);

    /* 逐 entry 打开-读取-精确比较 */
    {
        static const char *names[3] = { "hello.txt", "data/second.bin", "third.md" };
        static const char *expect[3] = { "Hello, libzzip!\n",
                                         "BINARY\x00\x01\x02\x03CONTENT",
                                         "# third entry\nmulti-line\n" };
        static const size_t expect_len[3] = { 16, 17, 25 };  /* 二进制内容含 NUL, 显式长度 */
        int i;
        for (i = 0; i < 3; i++) {
            ZZIP_FILE *fp = zzip_file_open(dir, names[i], 0);
            char buf[256];
            zzip_ssize_t n;
            char msg[128];
            snprintf(msg, sizeof msg, "zzip_file_open(%s)", names[i]);
            CHECK(fp != NULL, msg);
            if (!fp) continue;
            n = zzip_read(fp, buf, sizeof(buf) - 1);
            snprintf(msg, sizeof msg, "zzip_read(%s) 读到内容", names[i]);
            CHECK(n > 0, msg);
            if (n <= 0) { zzip_file_close(fp); continue; }
            snprintf(msg, sizeof msg, "zzip_read(%s) 字节数精确 %d", names[i], (int)expect_len[i]);
            CHECK((size_t)n == expect_len[i], msg);
            snprintf(msg, sizeof msg, "zzip_read(%s) 内容逐字节一致", names[i]);
            CHECK(n > 0 && memcmp(buf, expect[i], (size_t)n) == 0, msg);
            zzip_file_close(fp);
        }
    }

    /* zzip_dir_stat 查找 entry */
    {
        ZZIP_STAT st;
        int found = zzip_dir_stat(dir, "hello.txt", &st, 0);
        char msg[128];
        snprintf(msg, sizeof msg, "zzip_dir_stat 找到 hello.txt (rc=%d)", found);
        CHECK(found >= 0, msg);
        if (found >= 0)
            CHECK(st.st_size == (int)strlen("Hello, libzzip!\n"),
                  "zzip_dir_stat st_size 精确");
    }

    zzip_dir_close(dir);
}

static void scenario_negative_invalid(const char *badpath)
{
    ZZIP_DIR *dir = zzip_dir_open(badpath, 0);
    CHECK(dir == NULL, "非法 zip 数据 zzip_dir_open 返回 NULL");
    if (dir) zzip_dir_close(dir);
}

static void scenario_negative_empty(const char *emptypath)
{
    ZZIP_DIR *dir = zzip_dir_open(emptypath, 0);
    CHECK(dir == NULL, "空输入 zzip_dir_open 返回 NULL");
    if (dir) zzip_dir_close(dir);
}

static void scenario_negative_missing_file(void)
{
    ZZIP_DIR *dir = zzip_dir_open("/no/such/archive.zip", 0);
    CHECK(dir == NULL, "不存在的文件 zzip_dir_open 返回 NULL");
    if (dir) zzip_dir_close(dir);
}

int main(int argc, char **argv)
{
    static const entry_desc entries[3] = {
        { "hello.txt",        "Hello, libzzip!\n",              16 },
        { "data/second.bin",  "BINARY\x00\x01\x02\x03CONTENT",   17 },
        { "third.md",         "# third entry\nmulti-line\n",    25 },
    };
    unsigned char *zipbuf;
    size_t ziplen;
    FILE *f;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <tmpdir>\n", argv[0]);
        return 2;
    }

    /* fixture: 程序化生成 */
    ziplen = build_zip(&zipbuf, entries, 3);
    if (ziplen == 0) {                 /* 内部 malloc/realloc 失败: 安全失败, 不使用 NULL 缓冲 */
        fprintf(stderr, "build_zip: out of memory\n");
        return 2;
    }

    /* 写到 <tmpdir>/test.zip */
    {
        char path[512];
        snprintf(path, sizeof path, "%s/test.zip", argv[1]);
        f = fopen(path, "wb");
        if (!f) { perror("fopen test.zip"); return 2; }
        if (fwrite(zipbuf, 1, ziplen, f) != ziplen) {
            fprintf(stderr, "fwrite test.zip: short write\n");
            fclose(f);
            return 2;
        }
        fclose(f);
    }

    /* 参考归档: 独立构造第二个归档 (单 entry r1.txt, 与主 fixture 不同 entry 集),
     * 交叉验证读取路径。纯 C 文件 API 写入, 不经 shell、无命令拼接, 无注入面 */
    {
        static const entry_desc ref_entries[1] = {
            { "r1.txt", "Hello, libzzip!\n", 16 },
        };
        unsigned char *refbuf;
        size_t reflen = build_zip(&refbuf, ref_entries, 1);
        char path[512];
        if (reflen == 0) {
            fprintf(stderr, "build_zip(ref): out of memory\n");
            return 2;
        }
        snprintf(path, sizeof path, "%s/ref.zip", argv[1]);
        f = fopen(path, "wb");
        if (!f) { perror("fopen ref.zip"); free(refbuf); return 2; }
        if (fwrite(refbuf, 1, reflen, f) != reflen) {
            fprintf(stderr, "fwrite ref.zip: short write\n");
            fclose(f);
            free(refbuf);
            return 2;
        }
        fclose(f);
        free(refbuf);
        {
            ZZIP_DIR *dir = zzip_dir_open(path, 0);
            CHECK(dir != NULL, "读取独立构造的参考归档");
            if (dir) {
                ZZIP_FILE *fp = zzip_file_open(dir, "r1.txt", 0);
                CHECK(fp != NULL, "参考归档 r1.txt 打开");
                if (fp) {
                    char buf[64];
                    zzip_ssize_t n = zzip_read(fp, buf, sizeof buf - 1);
                    if (n > 0) buf[n] = 0;
                    CHECK(n == (zzip_ssize_t)strlen("Hello, libzzip!\n")
                              && memcmp(buf, "Hello, libzzip!\n", (size_t)n) == 0,
                          "参考归档内容精确一致");
                    zzip_file_close(fp);
                }
                zzip_dir_close(dir);
            }
        }
    }

    /* 主场景 */
    {
        char path[512];
        snprintf(path, sizeof path, "%s/test.zip", argv[1]);
        scenario_open_read_verify(path);
    }

    /* 负向场景: 非法 zip */
    {
        char path[512];
        snprintf(path, sizeof path, "%s/bad.zip", argv[1]);
        f = fopen(path, "wb");
        if (!f) { perror("fopen bad.zip"); return 2; }
        if (fwrite("THIS IS NOT A ZIP FILE AT ALL. JUST GARBAGE DATA 1234567890", 1, 59, f) != 59) {
            fprintf(stderr, "fwrite bad.zip: short write\n");
            fclose(f);
            return 2;
        }
        fclose(f);
        scenario_negative_invalid(path);
    }

    /* 负向场景: 空文件 */
    {
        char path[512];
        snprintf(path, sizeof path, "%s/empty.zip", argv[1]);
        f = fopen(path, "wb");
        if (!f) { perror("fopen empty.zip"); return 2; }
        fclose(f);
        scenario_negative_empty(path);
    }

    /* 负向场景: 路径不存在 */
    scenario_negative_missing_file();

    free(zipbuf);

    printf("\n==== test_package summary ====\n");
    printf("total checks=%d, failures=%d\n", checks, failures);
    if (failures) {
        printf("RESULT: FAIL\n");
        return 1;
    }
    printf("RESULT: PASS\n");
    return 0;
}
