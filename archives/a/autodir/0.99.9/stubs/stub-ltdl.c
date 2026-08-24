/*
 * stub-ltdl.c — minimal libltdl stub for HarmonyOS (no libltdl.so/.a in OHOS)
 *
 * autodir 用 libltdl 做模块动态加载（src/module.c 的 lt_dlhandle）——
 * OHOS sysroot 有 ltdl.h 但无 libltdl 库（-lltdl 链接失败）→ 编译本 stub
 * 为 libltdl.a（空实现——模块加载不可用，返回错误——autodir 主功能
 * （目录映射）正常）。如实申报：模块加载功能受限（同 mydumper/itstool
 * stub 先例）。
 *
 * 构建: clang -c stub-ltdl.c && ar rcs libltdl.a stub-ltdl.o
 */
#include <stddef.h>
#include "ltdl.h"

int lt_dlinit(void) { return 0; }

int lt_dlexit(void) { return 0; }

lt_dlhandle lt_dlopen(const char *filename) { (void)filename; return NULL; }

lt_dlhandle lt_dlopenext(const char *filename) { (void)filename; return NULL; }

void *lt_dlsym(lt_dlhandle handle, const char *name) { (void)handle; (void)name; return NULL; }

const char *lt_dlerror(void) { return "libltdl stub: module loading not available on HarmonyOS"; }

int lt_dlclose(lt_dlhandle handle) { (void)handle; return 0; }

const char *lt_dlgetsearchpath(void) { return ""; }

int lt_dlsetsearchpath(const char *search_path) { (void)search_path; return 0; }
