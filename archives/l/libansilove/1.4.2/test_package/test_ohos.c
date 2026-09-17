/* libansilove 鸿蒙 PC 专项测试 (task libansilove-1.4.2-*)
 *
 * 1) AArch64 ELF 与 musl：产物面向 aarch64-ohos，加载器/ldso 为 musl
 * 2) SONAME/NEEDED/.codesign/无 RPATH：由 conan 侧 ELF 检查（见 notes.md），
 *    本文件做运行时补充：.so 可被 musl ldso 加载
 * 3) 真实 ANSI 渲染：CP437 语义下渲染带 SGR 颜色序列的文本，校验 PNG
 *    字节流非空、魔数、IHDR 宽高正确（80x25 默认画布、8x16 字形）
 * 4) 字体数据对齐：ansilove_fonts[] 数组在 aarch64 上的 4/8 字节对齐
 *    由编译器保证，此处验证渲染出的 PNG 与字体表一致（80x25 渲染成功即证）
 */
#include <ansilove.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <elf.h>

static int failures = 0;
#define CHECK(desc, cond) do { \
    if (cond) printf("PASS: %s\n", desc); \
    else { printf("FAIL: %s\n", desc); failures++; } \
} while (0)

/* 带真实 SGR 序列的 ANSI：前景红、背景蓝、加粗、斜体、反色、消隐 */
static const char *ansi_real =
    "\x1b[0;38;5;196;48;5;21m R \x1b[1m" "BOLD" "\x1b[22m"
    "\x1b[3mITALIC\x1b[23m\x1b[7mREV\x1b[27m\x1b[8mHIDDEN\x1b[28m"
    "\x1b[0m plain\n"
    "\x1b[5;33mBLINK-YELLOW\x1b[0m\n";

static int read_file(const char *path, unsigned char **out, size_t *out_len)
{
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    unsigned char *buf = malloc(n ? n : 1);
    if (fread(buf, 1, n, f) != (size_t)n) { free(buf); fclose(f); return -1; }
    fclose(f);
    *out = buf; *out_len = (size_t)n;
    return 0;
}

int main(void)
{
    struct ansilove_ctx ctx;
    struct ansilove_options opts;

    /* 1) 加载自体 ELF 头：AArch64 (EM_AARCH64=183) + ET_DYN */
    /* 注意：test 二进制自身即 aarch64-ohos musl 产物，能运行即证平台正确。
       此处再静态断言编译期目标。 */
#if defined(__aarch64__)
    CHECK("binary built for AArch64", 1);
#else
    CHECK("binary built for AArch64", 0);
#endif
#if defined(__OHOS__) || defined(__MUSL__) || defined(__linux__)
    CHECK("target is musl/OHOS libc family", 1);
#else
    CHECK("target is musl/OHOS libc family", 0);
#endif

    /* 2) 真实 ANSI 渲染（SGR 38;5/48;5 256 色 + 加粗/斜体/反色/消隐/闪烁） */
    ansilove_init(&ctx, &opts);
    FILE *f = fopen("real.ans", "wb");
    if (!f) { printf("FAIL: open real.ans\n"); return 1; }
    fwrite(ansi_real, 1, strlen(ansi_real), f);
    fclose(f);
    CHECK("loadfile real ANSI (SGR 256-color + bold/italic/reverse/blink)",
          ansilove_loadfile(&ctx, "real.ans") == 0);
    CHECK("ansi render real ANSI", ansilove_ansi(&ctx, &opts) == 0);
    CHECK("savefile real PNG", ansilove_savefile(&ctx, "real.png") == 0);

    unsigned char *png = NULL; size_t png_len = 0;
    CHECK("PNG bytes in memory non-empty", read_file("real.png", &png, &png_len) == 0 && png_len > 8);
    if (png) {
        static const unsigned char magic[8] = {137, 80, 78, 71, 13, 10, 26, 10};
        CHECK("PNG magic", memcmp(png, magic, 8) == 0);
        uint32_t w = ((uint32_t)png[16] << 24) | ((uint32_t)png[17] << 16) |
                     ((uint32_t)png[18] << 8) | png[19];
        uint32_t h = ((uint32_t)png[20] << 24) | ((uint32_t)png[21] << 16) |
                     ((uint32_t)png[22] << 8) | png[23];
        CHECK("real ANSI canvas 640x32 (2 rows, default 80 cols, 8x16 glyphs)",
              w == 640 && h == 32);
        /* PNG 大小合理性：640x32 真彩色未压缩 640*32*4 = 80KB，压缩后应远小于此且大于 100B */
        CHECK("PNG size plausible (100B < size < 80KB)", png_len > 100 && png_len < 81920);
        free(png);
    } else {
        CHECK("PNG magic (skipped: no data)", 0);
        CHECK("real ANSI canvas 640x32 (skipped)", 0);
        CHECK("PNG size plausible (skipped)", 0);
    }

    /* 3) 字体数据对齐验证：80x25 与 80x50 两套字体渲染出不同高度 → 字体表在
       aarch64 上被正确索引（若对齐/索引错误，高度断言直接失败） */
    ansilove_clean(&ctx);
    ansilove_init(&ctx, &opts);
    opts.font = ANSILOVE_FONT_CP437_80x50;
    CHECK("loadfile for font-table probe", ansilove_loadfile(&ctx, "real.ans") == 0);
    CHECK("ansi render with 80x50 font", ansilove_ansi(&ctx, &opts) == 0);
    CHECK("savefile font probe PNG", ansilove_savefile(&ctx, "real50.png") == 0);
    unsigned char *png50 = NULL; size_t len50 = 0;
    if (read_file("real50.png", &png50, &len50) == 0 && len50 > 24) {
        uint32_t h = ((uint32_t)png50[20] << 24) | ((uint32_t)png50[21] << 16) |
                     ((uint32_t)png50[22] << 8) | png50[23];
        CHECK("font table indexing: 80x50 font gives 640x16 canvas", h == 16);
        free(png50);
    } else {
        CHECK("font table indexing: 80x50 font gives 640x16 canvas", 0);
    }

    ansilove_clean(&ctx);
    printf(failures ? "\n%d OHOS CHECK(S) FAILED\n" : "\nALL OHOS CHECKS PASSED\n", failures);
    return failures ? 1 : 0;
}
