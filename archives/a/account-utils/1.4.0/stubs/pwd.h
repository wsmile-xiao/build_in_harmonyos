/* OHOS stub：保留系统 pwd.h 定义，仅补 fgetpwent 声明 */
#ifndef PWD_STUB_SYS_H
#define PWD_STUB_SYS_H
#include_next <pwd.h>
#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif
struct passwd *fgetpwent(FILE *stream);
#ifdef __cplusplus
}
#endif
#endif /* PWD_STUB_SYS_H */
