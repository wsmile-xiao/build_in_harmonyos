/* test_libcupsfilters.c - libcupsfilters 2.2.1 上游测试纳入
 *
 * 纳入上游 TESTS 列表中最简单的两个测试：
 *   1. testdither.c（186 行，上游 TESTS 成员）
 *      核心 API: cfLutNew / cfDitherNew / cfDitherLine / cfDitherDelete / cfLutDelete
 *      使用 cfCUPSLogFunc（与上游 testdither.c 完全一致）
 *   2. image-colorspace.c 的 colorspace 转换（image 模块）
 *      核心 API: cfImageRGBToWhite / cfImageRGBToBlack
 *
 * 上游 colorspace 公式（image-colorspace.c）：
 *   cfImageRGBToWhite: out = (31*R + 61*G + 8*B) / 100      （亮度，黑→0，白→255）
 *   cfImageRGBToBlack: out = 255 - (31*R + 61*G + 8*B)/100  （黑通道 = 255 - 亮度）
 *
 * 评审 P2 修复：
 *   1. use-after-free: cfLutDelete(lut) 后 lut = NULL
 *   2. 断言语义相悖: 纯白像素 {255,255,255} 的黑通道应为 0（非"非全零"）
 *      纯黑像素 {0,0,0} 的白通道应为 0
 *
 * 参考：上游 cupsfilters/testdither.c、cupsfilters/image-colorspace.c
 */
#include <cupsfilters/image.h>
#include <cupsfilters/driver.h>
#include <cupsfilters/filter.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* 与上游 testdither.c 完全一致：cfCUPSLogFunc 来自 filter.h，链接 libcupsfilters */
cf_logfunc_t logfunc = cfCUPSLogFunc;
void         *ld = NULL;

int main(void) {
  int failures = 0;

  /* 评审 P2 修复：所有指针提前声明并初始化为 NULL，
   * 确保任意 goto done 错误路径下 done: 清理段读取的是已初始化的 NULL，
   * 而非未初始化的垃圾值（避免 OOM 路径的未定义行为）。 */
  cf_lut_t *lut = NULL;
  cf_dither_t *dither = NULL;

  /* ============================================================
   * 纳入上游 testdither.c 核心逻辑
   * 上游 testdither.c: lut = cfLutNew(nlutvals, lutvals, logfunc, ld)
   *                   dither = cfDitherNew(512)
   *                   cfDitherLine(dither, lut, line, 1, pixels)
   * ============================================================ */

  /* === 测试 1: cfLutNew 创建查找表（上游 testdither.c 默认 2-entry LUT）=== */
  float lutvals[2] = {0.0, 1.0};
  lut = cfLutNew(2, lutvals, logfunc, ld);
  if (lut == NULL) {
    fprintf(stderr, "FAIL: cfLutNew returned NULL\n");
    failures++;
    goto done;
  }
  printf("OK: cfLutNew(2 entries)\n");

  /* === 测试 2: cfDitherNew 创建 dither 状态（上游 testdither.c: cfDitherNew(512)）=== */
  dither = cfDitherNew(512);
  if (dither == NULL) {
    fprintf(stderr, "FAIL: cfDitherNew returned NULL\n");
    failures++;
    goto done;
  }
  printf("OK: cfDitherNew(512)\n");

  /* === 测试 3: cfDitherLine 多行抖动（上游 testdither.c 核心 512 行循环）===
   *
   * 上游 testdither.c 循环：for (y=0; y<512; y++) { line[x] = 4095*((y/32)*16+x/32)/255;
   * cfDitherLine(dither, lut, line, 1, pixels); output = 255 - pixvals[*pixptr]; }
   *
   * cfDitherLine 输出的 pixels 是 dither 索引（0 或 1），不是灰度值。
   * 用上游完整公式生成 512 行渐变灰度，dither 后转换为灰度输出，
   * 验证最终 PPM 灰度非全零（模拟上游 testdither > filename.ppm）。
   */
  short line[512];
  unsigned char pixels[512];
  int pixvals[2] = {0, 255};  /* 上游 testdither.c 默认 pixvals */
  int total_nonzero = 0;

  for (int y = 0; y < 512; y++) {
    /* 上游 testdither.c: line[x] = 4095 * ((y/32)*16 + x/32) / 255 */
    for (int x = 0; x < 512; x++)
      line[x] = 4095 * ((y / 32) * 16 + x / 32) / 255;

    cfDitherLine(dither, lut, line, 1, pixels);

    /* 上游 testdither.c: output = 255 - pixvals[*pixptr]
     * 统计全部 512 行的非零灰度输出，验证 dither 产出非空 PPM */
    for (int x = 0; x < 512; x++) {
      int output = 255 - pixvals[pixels[x]];
      if (output > 0) total_nonzero++;
    }
  }

  /* 512×512 = 262144 像素，渐变灰度 dither 必产出大量非零像素 */
  if (total_nonzero == 0) {
    fprintf(stderr, "FAIL: cfDitherLine 512-row dither produced all-zero output\n");
    failures++;
  } else {
    printf("OK: cfDitherLine(512 rows, %d non-zero pixels)\n", total_nonzero);
  }

  /* === 测试 4: cfDitherDelete + cfLutDelete 释放（上游 testdither.c 末尾）=== */
  /* 评审 P2 修复 1: use-after-free，删除后立即置 NULL */
  cfDitherDelete(dither);
  dither = NULL;
  printf("OK: cfDitherDelete\n");

  cfLutDelete(lut);
  lut = NULL;
  printf("OK: cfLutDelete\n");

  /* ============================================================
   * 纳入上游 image-colorspace.c colorspace 转换测试
   * ============================================================ */

  /* === 测试 5: cfImageRGBToWhite 纯白像素（亮度 = 255）=== */
  /* 评审 P2 修复 2: 纯白像素 {255,255,255} 的白通道 = (31*255+61*255+8*255)/100 = 255 */
  cf_ib_t white_in[3] = {255, 255, 255};
  cf_ib_t white_out[1] = {0};
  cfImageRGBToWhite(white_in, white_out, 1);
  if (white_out[0] != 255) {
    fprintf(stderr, "FAIL: cfImageRGBToWhite({255,255,255}) = %d, expected 255\n", white_out[0]);
    failures++;
  } else {
    printf("OK: cfImageRGBToWhite({255,255,255}) = 255\n");
  }

  /* === 测试 6: cfImageRGBToWhite 纯黑像素（亮度 = 0）=== */
  /* 纯黑像素 {0,0,0} 的白通道 = (0+0+0)/100 = 0 */
  cf_ib_t black_in[3] = {0, 0, 0};
  cf_ib_t black_out[1] = {0};
  cfImageRGBToWhite(black_in, black_out, 1);
  if (black_out[0] != 0) {
    fprintf(stderr, "FAIL: cfImageRGBToWhite({0,0,0}) = %d, expected 0\n", black_out[0]);
    failures++;
  } else {
    printf("OK: cfImageRGBToWhite({0,0,0}) = 0\n");
  }

  /* === 测试 7: cfImageRGBToBlack 纯白像素（黑通道 = 255 - 255 = 0）=== */
  /* 评审 P2 修复 2: 纯白像素的黑通道应为 0，非"非全零" */
  cf_ib_t black_from_white[1] = {0};
  cfImageRGBToBlack(white_in, black_from_white, 1);
  if (black_from_white[0] != 0) {
    fprintf(stderr, "FAIL: cfImageRGBToBlack({255,255,255}) = %d, expected 0\n", black_from_white[0]);
    failures++;
  } else {
    printf("OK: cfImageRGBToBlack({255,255,255}) = 0\n");
  }

  /* === 测试 8: cfImageRGBToBlack 纯黑像素（黑通道 = 255 - 0 = 255）=== */
  cf_ib_t black_from_black[1] = {0};
  cfImageRGBToBlack(black_in, black_from_black, 1);
  if (black_from_black[0] != 255) {
    fprintf(stderr, "FAIL: cfImageRGBToBlack({0,0,0}) = %d, expected 255\n", black_from_black[0]);
    failures++;
  } else {
    printf("OK: cfImageRGBToBlack({0,0,0}) = 255\n");
  }

done:
  /* 安全清理：已删除的指针不重复释放 */
  if (dither != NULL) cfDitherDelete(dither);
  if (lut != NULL) cfLutDelete(lut);

  if (failures > 0) {
    fprintf(stderr, "\nFAIL: %d test(s) failed\n", failures);
    return 1;
  }
  printf("\nAll tests PASS\n");
  return 0;
}
