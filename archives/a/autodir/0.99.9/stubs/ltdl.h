/*
 * ltdl.h — minimal libltdl API declarations for HarmonyOS stub
 *
 * OHOS sysroot 无 ltdl.h（libltdl 头+库都缺）——autodir 源码
 * （src/autodir.c + module.c）include <ltdl.h>——本头提供 autodir
 * 用到的 libltdl API 声明（实现见 stub-ltdl.c——模块加载不可用，
 * 主功能正常——MANIFEST 如实申报，同 mydumper/itstool stub 先例）。
 */
#ifndef LTDL_H
#define LTDL_H

#define LT_VERSION_MAJOR 2
#define LT_VERSION_MINOR 4

typedef struct lt_dlhandle_struct *lt_dlhandle;
typedef void *lt_ptr;

#define LT_SYMBOL_OVERHEAD 0

int lt_dlinit(void);
int lt_dlexit(void);
lt_dlhandle lt_dlopen(const char *filename);
lt_dlhandle lt_dlopenext(const char *filename);
void *lt_dlsym(lt_dlhandle handle, const char *name);
const char *lt_dlerror(void);
int lt_dlclose(lt_dlhandle handle);
const char *lt_dlgetsearchpath(void);
int lt_dlsetsearchpath(const char *search_path);

#endif /* LTDL_H */
