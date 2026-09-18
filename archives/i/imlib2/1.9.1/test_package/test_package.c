/*
 * test_package.c — imlib2 consumer smoke test (R34: 必须实质调用被测包 API)
 *
 * 通过公开头文件 Imlib2.h 调用公开 API：创建图像、设置格式、绘制像素、
 * 缩放并校验可观察结果，验证编译、链接与运行链路。
 */
#include <Imlib2.h>
#include <stdio.h>
#include <string.h>

int
main(void)
{
   Imlib_Image        img, scaled;
   DATA32            *data;
   int                w, h;
   int                ret = 1;

   imlib_context_set_dither(1);

   /* 公开 API：创建 64x64 ARGB 图像 */
   img = imlib_create_image(64, 64);
   if (!img)
     {
        fprintf(stderr, "FAIL: imlib_create_image returned NULL\n");
        return 1;
     }

   imlib_context_set_image(img);
   imlib_image_set_has_alpha(1);
   imlib_context_set_color(255, 0, 0, 255);
   imlib_image_fill_rectangle(0, 0, 64, 64);

   w = imlib_image_get_width();
   h = imlib_image_get_height();
   if (w != 64 || h != 64)
     {
        fprintf(stderr, "FAIL: size %dx%d != 64x64\n", w, h);
        goto out;
     }

   /* 校验填充的像素可观察结果（红色不透明） */
   data = imlib_image_get_data_for_reading_only();
   if (!data || data[0] != 0xffff0000u)
     {
        fprintf(stderr, "FAIL: pixel[0] = %08x != ffff0000\n",
                data ? (unsigned) data[0] : 0u);
        goto out;
     }

   /* 公开 API：缩放 64x64 -> 32x32 */
   imlib_context_set_image(img);
   scaled = imlib_create_cropped_scaled_image(0, 0, 64, 64, 32, 32);
   if (!scaled)
     {
        fprintf(stderr, "FAIL: imlib_create_cropped_scaled_image NULL\n");
        goto out;
     }
   imlib_context_set_image(scaled);
   if (imlib_image_get_width() != 32 || imlib_image_get_height() != 32)
     {
        fprintf(stderr, "FAIL: scaled size != 32x32\n");
        goto out;
     }

   imlib_free_image();
   imlib_context_set_image(img);
   imlib_free_image();

   printf("OK: imlib2 %d.%d.%d consumer test passed\n",
          (imlib_version() >> 16) & 0xff,
          (imlib_version() >> 8) & 0xff,
          imlib_version() & 0xff);
   ret = 0;

out:
   return ret;
}
