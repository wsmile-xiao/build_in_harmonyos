/* libmobi 0.12 鸿蒙特有测试 — 平台制品身份与真实解析（独立入口，不计入
 * 消费者测试 test.c 的 39 项内部检查）。
 *
 * 背景：HarmonyOS PC XPM 环境对包制品有两类平台性要求，缺一即运行期失败：
 *   1. 代码签名：dlopen/exec 的 ELF 必须带有效 .codesign 段（配方的
 *      _sign_binaries 用 binary-sign-tool 注入），否则 Permission denied；
 *   2. musl 链接：NDK 工具链产物 NEEDED 仅 libc.so（musl）等系统库，
 *      若误链 glibc 或 x86_64 产物，设备上无法加载。
 * 另验证 SONAME 传播（libmobi.so.0）与真实文件解析能力（非 mock）。
 *
 * 实现约束：不依赖外部 readelf/file —— 用最小 ELF64 解析器在测试内自证，
 * 避免测试身份依赖宿主工具布局；真实解析直接调用被测包的公开 API。
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

/* ---------- 最小 ELF64 大端/小端无关读取 ---------- */
static unsigned char *elf_map = NULL;
static size_t elf_size = 0;

static uint16_t rd16(const unsigned char *p, int le) {
    return le ? (uint16_t)(p[0] | (p[1] << 8)) : (uint16_t)((p[0] << 8) | p[1]);
}
static uint32_t rd32(const unsigned char *p, int le) {
    return le ? ((uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24))
              : (((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | (uint32_t)p[3]);
}
static uint64_t rd64(const unsigned char *p, int le) {
    return ((uint64_t)rd32(p + 4, le) << 32) | rd32(p, le);
}

static int elf_load(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END); elf_size = (size_t) ftell(f); fseek(f, 0, SEEK_SET);
    elf_map = malloc(elf_size ? elf_size : 1);
    if (!elf_map || fread(elf_map, 1, elf_size, f) != elf_size) { fclose(f); free(elf_map); elf_map = NULL; return -1; }
    fclose(f);
    if (elf_size < 64 || memcmp(elf_map, "\x7f" "ELF", 4) != 0) { free(elf_map); elf_map = NULL; return -1; }
    return 0;
}
static void elf_unload(void) { free(elf_map); elf_map = NULL; elf_size = 0; }

/* 期望：ELF64、AArch64 (EM_AARCH64=183)、共享对象或可执行 */
static int elf_check_aarch64(void) {
    if (elf_map[4] != 2 /* ELFCLASS64 */) return 0;
    if (rd16(elf_map + 18, elf_map[5] == 1) != 183 /* EM_AARCH64 */) return 0;
    return 1;
}

/* 遍历 PT_DYNAMIC：返回 (tag,value) 回调消费；le = little-endian 数据编码 */
typedef void (*dyn_cb)(uint64_t tag, uint64_t val, void *user);
static void elf_foreach_dynamic(dyn_cb cb, void *user) {
    int le = (elf_map[5] == 1);                    /* EI_DATA: 1=LSB 2=MSB */
    uint16_t phentsize = rd16(elf_map + 54, le);
    uint16_t phnum = rd16(elf_map + 56, le);
    uint64_t phoff = rd64(elf_map + 32, le);
    for (uint16_t i = 0; i < phnum; i++) {
        const unsigned char *ph = elf_map + phoff + (size_t) i * phentsize;
        if (rd32(ph, le) != 2 /* PT_DYNAMIC */) continue;
        uint64_t off = rd64(ph + 8, le);           /* p_offset */
        for (size_t n = 0; ; n++) {
            const unsigned char *d = elf_map + off + n * 16;
            uint64_t tag = rd64(d, le);
            uint64_t val = rd64(d + 8, le);
            if (tag == 0) return;
            cb(tag, val, user);
        }
    }
}

/* ---------- PT_DYNAMIC 断言的收集器 ---------- */
struct dyninfo {
    int has_soname_libmobi;      /* DT_SONAME 字符串 == "libmobi.so.0" */
    int has_needed_libc;         /* 任一 DT_NEEDED 字符串 == "libc.so"（musl） */
    int has_needed_bad_libc;     /* DT_NEEDED 含 glibc 特征（libc.so.6 / ld-linux） */
    const char *strtab;          /* DT_STRTAB 内容（vaddr 已换算为文件内指针） */
};
/* ELF 内 vaddr→文件偏移换算（遍历 PT_LOAD，p_vaddr<=a<p_vaddr+p_filesz）。
 * DT_STRTAB/DT_SONAME 的 d_ptr 是链接期 vaddr，本配方产物 vaddr 与文件
 * 偏移存在固定差（见 readelf -l：LOAD vaddr 0xd35c vs offset 0xc35c），
 * 不换算会读到错位字符串。 */
static uint64_t elf_vaddr_to_off(uint64_t vaddr) {
    int le = (elf_map[5] == 1);
    uint16_t phentsize = rd16(elf_map + 54, le);
    uint16_t phnum = rd16(elf_map + 56, le);
    uint64_t phoff = rd64(elf_map + 32, le);
    for (uint16_t i = 0; i < phnum; i++) {
        const unsigned char *ph = elf_map + phoff + (size_t) i * phentsize;
        if (rd32(ph, le) != 1 /* PT_LOAD */) continue;
        uint64_t off = rd64(ph + 8, le);
        uint64_t vaddr0 = rd64(ph + 16, le);
        uint64_t filesz = rd64(ph + 32, le);
        if (vaddr >= vaddr0 && vaddr < vaddr0 + filesz) return off + (vaddr - vaddr0);
    }
    return UINT64_MAX;
}
/* 收集器：遍历两遍——DT_STRTAB 常排在 DT_NEEDED/DT_SONAME 之后（实测本产物
 * 顺序 NEEDED,SONAME,...,STRTAB），单遍会全部漏判。第一遍只取 strtab，
 * 第二遍做字符串判定。 */
static void dyn_collect_strtab(uint64_t tag, uint64_t val, void *user) {
    struct dyninfo *di = (struct dyninfo *) user;
    if (tag == 5 /* DT_STRTAB */) {
        uint64_t off = elf_vaddr_to_off(val);
        if (off != UINT64_MAX) di->strtab = (const char *) (elf_map + off);
    }
}
static void dyn_collect(uint64_t tag, uint64_t val, void *user) {
    struct dyninfo *di = (struct dyninfo *) user;
    if (tag == 5 /* DT_STRTAB */) {
        uint64_t off = elf_vaddr_to_off(val);
        if (off != UINT64_MAX) di->strtab = (const char *) (elf_map + off);
    } else if (tag == 14 /* DT_SONAME */ && di->strtab) {
        if (strcmp(di->strtab + val, "libmobi.so.0") == 0) di->has_soname_libmobi = 1;
    } else if (tag == 1 /* DT_NEEDED */ && di->strtab) {
        const char *n = di->strtab + val;
        if (strcmp(n, "libc.so") == 0) di->has_needed_libc = 1;
        if (strstr(n, "libc.so.6") == n || strstr(n, "ld-linux") == n) di->has_needed_bad_libc = 1;
    }
}

/* ---------- .codesign 段存在性（遍历节头表） ---------- */
static int elf_has_codesign_section(void) {
    int le = (elf_map[5] == 1);
    uint64_t shoff = rd64(elf_map + 40, le);
    uint16_t shentsize = rd16(elf_map + 58, le);
    uint16_t shnum = rd16(elf_map + 60, le);
    uint32_t shstrndx = rd16(elf_map + 62, le);
    if (shoff == 0 || shnum == 0 || shstrndx >= shnum) return 0;
    const unsigned char *shstr = elf_map + rd64(elf_map + shoff + (size_t) shstrndx * shentsize + 24, le);
    for (uint16_t i = 0; i < shnum; i++) {
        const unsigned char *sh = elf_map + shoff + (size_t) i * shentsize;
        uint32_t nameoff = rd32(sh, le);
        if (strcmp((const char *) (shstr + nameoff), ".codesign") == 0) return 1;
    }
    return 0;
}

/* ---------- 真实解析 fixture：最小合法 KF7 MOBI ----------
 * 与消费者测试 test.c 的构造器语义一致（字段序列对照 read.c
 * mobi_parse_mobiheader 读取顺序），独立保留一份（不 #include test.c），
 * 保持两个入口零耦合；差异仅在文本与 full name 内容。 */
static size_t build_minimal_mobi(unsigned char *out) {
    static const char text[] = "HarmonyOS ohos-specific real parse.";
    const size_t text_len = sizeof text - 1;
    const char *title = "ohos-check";
    const char *author = "atomcode";
    /* PDB 头内的大端 u32 写入辅助 */
    #define BE32(p, v) do { (p)[0] = ((v) >> 24) & 0xff; (p)[1] = ((v) >> 16) & 0xff; (p)[2] = ((v) >> 8) & 0xff; (p)[3] = (v) & 0xff; } while (0)
    const size_t title_len = strlen(title), author_len = strlen(author);
    const size_t r0_cap = 1024;
    unsigned char *r0 = calloc(1, r0_cap);
    size_t n = 0;
    #define P16(v) do { r0[n++] = ((v) >> 8) & 0xff; r0[n++] = (v) & 0xff; } while (0)
    #define P32(v) do { r0[n] = ((v) >> 24) & 0xff; r0[n+1] = ((v) >> 16) & 0xff; r0[n+2] = ((v) >> 8) & 0xff; r0[n+3] = (v) & 0xff; n += 4; } while (0)
    #define PS(s) do { memcpy(r0 + n, (s), strlen(s)); n += strlen(s); } while (0)

    /* Palmdoc 头 16B */
    P16(1); P16(0); P32((uint32_t) text_len); P16(1); P16(4096); P16(0); P16(0);
    /* MOBI 头：magic @+16，header_length=0xe4；字段序列严格对照 read.c
     * mobi_parse_mobiheader 读取顺序（与消费者测试 test.c 的构造器同构），
     * 偏移注释相对 record0 起点；跳字段会触发库内越界读（实测 SIGSEGV） */
    PS("MOBI");                       /* @ +16 */
    P32(0xe4);                        /* header_length @ +20 */
    P32(2);                           /* mobi_type @ +24 */
    P32(65001);                       /* encoding @ +28 = UTF-8 */
    P32(42);                          /* uid @ +32 */
    P32(6);                           /* version @ +36 = KF7 */
    n = 80;                           /* orth..extra5（10×u32 零）@ +40..+80 */
    P32(0);                           /* non_text_index @ +80 */
    const size_t fno_pos = n;         /* full_name_offset @ +84 */
    P32(0); P32(0);                   /* offset/length 占位 */
    P32(9);                           /* locale @ +92 */
    P32(0); P32(0);                   /* dict_input/output_lang @ +96/+100 */
    P32(6);                           /* min_version @ +104 */
    P32(0); P32(0); P32(0); P32(0);   /* image/huff_rec/datp @ +108..+124 */
    P32(0x40);                        /* exth_flags @ +128：EXTH 存在 */
    n = 164;                          /* unknown @ +132..+164 */
    P32(0);                           /* unknown6 @ +164 */
    P32(0xffffffff);                  /* drm_offset @ +168 = NOTSET */
    P32(0); P32(0); P32(0);           /* drm_count/size/flags @ +172..+180 */
    n = 192;                          /* unknown @ +184..+192 */
    P16(0); P16(0);                   /* first/last_text_index @ +192/+194 */
    P32(0);                           /* fdst_section_count @ +196 */
    P32(0); P32(0);                   /* fcis_index/count @ +200/+204 */
    P32(0); P32(0);                   /* flis_index/count @ +208/+212 */
    P32(0); P32(0);                   /* unknown10/11 @ +216/+220 */
    P32(0); P32(0);                   /* srcs_index/count @ +224/+228 */
    P32(0); P32(0);                   /* unknown12/13 @ +232/+236 */
    P16(0); P16(0);                   /* fill + extra_flags @ +240/+242 */
    /* read.c 语义：MOBI 头字段解析到 record0+244 截止，EXTH 紧接其后 */
    const size_t exth_start = n;
    size_t exth_len = 12 + 8 + title_len + 8 + author_len;
    exth_len += (4 - (exth_len % 4)) % 4;
    PS("EXTH"); P32((uint32_t) exth_len); P32(2);
    P32(99); P32((uint32_t)(8 + title_len)); PS(title);
    P32(100); P32((uint32_t)(8 + author_len)); PS(author);
    while (n - exth_start < exth_len) r0[n++] = 0;
    /* full name（EXTH 之后），回填 offset/length */
    const uint32_t fno = (uint32_t) n, fnl = (uint32_t) title_len;
    r0[fno_pos] = (fno >> 24) & 0xff; r0[fno_pos+1] = (fno >> 16) & 0xff;
    r0[fno_pos+2] = (fno >> 8) & 0xff; r0[fno_pos+3] = fno & 0xff;
    r0[fno_pos+4] = (fnl >> 24) & 0xff; r0[fno_pos+5] = (fnl >> 16) & 0xff;
    r0[fno_pos+6] = (fnl >> 8) & 0xff; r0[fno_pos+7] = fnl & 0xff;
    PS(title);

    /* PDB 头 78B + 记录表 2×8B + record0 + text */
    size_t rec0_off = 94, rec1_off = rec0_off + n, total = rec1_off + text_len;
    memset(out, 0, 94);
    memcpy(out, "ohos-libmobi", 12);
    memcpy(out + 60, "BOOK", 4);
    memcpy(out + 64, "MOBI", 4);
    out[76] = 0; out[77] = 2;          /* rec_count @ 76（u16）*/
    /* 记录表：offset/attr/uid 8B/项（rec1 uid=1，同 test.c） */
    BE32(out + 78, (uint32_t) rec0_off);
    BE32(out + 86, (uint32_t) rec1_off);
    out[90] = 0; out[91] = 0;         /* rec0 attr/uid */
    out[92] = 0; out[93] = 1;         /* rec1 attr=0, uid=1 */
    memcpy(out + rec0_off, r0, n);
    memcpy(out + rec1_off, text, text_len);
    free(r0);
    return total;
}

int main(int argc, char **argv) {
    /* 参数：包内 lib 与 bin 的路径（由 test_package 传入，避免硬编码布局） */
    if (argc < 3) {
        fprintf(stderr, "usage: %s <package-lib-dir> <package-bin-dir>\n", argv[0]);
        return 2;
    }
    char path[4096];

    /* ── 检查点 1：libmobi 共享库的平台身份 ── */
    snprintf(path, sizeof path, "%s/libmobi.so.0.0.0", argv[1]);
    CHECK(elf_load(path) == 0, "包内 libmobi.so.0.0.0 存在且为 ELF");
    if (elf_map) {
        CHECK(elf_check_aarch64(), "libmobi 为 ELF64 AArch64");
        struct dyninfo di; memset(&di, 0, sizeof di);
        elf_foreach_dynamic(dyn_collect_strtab, &di);
        elf_foreach_dynamic(dyn_collect, &di);
        CHECK(di.has_soname_libmobi, "SONAME == libmobi.so.0");
        CHECK(di.has_needed_libc && !di.has_needed_bad_libc, "NEEDED 为 musl（libc.so，无 glibc 特征）");
        CHECK(elf_has_codesign_section(), "libmobi 含 .codesign 签名段");
        elf_unload();
    }

    /* ── 检查点 2：CLI 工具的平台身份 ── */
    snprintf(path, sizeof path, "%s/mobitool", argv[2]);
    CHECK(elf_load(path) == 0, "包内 mobitool 存在且为 ELF");
    if (elf_map) {
        CHECK(elf_check_aarch64(), "mobitool 为 ELF64 AArch64");
        CHECK(elf_has_codesign_section(), "mobitool 含 .codesign 签名段");
        elf_unload();
    }

    /* ── 检查点 3：真实文件解析（包内库的公开 API，非 mock） ── */
    {
        unsigned char doc[4096];
        size_t doc_len = build_minimal_mobi(doc);
        const char *fname = "ohos_specific_real_parse.mobi";
        FILE *f = fopen(fname, "wb");
        CHECK(f && fwrite(doc, 1, doc_len, f) == doc_len, "写入真实 MOBI fixture 文件");
        if (f) fclose(f);

        MOBI_RET ret;
        MOBIData *m = mobi_init();
        ret = mobi_load_filename(m, fname);
        CHECK(ret == MOBI_SUCCESS, "mobi_load_filename 真实解析成功");
        if (ret == MOBI_SUCCESS) {
            /* 与消费者测试 test.c 相同的已验证 API 路径（mobi_get_fullname
             * 依赖 full_name_length 字段回填的精确语义，EXTH title 更稳） */
            char *t = mobi_meta_get_title(m);
            CHECK(t != NULL && strcmp(t, "ohos-check") == 0,
                  "真实解析：EXTH title 提取正确");
            free(t);
        }
        mobi_free(m);
        unlink(fname);
    }

    if (failures) { fprintf(stderr, "\nohos-specific: %d/%d 检查点失败\n", failures, checks); return 1; }
    printf("\nohos-specific libmobi 0.12: 全部 %d 项检查点通过（AArch64 ELF / musl / .codesign / SONAME / 真实解析）\n", checks);
    return 0;
}
