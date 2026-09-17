/* libansilove 消费者测试：内联 ANSI 文本走全链路 loadfile → ansi loader → savefile PNG。
 * 覆盖：解析、调色板（16 色 VGA）、字体/画布尺寸、PNG 输出（PNG 魔数+IHDR 宽高）、
 * 非法控制序列（错误码）。
 */
#include <ansilove.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/mman.h>

static int failures = 0;

#define CHECK(desc, cond) do { \
    if (cond) printf("PASS: %s\n", desc); \
    else { printf("FAIL: %s\n", desc); failures++; } \
} while (0)

/* 80 列经典 ANSI: ESC[1;31m 红色加粗 "HELLO" + ESC[0m 复位 + 换行收尾。
 * 上游 ANSI loader 以 80 列为默认画布宽。 */
static const char *ansi_hello =
    "\x1b[1;31mHELLO\x1b[0m libansilove\n"
    "\x1b[44m     \x1b[0m\n";

/* 非法控制序列：ESC 后跟未完成/不支持序列，loader 应拒收或忽略，不得崩溃 */
static const char *ansi_invalid = "\x1b[999999999m\x1b[?25hX\x1bQ\x1b[";

static int write_tmp(const char *path, const char *data, size_t len)
{
    FILE *f = fopen(path, "wb");
    if (!f) return -1;
    if (fwrite(data, 1, len, f) != len) { fclose(f); return -1; }
    fclose(f);
    return 0;
}

/* PNG 结构断言：魔数 + IHDR 里的宽高（大端） */
static int check_png_dims(const char *path, uint32_t want_w, uint32_t want_h)
{
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    unsigned char hdr[33];
    if (fread(hdr, 1, sizeof(hdr), f) != sizeof(hdr)) { fclose(f); return -2; }
    fclose(f);
    static const unsigned char magic[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    if (memcmp(hdr, magic, 8) != 0) return -3;
    if (memcmp(hdr + 12, "IHDR", 4) != 0) return -4;
    uint32_t w = ((uint32_t)hdr[16] << 24) | ((uint32_t)hdr[17] << 16) |
                 ((uint32_t)hdr[18] << 8) | (uint32_t)hdr[19];
    uint32_t h = ((uint32_t)hdr[20] << 24) | ((uint32_t)hdr[21] << 16) |
                 ((uint32_t)hdr[22] << 8) | (uint32_t)hdr[23];
    if (w != want_w || h != want_h) { printf("  (got %ux%u want %ux%u)\n", w, h, want_w, want_h); return -5; }
    return 0;
}

int main(void)
{
    struct ansilove_ctx ctx;
    struct ansilove_options opts;

    /* 1. init/error/clean 生命周期：init 清零并把 buffer 置 MAP_FAILED、bits 默认 8 */
    ansilove_init(&ctx, &opts);
    CHECK("ansilove_init sets buffer = MAP_FAILED", ctx.buffer == MAP_FAILED);
    CHECK("ansilove_init zeroes error", ctx.error == 0);
    CHECK("ansilove_init defaults bits to 8", opts.bits == 8);
    CHECK("ansilove_error returns NULL when no error", ansilove_error(&ctx) == NULL);

    /* 2. 解析 + 渲染 + PNG 输出（默认 CP437 80x25 → 8x16 像素字形） */
    if (write_tmp("in.ans", ansi_hello, strlen(ansi_hello)) != 0) {
        printf("FAIL: write in.ans\n"); return 1;
    }
    int rc = ansilove_loadfile(&ctx, "in.ans");
    CHECK("ansilove_loadfile parses ANSI text", rc == 0);
    rc = ansilove_ansi(&ctx, &opts);
    CHECK("ansilove_ansi renders to canvas", rc == 0);
    rc = ansilove_savefile(&ctx, "out.png");
    CHECK("ansilove_savefile writes PNG", rc == 0);

    /* 画布尺寸：2 行文本 × 默认 80 列；CP437 字形 9x16（80x25 系列 loader 用 8 宽 16 高，
     * icedraw 除外）。上游 ansi.c：columns=80 → width=640, 行数 2 → height=32。 */
    CHECK("PNG canvas 640x32 (80 cols x 2 rows, CP437 8x16)",
          check_png_dims("out.png", 640, 32) == 0);

    /* 3. 字体/画布尺寸参数化：CP437_80x50 字形 8x8 → 同样 2 行高度 16 */
    ansilove_clean(&ctx);
    ansilove_init(&ctx, &opts);
    opts.font = ANSILOVE_FONT_CP437_80x50;
    rc = ansilove_loadfile(&ctx, "in.ans");
    CHECK("loadfile for 80x50 font run", rc == 0);
    rc = ansilove_ansi(&ctx, &opts);
    CHECK("ansi render with CP437_80x50 font", rc == 0);
    rc = ansilove_savefile(&ctx, "out50.png");
    CHECK("savefile with 80x50 font", rc == 0);
    CHECK("PNG canvas 640x16 (80x50 glyph 8x8, 2 rows)",
          check_png_dims("out50.png", 640, 16) == 0);

    /* 4. 调色板：truecolor 模式走 24-bit 路径（Workbench/16 色 VGA 默认路径已覆盖） */
    ansilove_clean(&ctx);
    ansilove_init(&ctx, &opts);
    opts.truecolor = true;
    rc = ansilove_loadfile(&ctx, "in.ans");
    CHECK("loadfile for truecolor run", rc == 0);
    rc = ansilove_ansi(&ctx, &opts);
    CHECK("ansi render truecolor palette path", rc == 0);
    rc = ansilove_savefile(&ctx, "out_tc.png");
    CHECK("savefile truecolor PNG", rc == 0);
    CHECK("truecolor PNG same canvas dims", check_png_dims("out_tc.png", 640, 32) == 0);

    /* 5. 非法/未知控制序列：loader 必须容错（不崩溃），返回 0 或格式错误码 */
    ansilove_clean(&ctx);
    ansilove_init(&ctx, &opts);
    if (write_tmp("bad.ans", ansi_invalid, strlen(ansi_invalid)) != 0) {
        printf("FAIL: write bad.ans\n"); return 1;
    }
    rc = ansilove_loadfile(&ctx, "bad.ans");
    CHECK("loadfile accepts malformed input", rc == 0);
    rc = ansilove_ansi(&ctx, &opts);
    CHECK("ansi tolerates invalid control sequences (rc sane)", rc == 0 || rc == ANSILOVE_FORMAT_ERROR);

    /* 6. 缺文件错误路径：loadfile 返回 -1，错误码在 ctx->error */
    ansilove_clean(&ctx);
    ansilove_init(&ctx, &opts);
    rc = ansilove_loadfile(&ctx, "no_such_file.ans");
    CHECK("missing file → loadfile returns -1", rc == -1);
    CHECK("missing file → ctx.error = ANSILOVE_FILE_READ_ERROR",
          ctx.error == ANSILOVE_FILE_READ_ERROR);
    CHECK("ansilove_error returns read error message",
          strstr(ansilove_error(&ctx), "read") != NULL ||
          strstr(ansilove_error(&ctx), "Read") != NULL);

    /* 7. xbin loader（7 个 loader 之一）：XBIN 头 11 字节 = "XBIN\x1a"(5)
     * + width(2LE) + height(2LE) + fontsize + flags；flags=0 走内置 VGA 调色板。
     * 80x1 字号 16 → 画布 8*80 x 16*1。 */
    ansilove_clean(&ctx);
    ansilove_init(&ctx, &opts);
    unsigned char xbin[] = {'X','B','I','N', 0x1a, 80,0, 1,0, 16, 0, 'A', 0x07};
    if (write_tmp("in.xbin", (const char *)xbin, sizeof(xbin)) != 0) {
        printf("FAIL: write in.xbin\n"); return 1;
    }
    rc = ansilove_loadfile(&ctx, "in.xbin");
    CHECK("loadfile parses XBIN", rc == 0);
    rc = ansilove_xbin(&ctx, &opts);
    CHECK("xbin loader renders", rc == 0);
    rc = ansilove_savefile(&ctx, "out_xbin.png");
    CHECK("xbin PNG output", rc == 0);
    CHECK("xbin canvas 640x16 (80x1, font 8x16)", check_png_dims("out_xbin.png", 640, 16) == 0);

    ansilove_clean(&ctx);
    printf(failures ? "\n%d CHECK(S) FAILED\n" : "\nALL CHECKS PASSED\n", failures);
    return failures ? 1 : 0;
}
