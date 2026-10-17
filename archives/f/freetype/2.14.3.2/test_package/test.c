/*
 * test_package for freetype 2.14.3 — R34 实质测试（非 dlopen/print 空壳）。
 *
 * 真实调用 freetype API 链路：
 *   FT_Init_FreeType → FT_Library_Version → FT_New_Face
 *   → FT_Get_Char_Index → FT_Load_Glyph → FT_Done_Face → FT_Done_FreeType
 *
 * FT_New_Face 需要一个字体文件：优先取环境变量 FREETYPE_TEST_FONT，
 * 否则在 HarmonyOS 系统字体目录 /system/fonts 内取一个存在的小字体
 * （该目录为本平台 OS 自带，CI 与真机同一 OHOS 镜像）。全部不可得才失败。
 */
#include <ft2build.h>
#include FT_FREETYPE_H
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

#ifndef TARGET_SO
#define TARGET_SO "libfreetype.so"
#endif

static const char *const kFontCandidates[] = {
    "/system/fonts/FTAeroSans-Regular.ttf",
    "/system/fonts/FTChariSans.ttf",
    "/system/fonts/FTGreisSans.ttf",
    "/system/fonts/DejaVuMathTeXGyre.ttf",
    "/system/fonts/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    NULL,
};

int main(void) {
    FT_Library library;
    FT_Face    face = NULL;
    FT_Error   error;
    FT_Int     major, minor, patch;
    int        i;

    error = FT_Init_FreeType(&library);
    if (error) {
        fprintf(stderr, "FAIL: FT_Init_FreeType error=%d\n", error);
        return 1;
    }

    FT_Library_Version(library, &major, &minor, &patch);
    printf("freetype %s: FT_Init_FreeType ok, library version=%d.%d.%d\n",
           TARGET_SO, major, minor, patch);

    /* 打开一个真实字体并做字形加载，验证核心渲染路径 */
    const char *font = getenv("FREETYPE_TEST_FONT");
    if (!font || !font[0]) {
        for (i = 0; kFontCandidates[i]; i++) {
            if (access(kFontCandidates[i], R_OK) == 0) {
                font = kFontCandidates[i];
                break;
            }
        }
    }
    if (!font) {
        fprintf(stderr, "FAIL: no font found (set FREETYPE_TEST_FONT)\n");
        FT_Done_FreeType(library);
        return 1;
    }

    error = FT_New_Face(library, font, 0, &face);
    if (error) {
        fprintf(stderr, "FAIL: FT_New_Face(%s) error=%d\n", font, error);
        FT_Done_FreeType(library);
        return 1;
    }
    printf("freetype %s: FT_New_Face(%s) ok, family='%s', num_glyphs=%ld\n",
           TARGET_SO, font, face->family_name ? face->family_name : "(null)",
           face->num_glyphs);

    /* 取 'A' (0x41) 的字形并加载，真实触发 cmap + glyf 解析 */
    {
        FT_UInt   gid = FT_Get_Char_Index(face, 65);
        FT_Error  code;
        if (gid == 0) {
            fprintf(stderr, "FAIL: FT_Get_Char_Index('A') returned 0\n");
            FT_Done_Face(face);
            FT_Done_FreeType(library);
            return 1;
        }
        code = FT_Load_Glyph(face, gid, FT_LOAD_DEFAULT);
        if (code) {
            fprintf(stderr, "FAIL: FT_Load_Glyph(gid=%u) error=%d\n", gid, code);
            FT_Done_Face(face);
            FT_Done_FreeType(library);
            return 1;
        }
        printf("freetype %s: FT_Get_Char_Index/FT_Load_Glyph('A') ok, gid=%u, w=%d h=%d\n",
               TARGET_SO, gid,
               (int)face->glyph->bitmap.width, (int)face->glyph->bitmap.rows);
    }

    FT_Done_Face(face);
    FT_Done_FreeType(library);
    printf("freetype %s: FT API test OK\n", TARGET_SO);
    return 0;
}
