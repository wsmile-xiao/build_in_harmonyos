/* test_package/test.c — libotf/0.9.16 消费者单元测试（链接 Conan 包内安装产物）
 *
 * 编译（消费者视角，仅使用包内头文件/库；otf.h 自身会再包含 freetype 头）：
 *   $CC test.c -o test_consumer -I<pkg>/include -I<freetype>/include \
 *       -L<pkg>/lib -L<freetype>/lib -lotf -lfreetype
 * 运行：
 *   LD_LIBRARY_PATH=<pkg>/lib:<freetype>/lib ./test_consumer <font-file>
 *
 * 断言分组（同一用例内的多项检查，不拆分计数）：
 *   A 标签工具：OTF_tag / OTF_tag_name 往返
 *   B 打开与表检查：OTF_open / OTF_check_table / OTF_get_scripts / OTF_get_features
 *   C cmap 驱动：OTF_drive_cmap 结果与 freetype FT_Get_Char_Index 逐字符比对，
 *     并以 OTF_get_unicode 做 glyph-id → Unicode 反向往返校验
 *     （同时验证 otf.h 暴露的 freetype 头文件与传递依赖链接：transitive_headers/libs）
 *   D FT_Face 接入：OTF_open_ft_face（消费者自持 FT_Face）
 *   E 错误路径：OTF_open 不存在的文件返回 NULL 且 OTF_error 置位
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <otf.h>  /* 同时引入 <ft2build.h> 与 FT_FREETYPE_H（上游公开头文件行为） */

static int checks = 0;
static int failures = 0;

#define CHECK(cond, ...)                                                      \
  do {                                                                        \
    checks++;                                                                 \
    if (cond) {                                                               \
      printf("ok: ");                                                         \
    } else {                                                                  \
      printf("FAIL: ");                                                       \
      failures++;                                                             \
    }                                                                         \
    printf(__VA_ARGS__);                                                      \
    printf("\n");                                                             \
  } while (0)

/* ── A. 标签工具（不依赖字体文件）── */
static void test_tags(void)
{
  OTF_Tag gsub = OTF_tag("GSUB");
  OTF_Tag gpos = OTF_tag("GPOS");
  char name[16];

  memset(name, 0, sizeof(name));
  OTF_tag_name(gsub, name);
  CHECK(strcmp(name, "GSUB") == 0, "A1 OTF_tag/OTF_tag_name 往返 GSUB -> %s", name);

  memset(name, 0, sizeof(name));
  OTF_tag_name(gpos, name);
  CHECK(strcmp(name, "GPOS") == 0, "A2 OTF_tag/OTF_tag_name 往返 GPOS -> %s", name);

  CHECK(gsub != gpos, "A3 不同标签得到不同 OTF_Tag");
}

/* OTF_check_table() 的返回约定与直觉相反：表存在返回 0、不存在返回 -1
   （src/otfopen.c: `return (get_table_info (otf, name) ? 0 : -1);`）。 */
static int table_present(OTF *otf, const char *name)
{
  return OTF_check_table(otf, name) == 0;
}

/* ── B/C/D/E. 需要真实字体文件 ── */
static void test_font(const char *path)
{
  OTF *otf, *otf2, *bad;
  OTF_GlyphString gs;
  FT_Library ftlib = NULL;
  FT_Face face = NULL;
  static const char ascii[] = "ABCXYZabcxyz0189";
  static const unsigned int cjk[] =
    {0x4E2D, 0x6587, 0x5B57, 0x4F53, 0x6D4B, 0x8BD5};
  const int n_ascii = (int) sizeof(ascii) - 1;
  const int n_cjk = (int) (sizeof(cjk) / sizeof(cjk[0]));
  int has_gsub, has_gpos, covered = 0, mismatched = 0, total, i, rc;

  /* ── B. 打开字体 + OTF 表检查 ── */
  otf = OTF_open(path);
  CHECK(otf != NULL, "B1 OTF_open(%s) 返回非空", path);
  if (! otf) {
    printf("info: OTF_error=%d\n", OTF_error);
    return;
  }

  CHECK(table_present(otf, "cmap"), "B2 cmap 表存在（OTF_check_table 返回 0）");
  has_gsub = table_present(otf, "GSUB");
  has_gpos = table_present(otf, "GPOS");
  printf("info: GDEF=%d GPOS=%d GSUB=%d\n",
         table_present(otf, "GDEF"), has_gpos, has_gsub);
  CHECK(has_gsub || has_gpos, "B3 字体含 OTF 布局表（GSUB=%d GPOS=%d）", has_gsub, has_gpos);
  if (has_gsub || has_gpos) {
    const int gsubp = has_gsub ? 1 : 0;
    const int rs = OTF_get_scripts(otf, gsubp);
    const int rf = OTF_get_features(otf, gsubp);
    /* 约定：0 = 成功装载 ScriptList/FeatureList，-1 = 失败并置 OTF_error */
    CHECK(rs == 0, "B4 OTF_get_scripts(gsubp=%d) 成功（返回 %d）", gsubp, rs);
    CHECK(rf == 0, "B5 OTF_get_features(gsubp=%d) 成功（返回 %d）", gsubp, rf);
  }

  /* ── C. cmap 驱动 vs freetype 逐字符比对 ── */
  if (FT_Init_FreeType(&ftlib) != 0) {
    CHECK(0, "C0 FT_Init_FreeType 失败");
    OTF_close(otf);
    return;
  }
  if (FT_New_Face(ftlib, path, 0, &face) != 0) {
    CHECK(0, "C0 FT_New_Face(%s) 失败", path);
    FT_Done_FreeType(ftlib);
    OTF_close(otf);
    return;
  }

  total = n_ascii + n_cjk;
  memset(&gs, 0, sizeof(gs));
  gs.size = total;
  gs.used = total;
  gs.glyphs = (OTF_Glyph *) calloc((size_t) total, sizeof(OTF_Glyph));
  if (! gs.glyphs) {
    CHECK(0, "C0 glyphs 分配失败");
    FT_Done_Face(face);
    FT_Done_FreeType(ftlib);
    OTF_close(otf);
    return;
  }
  for (i = 0; i < n_ascii; i++)
    gs.glyphs[i].c = (unsigned char) ascii[i];
  for (i = 0; i < n_cjk; i++)
    gs.glyphs[n_ascii + i].c = (int) cjk[i];

  rc = OTF_drive_cmap(otf, &gs);
  CHECK(rc >= 0, "C1 OTF_drive_cmap 返回 %d", rc);

  /* ASCII 段：任何字体都应覆盖，且 libotf 的映射须与 freetype 完全一致 */
  for (i = 0; i < n_ascii; i++) {
    const FT_UInt gid = FT_Get_Char_Index(face, (FT_ULong) gs.glyphs[i].c);
    if (gid == 0 || (unsigned int) gs.glyphs[i].glyph_id != (unsigned int) gid)
      mismatched++;
  }
  CHECK(mismatched == 0, "C2 ASCII 段 %d 字符与 freetype FT_Get_Char_Index 全部一致",
        n_ascii);

  /* CJK 段：字体覆盖到的字符须与 freetype 一致 */
  mismatched = 0;
  for (i = n_ascii; i < total; i++) {
    const FT_UInt gid = FT_Get_Char_Index(face, (FT_ULong) gs.glyphs[i].c);
    if (gid == 0)
      continue;
    covered++;
    if ((unsigned int) gs.glyphs[i].glyph_id != (unsigned int) gid)
      mismatched++;
  }
  CHECK(mismatched == 0,
        "C3 CJK 段 %d/%d 字符被字体覆盖，映射与 freetype 一致（不一致 %d 处）",
        covered, n_cjk, mismatched);
  CHECK(covered > 0, "C4 所选字体覆盖 CJK 测试字符（%d/%d），CJK cmap 路径已被覆盖",
        covered, n_cjk);

  /* C5 反向映射：glyph-id → Unicode 往返一致 */
  mismatched = 0;
  for (i = 0; i < total; i++) {
    if (OTF_get_unicode(otf, gs.glyphs[i].glyph_id) != (int) gs.glyphs[i].c)
      mismatched++;
  }
  CHECK(mismatched == 0, "C5 OTF_get_unicode 反查 %d 个字符全部一致（不一致 %d 处）",
        total, mismatched);

  /* ── D. 消费者自持 FT_Face 的接入路径 ── */
  otf2 = OTF_open_ft_face(face);
  CHECK(otf2 != NULL, "D1 OTF_open_ft_face(消费者 FT_Face) 返回非空");
  if (otf2) {
    CHECK(table_present(otf2, "cmap"),
          "D2 FT_Face 路径 cmap 表存在（OTF_check_table 返回 0）");
    OTF_close(otf2);
  }

  /* ── E. 错误路径 ── */
  OTF_error = 0;
  bad = OTF_open("/nonexistent/libotf-definitely-missing.otf");
  CHECK(bad == NULL, "E1 OTF_open(不存在路径) 返回 NULL");
  CHECK(OTF_error != 0, "E2 OTF_error 已置位（= %d）", OTF_error);

  free(gs.glyphs);
  FT_Done_Face(face);
  FT_Done_FreeType(ftlib);
  OTF_close(otf);
}

int main(int argc, char **argv)
{
  if (argc < 2) {
    fprintf(stderr, "usage: %s <font-file>\n", argv[0]);
    return 2;
  }
  printf("== libotf 消费者单元测试（font=%s）==\n", argv[1]);
  test_tags();
  test_font(argv[1]);
  printf("== checks=%d failures=%d ==\n", checks, failures);
  if (failures) {
    printf("TEST FAILED\n");
    return 1;
  }
  printf("ALL TESTS PASSED\n");
  return 0;
}
