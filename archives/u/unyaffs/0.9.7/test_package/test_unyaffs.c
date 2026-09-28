/*
 * test_unyaffs.c — unyaffs 0.9.7 消费者侧测试（HarmonyOS PC / OHOS aarch64）
 *
 * 判据设计（与本仓库 test_package 规范一致）：
 *   - popen 内存管道直读，**不使用 /tmp**（OHOS 上只读）；需要可写文件时只用
 *     argv[2] 传入的 scratch 目录，并先显式探测可写性
 *   - 跑不起来的完整分类：pclose==-1 / !WIFEXITED / 退出码 ∈ {126,127} 或 >=128
 *     一律判 FAIL（popen 经 /bin/sh 中转，信号死亡被转写成 128+signum）
 *   - 循环读到 EOF 再 pclose；expect() 计数而非 assert()
 *
 * ★ 夹具策略：**在测试进程内程序化合成 YAFFS2 镜像**，不依赖任何外部样本。
 *   镜像按 unyaffs.h 的对象头布局（aarch64 下编译期算出的字段偏移）与
 *   yaffs_PackedTags2 标签（seq/objectId/chunkId/byteCount）逐 chunk 拼装：
 *     chunk = chunk_size(2048) 数据 + spare_size(64) 标签区
 *   上游不校验 ECC，因此无需计算纠错码即可产出可被正确解析的镜像。
 *
 * ★ 判据主体是**往返属性**而非 golden 向量：
 *   对多组文件集合（含空文件、1 字节、正好一个 chunk、跨 chunk、多 chunk）
 *   执行「合成镜像 → unyaffs 提取 → 逐字节比对」，由被测程序自己证明自己的
 *   镜像解析与文件重建自洽；无需维护任何期望输出表。
 *
 * 用法: test_unyaffs <unyaffs 可执行文件路径> <可写 scratch 目录>
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static const char *g_bin = NULL;
static const char *g_scratch = NULL;
static int g_pass = 0, g_fail = 0;

#define CHUNK_SIZE 2048
#define SPARE_SIZE 64
#define CHUNK_TOTAL (CHUNK_SIZE + SPARE_SIZE)
#define OH_TOTAL 512

/* 与 unyaffs.h 一致的对象头字段偏移（aarch64 编译器对齐下实测标定） */
#define OH_TYPE 0
#define OH_PARENT 4
#define OH_NAME 10
#define OH_MODE 268
#define OH_FILESIZE 292
#define OH_ALIAS 300

#define T_FILE 1
#define T_SYMLINK 2
#define T_DIR 3

static void expect(int cond, const char *what, const char *detail)
{
    if (cond) {
        g_pass++;
        printf("  [PASS] %s\n", what);
    } else {
        g_fail++;
        printf("  [FAIL] %s%s%s\n", what,
               detail && *detail ? " — " : "", detail && *detail ? detail : "");
    }
    fflush(stdout);
}

static void expect_contains(const char *label, const char *out, const char *needle)
{
    char what[320], d[400];
    snprintf(what, sizeof(what), "%s: 输出含 \"%s\"", label, needle);
    if (strstr(out, needle) != NULL) {
        expect(1, what, "");
    } else {
        snprintf(d, sizeof(d), "实际输出: %.240s", out);
        expect(0, what, d);
    }
}

static int run_capture(const char *args, char *buf, size_t cap)
{
    char cmd[4096];
    FILE *fp;
    size_t n = 0, got;
    int rc, killed, code;

    snprintf(cmd, sizeof(cmd), "\"%s\" %s < /dev/null 2>&1", g_bin, args);
    buf[0] = '\0';
    fp = popen(cmd, "r");
    if (!fp)
        return -1;
    while (n < cap - 1 && (got = fread(buf + n, 1, cap - 1 - n, fp)) > 0)
        n += got;
    buf[n] = '\0';
    rc = pclose(fp);
    if (rc == -1)
        return -1;
    killed = !WIFEXITED(rc);
    code = killed ? -1 : WEXITSTATUS(rc);
    if (killed || code == 126 || code == 127 || code >= 128)
        return -1;
    return code;
}

/* ── 小端写入 ── */
static void put32(unsigned char *p, unsigned v)
{
    p[0] = (unsigned char)(v & 0xff);
    p[1] = (unsigned char)((v >> 8) & 0xff);
    p[2] = (unsigned char)((v >> 16) & 0xff);
    p[3] = (unsigned char)((v >> 24) & 0xff);
}

/* 生成一个 chunk：数据区 + 标签区（4×u32 小端 + 0xff 填充） */
static void make_chunk(unsigned char *out, const unsigned char *data, size_t dlen,
                       unsigned seq, unsigned objid, unsigned chunkid, unsigned nbytes)
{
    memset(out, 0xff, CHUNK_TOTAL);
    if (dlen > CHUNK_SIZE)
        dlen = CHUNK_SIZE;
    if (data && dlen)
        memcpy(out, data, dlen);
    put32(out + CHUNK_SIZE + 0, seq);
    put32(out + CHUNK_SIZE + 4, objid);
    put32(out + CHUNK_SIZE + 8, chunkid);
    put32(out + CHUNK_SIZE + 12, nbytes);
}

static void make_objheader(unsigned char *out, int type, int parent,
                           const char *name, unsigned mode, int fsize,
                           const char *alias)
{
    size_t nl;
    memset(out, 0, OH_TOTAL);
    put32(out + OH_TYPE, (unsigned)type);
    put32(out + OH_PARENT, (unsigned)parent);
    nl = strlen(name);
    if (nl > 255)
        nl = 255;
    memcpy(out + OH_NAME, name, nl);
    put32(out + OH_MODE, mode);
    put32(out + OH_FILESIZE, (unsigned)fsize);
    if (alias && *alias) {
        size_t al = strlen(alias);
        if (al > 159)
            al = 159;
        memcpy(out + OH_ALIAS, alias, al);
    }
}

/* 合成镜像：根目录 + 若干文件（全部平铺在根下） */
static int build_image(const char *path,
                       const char *const *names,
                       const unsigned char *const *datas,
                       const size_t *lens, int nfiles)
{
    unsigned char chunkbuf[CHUNK_TOTAL], oh[OH_TOTAL];
    FILE *fp = fopen(path, "wb");
    unsigned seq = 1;
    unsigned oid = 2;
    int i;

    if (!fp)
        return -1;

    make_objheader(oh, T_DIR, 1, "/", 0755, 0, NULL);
    make_chunk(chunkbuf, oh, OH_TOTAL, seq++, 1, 0, 0);
    if (fwrite(chunkbuf, 1, CHUNK_TOTAL, fp) != CHUNK_TOTAL) {
        fclose(fp);
        return -1;
    }

    for (i = 0; i < nfiles; i++) {
        size_t len = lens[i], off = 0;
        unsigned cid = 1;
        make_objheader(oh, T_FILE, 1, names[i], 0644, (int)len, NULL);
        make_chunk(chunkbuf, oh, OH_TOTAL, seq++, oid, 0, 0);
        if (fwrite(chunkbuf, 1, CHUNK_TOTAL, fp) != CHUNK_TOTAL) {
            fclose(fp);
            return -1;
        }
        /* 空文件也应有一个 chunkId=1 的空数据 chunk（YAFFS2 约定） */
        do {
            size_t take = len - off;
            if (take > CHUNK_SIZE)
                take = CHUNK_SIZE;
            make_chunk(chunkbuf, datas[i] ? datas[i] + off : NULL, take,
                       seq++, oid, cid++, (unsigned)take);
            if (fwrite(chunkbuf, 1, CHUNK_TOTAL, fp) != CHUNK_TOTAL) {
                fclose(fp);
                return -1;
            }
            off += take;
        } while (off < len);
        oid++;
    }
    fclose(fp);
    return 0;
}

static int read_file(const char *path, unsigned char *buf, size_t cap, size_t *outlen)
{
    FILE *fp = fopen(path, "rb");
    size_t n;
    if (!fp)
        return -1;
    n = fread(buf, 1, cap, fp);
    fclose(fp);
    *outlen = n;
    return 0;
}

/* 构造一条 "scratch/xxx" 路径 */
static void spath(char *out, size_t cap, const char *name)
{
    snprintf(out, cap, "%s/%s", g_scratch, name);
}

int main(int argc, char **argv)
{
    static char buf[65536];
    char img[512], outdir[512], p1[512], p2[512], args[2048], label[320], d[320];
    int rc, i;

    if (argc < 3) {
        fprintf(stderr, "usage: %s <unyaffs-binary> <scratch-dir>\n", argv[0]);
        return 2;
    }
    g_bin = argv[1];
    g_scratch = argv[2];
    printf("=== unyaffs 0.9.7 消费者测试 ===\n");
    printf("被测二进制: %s\n", g_bin);
    printf("scratch   : %s\n", g_scratch);

    /* ── 0. scratch 可写性显式探测（不假定任何固定路径）── */
    spath(p1, sizeof(p1), "probe.tmp");
    {
        FILE *f = fopen(p1, "wb");
        if (f) {
            fputs("probe", f);
            fclose(f);
            remove(p1);
            expect(1, "scratch 目录可写（探针文件写入成功）", "");
        } else {
            expect(0, "scratch 目录可写（探针文件写入成功）", p1);
            goto summary;
        }
    }

    /* ── 1. 版本与用法契约 ── */
    printf("── unyaffs -V\n");
    rc = run_capture("-V", buf, sizeof(buf));
    expect(rc == 0, "-V 退出码 (期望 0)", "");
    expect_contains("-V", buf, "V0.9.7");

    printf("── unyaffs（无参数）\n");
    rc = run_capture("", buf, sizeof(buf));
    expect(rc == 1, "无参数退出码 (期望 1)", "");
    expect_contains("无参数", buf, "Usage: unyaffs [options] <image_file_name>");
    expect_contains("无参数", buf, "extract files from a YAFFS2 file system image");

    printf("── unyaffs -h\n");
    rc = run_capture("-h", buf, sizeof(buf));
    expect(rc == 1, "-h 退出码 (期望 1)", "");
    expect_contains("-h", buf, "Usage: unyaffs");

    printf("── unyaffs a b c（位置参数过多）\n");
    rc = run_capture("a b c", buf, sizeof(buf));
    expect(rc == 1, "位置参数 >2 时退出码 (期望 1)", "");
    expect_contains("参数过多", buf, "Usage: unyaffs");

    /* ── 2. 选项边界：-c 上限 16(KByte)，-s 上限 512(Byte) ── */
    printf("── unyaffs -c 17 x（超上限）\n");
    rc = run_capture("-c 17 x", buf, sizeof(buf));
    expect(rc == 1, "-c 17 退出码 (期望 1)", "");
    expect_contains("-c 17", buf, "Usage: unyaffs");

    printf("── unyaffs -s 513 x（超上限）\n");
    rc = run_capture("-s 513 x", buf, sizeof(buf));
    expect(rc == 1, "-s 513 退出码 (期望 1)", "");
    expect_contains("-s 513", buf, "Usage: unyaffs");

    printf("── unyaffs -c abc x（非数字）\n");
    rc = run_capture("-c abc x", buf, sizeof(buf));
    expect(rc == 1, "-c abc 退出码 (期望 1)", "");
    expect_contains("-c abc", buf, "Usage: unyaffs");

    printf("── unyaffs -c 16 -s 512 -V（上限内合法，-V 优先生效）\n");
    rc = run_capture("-c 16 -s 512 -V", buf, sizeof(buf));
    expect(rc == 0, "-c 16 -s 512 -V 退出码 (期望 0)", "");
    expect_contains("-c16 -s512", buf, "V0.9.7");

    /* ── 3. 打不开的镜像 ── */
    spath(p1, sizeof(p1), "does-not-exist.img");
    snprintf(args, sizeof(args), "-c 2 -s 64 -t \"%s\"", p1);
    printf("── unyaffs -c 2 -s 64 -t <不存在>\n");
    rc = run_capture(args, buf, sizeof(buf));
    expect(rc == 1, "不存在镜像退出码 (期望 1)", "");
    expect_contains("不存在镜像", buf, "Open image file failed");

    /* ── 4. 合成镜像：列表 + 提取（核心）── */
    {
        static const char *const names[] = { "hello.txt", "big.bin" };
        static unsigned char big[5120];
        static unsigned char small[14];
        const unsigned char *datas[2];
        size_t lens[2];
        unsigned char rep[8192];
        size_t rl;
        int j;

        for (j = 0; j < 5120; j++)
            big[j] = (unsigned char)((j * 7 + 3) & 0xff);
        memcpy(small, "Hello, YAFFS!\n", 14);
        datas[0] = small;
        datas[1] = big;
        lens[0] = 14;
        lens[1] = 5120;

        spath(img, sizeof(img), "image1.yaffs2");
        if (build_image(img, names, datas, lens, 2) != 0) {
            expect(0, "合成镜像 image1 成功", img);
            goto after_image1;
        }
        expect(1, "合成镜像 image1 成功（2048+64 布局，2 个文件）", "");

        /* 4a. -t 列表 */
        snprintf(args, sizeof(args), "-c 2 -s 64 -t \"%s\"", img);
        printf("── unyaffs -c 2 -s 64 -t <image1>\n");
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 0, "列表退出码 (期望 0)", "");
        expect_contains("列表", buf, ".");
        expect_contains("列表", buf, "hello.txt");
        expect_contains("列表", buf, "big.bin");

        /* 4b. -v -t 列出元数据 */
        snprintf(args, sizeof(args), "-c 2 -s 64 -v -t \"%s\"", img);
        printf("── unyaffs -c 2 -s 64 -v -t <image1>\n");
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 0, "详细列表退出码 (期望 0)", "");
        expect_contains("详细列表", buf, "hello.txt");
        expect_contains("详细列表", buf, "14");
        expect_contains("详细列表", buf, "5120");

        /* 4c. 提取并逐字节比对 */
        spath(outdir, sizeof(outdir), "out1");
        remove(outdir);
        snprintf(args, sizeof(args), "-c 2 -s 64 \"%s\" \"%s\"", img, outdir);
        printf("── unyaffs -c 2 -s 64 <image1> <out1>\n");
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 0, "提取退出码 (期望 0)", "");

        spath(p1, sizeof(p1), "out1/hello.txt");
        if (read_file(p1, rep, sizeof(rep), &rl) != 0) {
            expect(0, "提取出 hello.txt", p1);
        } else {
            expect(rl == 14 && memcmp(rep, small, 14) == 0,
                   "hello.txt 内容逐字节一致 (14B)", "");
        }
        spath(p2, sizeof(p2), "out1/big.bin");
        if (read_file(p2, rep, sizeof(rep), &rl) != 0) {
            expect(0, "提取出 big.bin", p2);
        } else {
            expect(rl == 5120 && memcmp(rep, big, 5120) == 0,
                   "big.bin 内容逐字节一致 (5120B，跨 3 个 chunk)", "");
        }

        /* 4d. -d 布局检测（该合成镜像不带真实 NAND 布局特征） */
        snprintf(args, sizeof(args), "-d \"%s\"", img);
        printf("── unyaffs -d <image1>\n");
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 1, "-d 退出码 (期望 1：合成镜像无 NAND 布局特征)", "");
        expect_contains("-d", buf, "Detected flash layout(s):");
        expect_contains("-d", buf, "-- none --");
    }
after_image1:

    /* ── 5. 往返属性：多种尺寸/文件数，合成 → 提取 → 逐字节比对 ── */
    {
        /* 尺寸覆盖：0（空文件）、1、2047（不足一个 chunk）、2048（正好一个）、
         * 2049（跨 2 个）、4096（正好 2 个）、10000（跨 5 个） */
        static const size_t SIZES[] = { 0, 1, 2047, 2048, 2049, 4096, 10000 };
        static const int NSIZE = 7;
        static unsigned char src[10000], got[16384];
        static const char *const one[] = { "f0.bin" };
        const unsigned char *d1[1];
        size_t l1[1];
        int k;

        for (k = 0; k < NSIZE; k++) {
            size_t len = SIZES[k], n, rl2;
            int kk;
            for (kk = 0; kk < (int)len; kk++)
                src[kk] = (unsigned char)((kk * 31 + len) & 0xff);
            d1[0] = src;
            l1[0] = len;

            spath(img, sizeof(img), "rt.yaffs2");
            snprintf(outdir, sizeof(outdir), "%s/rt%zu", g_scratch, len);
            snprintf(label, sizeof(label), "往返 %zu 字节：合成镜像成功", len);
            if (build_image(img, one, d1, l1, 1) != 0) {
                expect(0, label, "");
                continue;
            }
            remove(outdir);
            snprintf(args, sizeof(args), "-c 2 -s 64 \"%s\" \"%s\"", img, outdir);
            if (run_capture(args, buf, sizeof(buf)) < 0) {
                snprintf(label, sizeof(label), "往返 %zu 字节：提取进程正常执行", len);
                expect(0, label, "");
                continue;
            }
            spath(p1, sizeof(p1), "f0.bin");
            /* 路径是 <outdir>/f0.bin，重新拼 */
            snprintf(p1, sizeof(p1), "%s/f0.bin", outdir);
            if (read_file(p1, got, sizeof(got), &rl2) != 0) {
                snprintf(label, sizeof(label), "往返 %zu 字节：提取出 f0.bin", len);
                expect(0, label, p1);
                continue;
            }
            n = (rl2 < len) ? rl2 : len;
            {
                char what[192], dd[160];
                int same = (rl2 == len) && (len == 0 || memcmp(got, src, len) == 0);
                snprintf(what, sizeof(what),
                         "往返 %zu 字节：提取内容逐字节一致（实际 %zu 字节）", len, rl2);
                snprintf(dd, sizeof(dd), "期望 %zu 字节，实际 %zu 字节%s", len, rl2,
                         (len && rl2 == len && memcmp(got, src, n) != 0) ? "，内容不同" : "");
                expect(same, what, same ? "" : dd);
            }
        }
    }

    /* ── 6. 多文件集合：列表条数 == 文件数 + 1（"."）── */
    {
        static const char *const names[] = { "a.txt", "c.txt", "d.bin", "e" };
        static const unsigned char c0[] = "alpha";
        static const unsigned char c2[] = { 0x00, 0xff, 0x7f, 0x80 };
        static const unsigned char c3[] = "e";
        const unsigned char *datas[4];
        size_t lens[4];
        int lines = 0;
        const char *p;

        datas[0] = c0; lens[0] = 5;
        datas[1] = (const unsigned char *)"nested";
        lens[1] = 6;
        datas[2] = c2; lens[2] = 4;
        datas[3] = c3; lens[3] = 1;

        spath(img, sizeof(img), "multi.yaffs2");
        if (build_image(img, names, datas, lens, 4) == 0) {
            snprintf(args, sizeof(args), "-c 2 -s 64 -t \"%s\"", img);
            printf("── unyaffs -c 2 -s 64 -t <multi>（4 个文件）\n");
            rc = run_capture(args, buf, sizeof(buf));
            expect(rc == 0, "多文件列表退出码 (期望 0)", "");
            for (p = buf; *p; p++)
                if (*p == '\n')
                    lines++;
            {
                char what[160], dd[96];
                snprintf(what, sizeof(what), "列表行数 == 文件数+1 (5)，实际 %d", lines);
                snprintf(dd, sizeof(dd), "实际 %d 行", lines);
                expect(lines == 5, what, lines == 5 ? "" : dd);
            }
            expect_contains("多文件列表", buf, "a.txt");
            expect_contains("多文件列表", buf, "d.bin");
        } else {
            expect(0, "合成多文件镜像成功", "");
        }
    }

    /* ── 6b. 文件名合法性校验：含 '/' 的对象名必须被拒绝而非静默写出 ──
     *     上游用 "Illegal file name" 明确报错，避免路径穿越（对象名里带
     *     分隔符可让提取写到目标目录之外）。这里断言该拒绝行为存在。 */
    {
        static const char *const bad[] = { "evil/../escape.txt" };
        static const unsigned char payload[] = "pwned";
        const unsigned char *bd[1];
        size_t bl[1];

        bd[0] = payload;
        bl[0] = 5;
        spath(img, sizeof(img), "badname.yaffs2");
        if (build_image(img, bad, bd, bl, 1) == 0) {
            spath(outdir, sizeof(outdir), "badout");
            remove(outdir);
            snprintf(args, sizeof(args), "-c 2 -s 64 \"%s\" \"%s\"", img, outdir);
            printf("── unyaffs -c 2 -s 64 <badname> <badout>（对象名含 '/'）\n");
            rc = run_capture(args, buf, sizeof(buf));
            expect(rc != 0, "含 '/' 的对象名被拒绝（非 0 退出码）", "");
            expect_contains("非法文件名", buf, "Illegal file name");
            /* 断言没有写到目标目录之外 */
            spath(p1, sizeof(p1), "escape.txt");
            {
                FILE *f = fopen(p1, "rb");
                expect(f == NULL, "未在 scratch 根目录写出 escape.txt（无路径穿越）", p1);
                if (f)
                    fclose(f);
            }
        } else {
            expect(0, "合成非法文件名镜像成功", "");
        }
    }

    /* ── 7. 损坏输入的错误路径 ── */
    {
        spath(p1, sizeof(p1), "empty.img");
        {
            FILE *f = fopen(p1, "wb");
            if (f)
                fclose(f);          /* 0 字节 */
        }
        snprintf(args, sizeof(args), "-t \"%s\"", p1);
        printf("── unyaffs -t <0 字节文件>\n");
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 1, "空文件退出码 (期望 1)", "");
        expect_contains("空文件", buf, "Can't determine flash layout");

        spath(p1, sizeof(p1), "garbage.img");
        {
            FILE *f = fopen(p1, "wb");
            if (f) {
                for (i = 0; i < 4096; i++)
                    fputc((i * 13 + 7) & 0xff, f);
                fclose(f);
            }
        }
        snprintf(args, sizeof(args), "-t \"%s\"", p1);
        printf("── unyaffs -t <随机字节文件>\n");
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 1, "随机文件退出码 (期望 1)", "");
        expect_contains("随机文件", buf, "Can't determine flash layout");

        /* 截断的合法镜像：只保留前 1.5 个 chunk */
        spath(p2, sizeof(p2), "trunc.img");
        {
            FILE *in, *out;
            unsigned char tmp[4096];
            size_t n;
            spath(img, sizeof(img), "image1.yaffs2");
            in = fopen(img, "rb");
            out = fopen(p2, "wb");
            if (in && out) {
                n = fread(tmp, 1, sizeof(tmp), in);
                fwrite(tmp, 1, n, out);
            }
            if (in)
                fclose(in);
            if (out)
                fclose(out);
        }
        snprintf(args, sizeof(args), "-c 2 -s 64 -t \"%s\"", p2);
        printf("── unyaffs -c 2 -s 64 -t <截断镜像>\n");
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc >= 0, "截断镜像未导致进程异常终止（非信号/非 126,127,>=128）", "");
    }

summary:
    printf("\n=== 汇总: %d 通过, %d 失败 ===\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
