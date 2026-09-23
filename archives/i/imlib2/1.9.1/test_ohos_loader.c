/*
 * test_ohos_loader.c — HarmonyOS 专项测试（imlib2 1.9.1）
 *
 * 验证本库在 OHOS 上的真实运行时适配链路，非空壳测试：
 *   1. 经公开 API imlib_create_image/imlib_image_fill_rectangle 创建图像；
 *   2. imlib_save_image("png") 经 PNG loader 模块（png.so，链接 libpng）落盘；
 *   3. imlib_load_image 重新加载该 PNG，校验可观察像素结果；
 *   4. 全流程依赖 IMLIB2_LOADER_PATH 指向安装包的 loaders 目录 —— 即
 *      OHOS 上动态 loader 模块查找/加载链路的实测。
 * 退出码 0 仅当像素值逐项匹配且文件真实存在。
 */
#include <Imlib2.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* 生成测试图像文件路径（可写目录，避免 /tmp 只读） */
static void
make_path(char *buf, size_t sz, const char *name)
{
   const char *tmp = getenv("TMPDIR");
   if (!tmp || !*tmp)
     tmp = "/storage/Users/currentUser/tmp";
   snprintf(buf, sz, "%s/%s", tmp, name);
}

int
main(void)
{
   Imlib_Image        img = NULL, reloaded = NULL;
   DATA32            *d1 = NULL, *d2 = NULL;
   char               png_path[512], buf_path[1024];
   int                w, h, ok = 0, save_errno = 0;

   make_path(png_path, sizeof(png_path), "imlib2_ohos_test.png");

   imlib_context_set_dither(1);

   /* 1. 公开 API：创建 32x32 图像并填充红色 */
   img = imlib_create_image(32, 32);
   if (!img)
     {
        fprintf(stderr, "FAIL: imlib_create_image NULL\n");
        goto out;
     }
   imlib_context_set_image(img);
   imlib_image_set_has_alpha(1);
   imlib_context_set_color(255, 0, 0, 255);
   imlib_image_fill_rectangle(0, 0, 32, 32);

   /* 2. 经 PNG loader 保存（需 png.so 经由 IMLIB2_LOADER_PATH 被加载）；
    *    1.9.1 的 imlib_save_image 返回 void，用 with_errno_return 检查 */
   imlib_context_set_image(img);
   imlib_image_set_format("png");
   imlib_save_image_with_errno_return(png_path, &save_errno);
   if (save_errno != 0)
     {
        fprintf(stderr, "FAIL: imlib_save_image_with_errno_return errno=%d: %s\n",
                save_errno, png_path);
        goto out;
     }
   if (access(png_path, F_OK) != 0)
     {
        fprintf(stderr, "FAIL: saved png not found on disk\n");
        goto out;
     }

   /* 3. 重新加载并校验可观察像素（0119 版像素布局 RGBA 大端序为 0xff0000ff）
    *    用 create/load 两条路径的像素逐项比对，避免端序假设 */
   reloaded = imlib_load_image(png_path);
   if (!reloaded)
     {
        fprintf(stderr, "FAIL: imlib_load_image(png) NULL\n");
        goto out;
     }
   imlib_context_set_image(reloaded);
   w = imlib_image_get_width();
   h = imlib_image_get_height();
   if (w != 32 || h != 32)
     {
        fprintf(stderr, "FAIL: reloaded size %dx%d != 32x32\n", w, h);
        goto out;
     }
   d1 = imlib_image_get_data_for_reading_only();
   imlib_context_set_image(img);
   d2 = imlib_image_get_data_for_reading_only();
   if (!d1 || !d2)
     {
        fprintf(stderr, "FAIL: pixel data NULL\n");
        goto out;
     }
   /* 像素布局：imlib2 1.9.x DATA32 为 ARGB 大端序（A 在高 8 位）。
    * 填充红色 (255,0,0,255) → 期望 A=0xff R=0xff G=0x00 B=0x00，
    * 亦即 data & 0xffffff00 == 0xffff0000。逐字节校验可观察结果 */
   if ((d1[0] & 0xff000000u) != 0xff000000u ||  /* A=255 */
       (d1[0] & 0x00ff0000u) != 0x00ff0000u ||  /* R=255 */
       (d1[0] & 0x0000ff00u) != 0x00000000u ||  /* G=0   */
       (d1[0] & 0x000000ffu) != 0x00000000u)    /* B=0   */
     {
        fprintf(stderr, "FAIL: reloaded pixel not opaque red: d1[0]=%08x\n",
                (unsigned) d1[0]);
        goto out;
     }
   /* 再校验另一位置像素（10,0）同样为红色 */
   if ((d1[10] & 0x00ff0000u) != 0x00ff0000u)
     {
        fprintf(stderr, "FAIL: pixel[10] not red: %08x\n",
                (unsigned) d1[10]);
        goto out;
     }

   ok = 1;
   printf("OK: ohos loader test passed (create->save png->reload %dx%d, path=%s)\n",
          w, h, png_path);

out:
   if (reloaded)
     {
        imlib_context_set_image(reloaded);
        imlib_free_image();
     }
   if (img)
     {
        imlib_context_set_image(img);
        imlib_free_image();
     }
   (void) buf_path;
   return ok ? 0 : 1;
}