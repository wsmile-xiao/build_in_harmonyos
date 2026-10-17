/* freetype 消费者探针（HarmonyOS PC / aarch64）
 *
 * 与旧版 dlopen 空壳探针不同，本探针与 libfreetype.so 真实链接，并对一个
 * 程序化生成的微型 TrueType 字体（probe_font.h，fontTools 生成、无第三方
 * 版权数据）执行完整渲染链路验证：
 *   库初始化 → 版本核对 → 内存加载字体 → charmap 选择 → 像素尺寸设定
 *   → 码位映射 → 字形加载 → 光栅化出墨 → 度量 → 上游 issue-1063 等价循环
 */
#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_GLYPH_H
#include FT_BITMAP_H
#include FT_OUTLINE_H
#include FT_BBOX_H
#include <stdio.h>

#include "probe_font.h"

static int checks = 0, fails = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        checks++;                                               \
        if (cond) {                                             \
            printf("[OK]   %s\n", msg);                         \
        } else {                                                \
            fails++;                                            \
            printf("[FAIL] %s\n", msg);                         \
        }                                                       \
    } while (0)

int main(void)
{
    FT_Library  lib  = NULL;
    FT_Face     face = NULL;
    FT_Error    err;

    /* 1. 库初始化 */
    err = FT_Init_FreeType(&lib);
    CHECK(err == 0 && lib != NULL, "FT_Init_FreeType 初始化");

    /* 2. 运行期版本 == 2.14.3，且与编译期头文件宏一致 */
    FT_Int maj, min, pat;
    FT_Library_Version(lib, &maj, &min, &pat);
    CHECK(maj == 2 && min == 14 && pat == 3, "FT_Library_Version == 2.14.3");
    CHECK(maj == FREETYPE_MAJOR && min == FREETYPE_MINOR && pat == FREETYPE_PATCH,
          "运行期版本与编译期宏一致");

    /* 3. 从内存加载嵌入字体 */
    err = FT_New_Memory_Face(lib, probe_font, probe_font_len, 0, &face);
    CHECK(err == 0 && face != NULL, "FT_New_Memory_Face(嵌入 TTF)");
    if (!face) {
        printf("face 加载失败，终止\n");
        return 1;
    }
    CHECK(face->num_glyphs >= 3, "num_glyphs >= 3 (.notdef/A/B)");
    CHECK(face->face_flags & FT_FACE_FLAG_SCALABLE, "FT_FACE_FLAG_SCALABLE");

    /* 4. charmap + 像素尺寸 */
    CHECK(FT_Select_Charmap(face, FT_ENCODING_UNICODE) == 0, "FT_Select_Charmap(UNICODE)");
    CHECK(FT_Set_Pixel_Sizes(face, 16, 16) == 0, "FT_Set_Pixel_Sizes(16,16)");

    /* 5. cmap 码位映射（含未映射字符负向） */
    FT_UInt gid_a = FT_Get_Char_Index(face, 'A');
    CHECK(gid_a == 1, "FT_Get_Char_Index('A') == 1");
    CHECK(FT_Get_Char_Index(face, 'Q') == 0, "未映射字符 'Q' 返回 0");

    /* 6. 字形加载 + 光栅化 */
    CHECK(FT_Load_Glyph(face, gid_a, FT_LOAD_DEFAULT) == 0, "FT_Load_Glyph('A')");
    err = FT_Render_Glyph(face->glyph, FT_RENDER_MODE_NORMAL);
    CHECK(err == 0, "FT_Render_Glyph(NORMAL)");

    FT_Bitmap  *bmp = &face->glyph->bitmap;
    CHECK(bmp->width > 0 && bmp->rows > 0 && bmp->pitch != 0 && bmp->buffer != NULL,
          "bitmap 尺寸/缓冲有效");
    int  pitch = bmp->pitch >= 0 ? bmp->pitch : -bmp->pitch;
    int  ink   = 0;
    for (unsigned int y = 0; y < bmp->rows; y++)
        for (unsigned int x = 0; x < bmp->width; x++)
            if (bmp->buffer[y * pitch + x])
                ink++;
    CHECK(ink > 50, "渲染出墨（非零像素 > 50）");
    printf("      bitmap %ux%u pitch=%d ink=%d\n", bmp->width, bmp->rows, bmp->pitch, ink);

    /* 7. 度量 */
    CHECK(face->glyph->advance.x > 0, "advance.x > 0");

    /* 8. 等价覆盖上游 issue-1063 回归用例：码位 59..170 全量加载无错误
     *    （上游用例需 tests/data 外部字体，本探针用嵌入字体做同语义覆盖） */
    int bad = 0, mapped = 0;
    for (FT_ULong i = 59; i < 171; i++) {
        FT_UInt gid = FT_Get_Char_Index(face, i);
        if (!gid)
            continue;
        mapped++;
        if (FT_Load_Glyph(face, gid, FT_LOAD_DEFAULT))
            bad++;
    }
    CHECK(bad == 0 && mapped == 2, "issue-1063 等价码位循环 59..170 无错误（映射 2 字形）");

    /* 9. 清理 */
    CHECK(FT_Done_Face(face) == 0, "FT_Done_Face");
    CHECK(FT_Done_FreeType(lib) == 0, "FT_Done_FreeType");

    printf("freetype probe: %d checks, %d failed\n", checks, fails);
    return fails ? 1 : 0;
}
