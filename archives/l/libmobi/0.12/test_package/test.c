/* libmobi 0.12 test_package — 真实消费公开 API 的往返与负向输入测试。
 *
 * fixture 策略：MOBI 是复杂二进制容器（PalmDB 容器 + record0 三层嵌套头），
 * 但字段布局完全公开（上游 mobi.h 结构体偏移注释 + read.c 解析顺序），
 * 且经样本 sample-ncx.mobi 交叉验证：整文件为大端字节序（buffer_get32 为
 * data[0]<<24|…，记录表 offset 大端）。因此 fixture 在测试内程序化生成 ——
 * 不提交任何来源不明的二进制样本。
 *
 * 正向链路：构造最小合法 MOBI（未压缩文本）→ mobi_load_filename 载入 →
 *   元数据（EXTH title/author、full name）→ 谓词（is_mobipocket/未加密/KF7）→
 *   文本解压（mobi_get_rawml 逐字节比对）→ 记录访问（mobi_get_record_by_seqnumber）。
 *   桩实现（只装符号无逻辑）无法通过任一环节。
 *
 * 负向链路（全部断言具体返回码，非仅“不崩溃”）：
 *   空文件/截断 PDB 头/截断记录表/rec_count=0 → MOBI_DATA_CORRUPT
 *   错误 type magic → MOBI_FILE_UNSUPPORTED
 *   不存在路径 → MOBI_FILE_NOT_FOUND
 *   越界 record offset → MOBI_DATA_CORRUPT（fread 短读）
 *   record0 < 16 字节 → MOBI_DATA_CORRUPT
 *   错误 MOBI magic → load 仍 SUCCESS（parse_record0 吞错），但 mh==NULL、
 *     mobi_is_mobipocket 为假 —— 断言“半解析状态”而非返回码
 *   EXTH 越界长度 → exth 丢弃（eh==NULL），title 缺失
 *   文本缓冲过小 → MOBI_PARAM_ERR
 *
 * 布局依据（全部相对 record0 数据起点，大端）：
 *   [0..16)   Palmdoc 头：compression(2)=1 text_length(4) trcount(2)=1
 *             trsize(2)=4096 encryption(2)=0 unknown1(2)
 *   [16..)    MOBI 头：magic(4)="MOBI" header_length(4)=0xe4 …
 *   [+84]     full_name_offset(4) —— record0 内偏移（非文件偏移）
 *   [+128]    exth_flags(4) bit6=0x40 → EXTH 存在
 *   [+232..)  EXTH：magic(4) length(4) count(4) 记录(tag(4) size(4) data…)
 *   之后      full name 字符串
 */
#include <mobi.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>

static int failures = 0;
static int checks = 0;
#define CHECK(c, m) do { ++checks; if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                       else printf("[ok] %s\n", (m)); } while (0)

/* ---------- 大端写字节流助手（整文件大端，含 PDB 记录表） ---------- */
typedef struct { unsigned char b[640]; size_t len; } buf_t;

static void put16(buf_t *b, uint16_t v) { b->b[b->len++] = (v >> 8) & 0xff; b->b[b->len++] = v & 0xff; }
static void put32(buf_t *b, uint32_t v) {
    b->b[b->len++] = (v >> 24) & 0xff; b->b[b->len++] = (v >> 16) & 0xff;
    b->b[b->len++] = (v >> 8) & 0xff; b->b[b->len++] = v & 0xff;
}
static void puts_(buf_t *b, const char *s) { memcpy(b->b + b->len, s, strlen(s)); b->len += strlen(s); }
static void fill32(buf_t *b, size_t n) { for (size_t i = 0; i < n; i++) put32(b, 0); }

/*
 * 构造最小合法 MOBI（KF7，无压缩，2 条记录）：
 *   PDB 头 78B（name/type=BOOK/creator=MOBI/rec_count=2）+ 记录表 2×8B
 *   record0（偏移 94）：Palmdoc 头 16B + MOBI 头 0xe4B + EXTH + full name
 *   record1：未压缩文本
 */
static size_t build_minimal_mobi(unsigned char *out, size_t out_cap,
                                 const char *title, const char *author,
                                 const char *text, size_t text_len) {
    if (!out || !title || !author || !text) return 0;

    /* ---- record0 ---- */
    buf_t r0; memset(&r0, 0, sizeof r0);
    /* Palmdoc 头 */
    put16(&r0, 1);                    /* compression = NONE */
    put16(&r0, 0);                    /* unused */
    put32(&r0, (uint32_t) text_len);  /* text_length */
    put16(&r0, 1);                    /* text_record_count */
    put16(&r0, 4096);                 /* text_record_size */
    put16(&r0, 0);                    /* encryption = none */
    put16(&r0, 0);                    /* unknown1 */
    /* MOBI 头（header_length 字段起共 0xe4 字节；字段序列严格对照 read.c
     * mobi_parse_mobiheader 的读取顺序，偏移注释相对 record0 起点） */
    puts_(&r0, "MOBI");               /* magic @ +16 */
    put32(&r0, 0xe4);                 /* header_length @ +20 */
    put32(&r0, 2);                    /* mobi_type @ +24 */
    put32(&r0, 65001);                /* encoding @ +28 = UTF-8 */
    put32(&r0, 42);                   /* uid @ +32 */
    put32(&r0, 6);                    /* version @ +36 = 6 (KF7) */
    fill32(&r0, 10);                  /* orth..extra5 @ +40..+80 */
    put32(&r0, 0);                    /* non_text_index @ +80 */
    const size_t full_name_offset_pos = r0.len; /* @ +84，稍后回填 */
    put32(&r0, 0);                    /* full_name_offset（占位） */
    put32(&r0, 0);                    /* full_name_length（占位） */
    put32(&r0, 9);                    /* locale @ +92 = en-us */
    put32(&r0, 0);                    /* dict_input_lang @ +96 */
    put32(&r0, 0);                    /* dict_output_lang @ +100 */
    put32(&r0, 6);                    /* min_version @ +104 */
    put32(&r0, 0);                    /* image_index @ +108 */
    put32(&r0, 0);                    /* huff_rec_index @ +112 */
    put32(&r0, 0);                    /* huff_rec_count @ +116 */
    put32(&r0, 0);                    /* datp_rec_index @ +120 */
    put32(&r0, 0);                    /* datp_rec_count @ +124 */
    put32(&r0, 0x40);                 /* exth_flags @ +128：EXTH 存在 */
    fill32(&r0, 8);                   /* 32 unknown 字节 @ +132..+164 */
    put32(&r0, 0);                    /* unknown6 @ +164 */
    put32(&r0, 0xffffffff);           /* drm_offset @ +168 = NOTSET */
    put32(&r0, 0);                    /* drm_count @ +172 */
    put32(&r0, 0);                    /* drm_size @ +176 */
    put32(&r0, 0);                    /* drm_flags @ +180 */
    fill32(&r0, 2);                   /* 8 unknown 字节 @ +184..+192 */
    put16(&r0, 0);                    /* first_text_index @ +192 (KF7) */
    put16(&r0, 0);                    /* last_text_index @ +194 (KF7) */
    put32(&r0, 0);                    /* fdst_section_count @ +196 */
    put32(&r0, 0);                    /* fcis_index @ +200 */
    put32(&r0, 0);                    /* fcis_count @ +204 */
    put32(&r0, 0);                    /* flis_index @ +208 */
    put32(&r0, 0);                    /* flis_count @ +212 */
    put32(&r0, 0);                    /* unknown10 @ +216 */
    put32(&r0, 0);                    /* unknown11 @ +220 */
    put32(&r0, 0);                    /* srcs_index @ +224 */
    put32(&r0, 0);                    /* srcs_count @ +228 */
    put32(&r0, 0);                    /* unknown12 @ +232 */
    put32(&r0, 0);                    /* unknown13 @ +236 */
    put16(&r0, 0);                    /* 2 字节 fill @ +240 */
    put16(&r0, 0);                    /* extra_flags @ +242 = 0（无尾部附加数据） */
    /* read.c 语义：MOBI 头字段解析到 record0 + header_length + 8 处截断
     * （header_length 从 magic 起算：+16 magic +4 header_length +4 → 字段区
     * 到 +16+0xe4 = +244）。exth 解析从 buf 当前位置（+244）开始，
     * EXTH 头必须紧接 record0+244 放置 —— ncx/unknown14..20 在本
     * header_length 下不被读取，无需写入。 */
    /* ---- EXTH（record0+244 起）---- */
    const size_t exth_start = r0.len;
    const size_t title_len = strlen(title);
    const size_t author_len = strlen(author);
    size_t exth_len = 12 + 8 + title_len + 8 + author_len;
    const size_t pad = (4 - (exth_len % 4)) % 4;
    exth_len += pad;
    puts_(&r0, "EXTH");
    put32(&r0, (uint32_t) exth_len);  /* 含 magic+length+count+records+pad */
    put32(&r0, 2);                    /* 记录数 */
    put32(&r0, 99);                   /* EXTH_TITLE */
    put32(&r0, (uint32_t) (8 + title_len));
    puts_(&r0, title);
    put32(&r0, 100);                  /* EXTH_AUTHOR */
    put32(&r0, (uint32_t) (8 + author_len));
    puts_(&r0, author);
    while (r0.len - exth_start < exth_len) r0.b[r0.len++] = 0;
    /* ---- full name（EXTH 之后）---- */
    const size_t fullname_off_in_rec0 = r0.len; /* record0 内偏移 */
    /* 回填 full_name_offset / full_name_length（均为大端 u32 @ record0+84） */
    uint32_t v = (uint32_t) fullname_off_in_rec0;
    r0.b[full_name_offset_pos]     = (v >> 24) & 0xff;
    r0.b[full_name_offset_pos + 1] = (v >> 16) & 0xff;
    r0.b[full_name_offset_pos + 2] = (v >> 8) & 0xff;
    r0.b[full_name_offset_pos + 3] = v & 0xff;
    uint32_t fl = (uint32_t) strlen(title); /* full name 与 title 同串 */
    r0.b[full_name_offset_pos + 4] = (fl >> 24) & 0xff;
    r0.b[full_name_offset_pos + 5] = (fl >> 16) & 0xff;
    r0.b[full_name_offset_pos + 6] = (fl >> 8) & 0xff;
    r0.b[full_name_offset_pos + 7] = fl & 0xff;
    puts_(&r0, title);

    /* ---- PDB 头 + 记录表（全部大端）---- */
    buf_t outb; memset(&outb, 0, sizeof outb);
    char name[32]; memset(name, 0, sizeof name);
    snprintf(name, sizeof name, "libmobi-test");
    memcpy(outb.b + outb.len, name, 32); outb.len += 32;
    put16(&outb, 0);                  /* attributes */
    put16(&outb, 0);                  /* version */
    put32(&outb, 0); put32(&outb, 0); put32(&outb, 0); /* ctime/mtime/btime */
    put32(&outb, 0);                  /* mod_num */
    put32(&outb, 0);                  /* appinfo_offset */
    put32(&outb, 0);                  /* sortinfo_offset */
    puts_(&outb, "BOOK");             /* type @ 60 */
    puts_(&outb, "MOBI");             /* creator @ 64 */
    put32(&outb, 0);                  /* uid @ 68 */
    put32(&outb, 0);                  /* next_rec @ 72 */
    put16(&outb, 2);                  /* rec_count @ 76 */
    const size_t rec0_off = 78 + 2 * 8; /* = 94 */
    const size_t rec1_off = rec0_off + r0.len;
    put32(&outb, (uint32_t) rec0_off); put16(&outb, 0); put16(&outb, 0);
    put32(&outb, (uint32_t) rec1_off); put16(&outb, 0); put16(&outb, 1);
    memcpy(outb.b + outb.len, r0.b, r0.len); outb.len += r0.len;
    memcpy(outb.b + outb.len, text, text_len); outb.len += text_len;

    if (outb.len > out_cap) return 0;
    memcpy(out, outb.b, outb.len);
    return outb.len;
}

static int write_file(const char *path, const unsigned char *data, size_t len) {
    FILE *f = fopen(path, "wb");
    if (!f) return -1;
    size_t n = fwrite(data, 1, len, f);
    fclose(f);
    return n == len ? 0 : -1;
}

int main(void) {
    const char *good = "./_libmobi_probe.mobi";
    const char *bad = "./_libmobi_bad.mobi";
    const char *title = "Harmony PC Test Book";
    const char *author = "AtomCode";
    const char *text = "<html><body><p>harmony-pc libmobi roundtrip</p></body></html>";
    size_t text_len = strlen(text);
    unsigned char doc[640];
    size_t doc_len = build_minimal_mobi(doc, sizeof doc, title, author, text, text_len);
    CHECK(doc_len > 0 && doc_len <= sizeof doc, "程序化生成最小 MOBI fixture（大端布局）");

    /* ========== 正向链路 ========== */
    CHECK(write_file(good, doc, doc_len) == 0, "fixture 写盘（CWD，非 /tmp）");

    MOBIData *m = mobi_init();
    CHECK(m != NULL, "mobi_init 成功");
    MOBI_RET ret = mobi_load_filename(m, good);
    CHECK(ret == MOBI_SUCCESS, "mobi_load_filename 载入成功");
    if (ret == MOBI_SUCCESS) {
        char *t = mobi_meta_get_title(m);
        CHECK(t != NULL && strcmp(t, title) == 0, "EXTH title 读取一致");
        free(t);
        char *a = mobi_meta_get_author(m);
        CHECK(a != NULL && strcmp(a, author) == 0, "EXTH author 读取一致");
        free(a);
        char fullname[256];
        ret = mobi_get_fullname(m, fullname, sizeof fullname);
        CHECK(ret == MOBI_SUCCESS && strcmp(fullname, title) == 0, "full name 读取一致");
        CHECK(mobi_get_fileversion(m) == 6, "fileversion == 6 (KF7)");
        CHECK(mobi_is_mobipocket(m), "mobi_is_mobipocket 为真");
        CHECK(!mobi_is_encrypted(m), "未加密");
        CHECK(!mobi_is_kf8(m), "非 KF8");
        CHECK(!mobi_is_hybrid(m), "非 hybrid");
        /* 文本解压链（未压缩记录直通） */
        size_t maxlen = mobi_get_text_maxsize(m);
        CHECK(maxlen >= text_len, "text_maxsize 覆盖文本长度");
        char *raw = malloc(maxlen + 1);
        size_t rawlen = maxlen;
        ret = mobi_get_rawml(m, raw, &rawlen);
        CHECK(ret == MOBI_SUCCESS, "mobi_get_rawml 文本解析成功");
        if (ret == MOBI_SUCCESS) {
            CHECK(rawlen == text_len && memcmp(raw, text, text_len) == 0,
                  "解压文本与写入逐字节一致");
        }
        free(raw);
        /* 记录访问 */
        MOBIPdbRecord *rec = mobi_get_record_by_seqnumber(m, 1);
        CHECK(rec != NULL && rec->size == text_len &&
              memcmp(rec->data, text, text_len) == 0, "record 1 数据逐字节一致");
        CHECK(mobi_get_record_by_seqnumber(m, 99) == NULL, "越界 seqnumber 返回 NULL");
    }
    mobi_free(m);

    /* ========== 负向链路（断言具体返回码/状态） ========== */
    unsigned char doc2[640];
    MOBIData *m2;

    /* 1. 不存在的文件 */
    m2 = mobi_init();
    CHECK(mobi_load_filename(m2, bad) == MOBI_FILE_NOT_FOUND, "不存在文件 → MOBI_FILE_NOT_FOUND");
    mobi_free(m2);

    /* 2. 空文件（PDB 头 fread 不足 78 字节） */
    CHECK(write_file(bad, doc, 0) == 0, "写空文件");
    m2 = mobi_init();
    CHECK(mobi_load_filename(m2, bad) == MOBI_DATA_CORRUPT, "空文件 → MOBI_DATA_CORRUPT");
    mobi_free(m2);

    /* 3. 截断 PDB 头（40 字节） */
    CHECK(write_file(bad, doc, 40) == 0, "写截断 PDB 头文件");
    m2 = mobi_init();
    CHECK(mobi_load_filename(m2, bad) == MOBI_DATA_CORRUPT, "截断 PDB 头 → MOBI_DATA_CORRUPT");
    mobi_free(m2);

    /* 4. 截断记录表（88 字节：头 78 + 10/16 记录表项） */
    CHECK(write_file(bad, doc, 88) == 0, "写截断记录表文件");
    m2 = mobi_init();
    CHECK(mobi_load_filename(m2, bad) == MOBI_DATA_CORRUPT, "截断记录表 → MOBI_DATA_CORRUPT");
    mobi_free(m2);

    /* 5. 错误 type magic（BOOK → BROK，@ offset 60） */
    memcpy(doc2, doc, doc_len);
    memcpy(doc2 + 60, "BROK", 4);
    CHECK(write_file(bad, doc2, doc_len) == 0, "写错误 type fixture");
    m2 = mobi_init();
    CHECK(mobi_load_filename(m2, bad) == MOBI_FILE_UNSUPPORTED, "错误 type magic → MOBI_FILE_UNSUPPORTED");
    mobi_free(m2);

    /* 6. rec_count = 0（@ offset 76） */
    memcpy(doc2, doc, doc_len);
    doc2[76] = 0; doc2[77] = 0;
    CHECK(write_file(bad, doc2, doc_len) == 0, "写 rec_count=0 fixture");
    m2 = mobi_init();
    CHECK(mobi_load_filename(m2, bad) == MOBI_DATA_CORRUPT, "rec_count=0 → MOBI_DATA_CORRUPT");
    mobi_free(m2);

    /* 7. 越界 record offset（rec0.offset=0xffffffff @ offset 78） */
    memcpy(doc2, doc, doc_len);
    doc2[78] = 0xff; doc2[79] = 0xff; doc2[80] = 0xff; doc2[81] = 0xff;
    CHECK(write_file(bad, doc2, doc_len) == 0, "写越界 offset fixture");
    m2 = mobi_init();
    CHECK(mobi_load_filename(m2, bad) == MOBI_DATA_CORRUPT, "越界 record offset → MOBI_DATA_CORRUPT");
    mobi_free(m2);

    /* 8. record0 截断（rec1 紧贴 rec0+8 → record0.size=8 < 16） */
    memcpy(doc2, doc, doc_len);
    doc2[86] = 0; doc2[87] = 0; doc2[88] = 0; doc2[89] = (94 + 8) & 0xff; /* rec1.offset 大端 */
    CHECK(write_file(bad, doc2, doc_len) == 0, "写短 record0 fixture");
    m2 = mobi_init();
    CHECK(mobi_load_filename(m2, bad) == MOBI_DATA_CORRUPT, "record0 < 16 字节 → MOBI_DATA_CORRUPT");
    mobi_free(m2);

    /* 9. 错误 MOBI magic（record0+16 "MOBI" → "XOBI"）
     *    parse_record0 吞掉 parse_mobiheader 的错误 → load 仍 SUCCESS，
     *    断言半解析状态：mh==NULL 且 is_mobipocket 为假 */
    memcpy(doc2, doc, doc_len);
    memcpy(doc2 + 94 + 16, "XOBI", 4);
    CHECK(write_file(bad, doc2, doc_len) == 0, "写错误 MOBI magic fixture");
    m2 = mobi_init();
    CHECK(mobi_load_filename(m2, bad) == MOBI_SUCCESS && m2->mh == NULL,
          "错误 MOBI magic → load SUCCESS 但半解析（mh 丢弃）");
    mobi_free(m2);

    /* 10. EXTH 声明越界长度（length 字段 @ record0+244+4，改为 0xffff） */
    memcpy(doc2, doc, doc_len);
    {
        const size_t exth_len_pos = 94 + 244 + 4;
        doc2[exth_len_pos] = 0xff; doc2[exth_len_pos + 1] = 0xff;
        doc2[exth_len_pos + 2] = 0x00; doc2[exth_len_pos + 3] = 0x00;
    }
    CHECK(write_file(bad, doc2, doc_len) == 0, "写 EXTH 越界长度 fixture");
    m2 = mobi_init();
    ret = mobi_load_filename(m2, bad);
    CHECK((ret == MOBI_SUCCESS && m2->eh == NULL) || ret == MOBI_DATA_CORRUPT,
          "EXTH 越界长度 → EXTH 丢弃（eh==NULL）或 DATA_CORRUPT");
    mobi_free(m2);

    /* 11. Palmdoc compression 非法（record0+0 改 0x9999）→ DATA_CORRUPT */
    memcpy(doc2, doc, doc_len);
    doc2[94] = 0x99; doc2[95] = 0x99;
    CHECK(write_file(bad, doc2, doc_len) == 0, "写非法 compression fixture");
    m2 = mobi_init();
    CHECK(mobi_load_filename(m2, bad) == MOBI_DATA_CORRUPT, "非法 compression → MOBI_DATA_CORRUPT");
    mobi_free(m2);

    /* 12. 文本缓冲过小 → MOBI_PARAM_ERR（参数化负向） */
    m2 = mobi_init();
    if (mobi_load_filename(m2, good) == MOBI_SUCCESS) {
        char small[4];
        size_t small_len = 1;
        CHECK(mobi_get_rawml(m2, small, &small_len) == MOBI_PARAM_ERR,
              "文本缓冲过小 → MOBI_PARAM_ERR");
    }
    mobi_free(m2);


    unlink(good);
    unlink(bad);
    /* 调试注记：unlink 必须保留 —— 负向用例 1 依赖 bad 文件确实不存在 */

    if (failures) { fprintf(stderr, "\nlibmobi: %d/%d 项断言失败\n", failures, checks); return 1; }
    printf("\nlibmobi 0.12: 全部 %d 项断言通过（载入 → 元数据 → 文本 → 记录 → 负向返回码）\n", checks);
    return 0;
}
