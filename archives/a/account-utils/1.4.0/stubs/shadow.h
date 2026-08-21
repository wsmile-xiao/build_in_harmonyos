/* OHOS stub：保留系统 shadow.h 定义，仅补 getspnam/fgetspent 声明 */
#ifndef SHADOW_STUB_SYS_H
#define SHADOW_STUB_SYS_H
#include_next <shadow.h>
#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif
struct spwd *getspnam(const char *name);
struct spwd *fgetspent(FILE *stream);
#ifdef __cplusplus
}
#endif
#endif /* SHADOW_STUB_SYS_H */
