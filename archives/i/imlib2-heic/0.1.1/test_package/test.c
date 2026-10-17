/*
 * test.c — 真实 test_package 消费者校验（imlib2-heic 0.1.1）
 *
 * 从安装包 lib/imlib2/loaders/ 找到并 dlopen heic.so（dlopen 插件，
 * 不提供链接库/头文件），dlsym load/save/formats 三个公开 loader ABI，
 * 调用 formats() 校验注册 heic/heif——验证安装产物可被消费者正常加载。
 * 插件路径通过编译宏 IMLIB2_HEIC_PLUGIN 注入（由 test_package/conanfile.py
 * 依据实际 package_folder 生成），避免写死路径。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef IMLIB2_HEIC_PLUGIN
#define IMLIB2_HEIC_PLUGIN "heic.so"
#endif

/* imlib2 loader ABI 公开结构（见插件 imlib2_common.h / loader.h） */
typedef struct _imlibimage ImlibImage;
typedef struct _imlibloader ImlibLoader;
typedef int (*ImlibProgressFunction)(ImlibImage *im, char percent,
                                     int update_x, int update_y,
                                     int update_w, int update_h);
struct _imlibloader
{
   char         *file;
   int           num_formats;
   char        **formats;
   void         *handle;
   char        (*load)(ImlibImage *im, ImlibProgressFunction progress,
                       char progress_granularity, char immediate_load);
   char        (*save)(ImlibImage *im, ImlibProgressFunction progress,
                       char progress_granularity);
   ImlibLoader  *next;
};

int
main(void)
{
   /* 优先取运行时环境变量（由 test_package/conanfile.py 注入安装包内
    * 插件绝对路径），缺失时回退到编译期宏 */
   const char *so = getenv("IMLIB2_HEIC_PLUGIN");
   if (!so || !*so)
     so = IMLIB2_HEIC_PLUGIN;
   void *h;
   void (*p_formats)(ImlibLoader *) = NULL;
   char (*p_load)(ImlibImage *, ImlibProgressFunction, char, char) = NULL;
   char (*p_save)(ImlibImage *, ImlibProgressFunction, char) = NULL;
   ImlibLoader loader;
   int num_formats = 0, i, found_heic = 0, found_heif = 0, failures = 0;

   printf("test_package: plugin = %s\n", so);
   h = dlopen(so, RTLD_NOW);
   if (!h) {
      fprintf(stderr, "FAIL: dlopen %s: %s\n", so, dlerror());
      return 1;
   }
   printf("PASS: dlopen\n");

   *(void **)(&p_formats) = dlsym(h, "formats");
   *(void **)(&p_load) = dlsym(h, "load");
   *(void **)(&p_save) = dlsym(h, "save");
   if (!p_formats || !p_load || !p_save) {
      fprintf(stderr, "FAIL: missing loader ABI symbols\n");
      dlclose(h);
      return 1;
   }
   printf("PASS: loader ABI symbols (load/save/formats)\n");

   memset(&loader, 0, sizeof(loader));
   p_formats(&loader);                  /* 上游签名: void formats(ImlibLoader*) */
   num_formats = loader.num_formats;
   for (i = 0; i < num_formats && i < 16; i++) {
      if (loader.formats && loader.formats[i]) {
         printf("  format[%d] = %s\n", i, loader.formats[i]);
         if (strcmp(loader.formats[i], "heic") == 0) found_heic = 1;
         if (strcmp(loader.formats[i], "heif") == 0) found_heif = 1;
      }
   }
   if (!found_heic) { fprintf(stderr, "FAIL: no 'heic'\n"); failures++; }
   if (!found_heif) { fprintf(stderr, "FAIL: no 'heif'\n"); failures++; }
   if (loader.formats) {
      for (i = 0; i < num_formats; i++) free(loader.formats[i]);
      free(loader.formats);
   }

   dlclose(h);
   if (failures) {
      fprintf(stderr, "RESULT: FAIL (%d)\n", failures);
      return 1;
   }
   printf("RESULT: PASS\n");
   return 0;
}