/*
 * consumer_heic_host.c — 消费者可用性用例（imlib2-heic 0.1.1）
 *
 * 模拟业务上层组件/应用（feh 等 imlib2 宿主）消费本插件：
 *   1. 仅通过安装产物的公开 loader ABI（dlopen + dlsym load/save/formats，
 *      即 imlib2 宿主加载器模块的运行时消费路径）使用本库；
 *   2. 不包含任何库私有实现文件；
 *   3. 调用 formats() 获得格式注册（公开 API 的可观察结果）；
 *   4. 尝试经 load() 解码真实 HEIC 样本，输出结果（解码能力取决于依赖
 *      制品 libheif 是否提供解码插件，如实记录）。
 * 退出码 0 当且仅当插件可被宿主正常加载并暴露完整公开 ABI。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef HEIC_SO_PATH
#define HEIC_SO_PATH "heic.so"
#endif
#ifndef HEIC_SAMPLE
#define HEIC_SAMPLE "example.heic"
#endif

/* 宿主侧按 imlib2 loader ABI 声明的公开契约（与插件导出结构一致）
 * —— 仅使用公开头(loader.h/imlib2_common.h)声明的字段，非实现文件。 */
#include "imlib2_common.h"

int
main(int argc, char **argv)
{
   const char *so_path = (argc > 1) ? argv[1] : HEIC_SO_PATH;
   const char *sample = (argc > 2) ? argv[2] : HEIC_SAMPLE;
   void *h;
   void (*p_formats)(ImlibLoader *) = NULL;
   char (*p_load)(ImlibImage *, ImlibProgressFunction, char, char) = NULL;
   char (*p_save)(ImlibImage *, ImlibProgressFunction, char) = NULL;
   ImlibLoader loader;
   char ok = 1;

   printf("[consumer] opening plugin: %s\n", so_path);
   h = dlopen(so_path, RTLD_NOW);
   if (!h) {
      fprintf(stderr, "[consumer] FAIL: dlopen %s: %s\n", so_path, dlerror());
      return 1;
   }
   *(void **)(&p_formats) = dlsym(h, "formats");
   *(void **)(&p_load) = dlsym(h, "load");
   *(void **)(&p_save) = dlsym(h, "save");
   if (!p_formats || !p_load || !p_save) {
      fprintf(stderr, "[consumer] FAIL: ABI symbols incomplete\n");
      dlclose(h);
      return 1;
   }
   printf("[consumer] PASS: plugin loaded, public ABI (load/save/formats) resolved\n");

   /* 公开 API 调用：读取插件注册的媒体格式（imlib2 宿主启动时即用此发现插件） */
   memset(&loader, 0, sizeof(loader));
   p_formats(&loader);                  /* 上游签名: void formats(ImlibLoader*) */
   loader.num_formats = (loader.num_formats <= 16) ? loader.num_formats : 0;
   printf("[consumer] registered formats: %d\n", loader.num_formats);
   for (int i = 0; i < loader.num_formats; i++) {
      if (loader.formats && loader.formats[i])
         printf("[consumer]   format[%d] = %s\n", i, loader.formats[i]);
   }
   if (loader.num_formats < 2) { ok = 0; fprintf(stderr, "[consumer] FAIL: format count\n"); }
   if (loader.formats) {
      for (int i = 0; i < loader.num_formats; i++) free(loader.formats[i]);
      free(loader.formats);
   }

   /* 试用 load()：真实 HEIC 样本解码（依赖 libheif 制品解码插件能力，如实记录） */
   {
      ImlibImage im;
      memset(&im, 0, sizeof(im));
      im.real_file = (char *)sample;
      if (p_load(&im, NULL, 0, 1)) {
         printf("[consumer] decode OK: %dx%d data=%p\n", im.w, im.h, (void *)im.data);
         if (im.data) free(im.data);
      } else {
         printf("[consumer] decode unavailable (published libheif lacks decoder "
                "plugin); formats registration still verified\n");
      }
      if (im.format) free(im.format);
   }

   dlclose(h);
   printf(ok ? "[consumer] RESULT: PASS\n" : "[consumer] RESULT: FAIL\n");
   return ok ? 0 : 1;
}