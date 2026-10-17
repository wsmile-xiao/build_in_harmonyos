/* Minimal stub of selinux/selinux.h for OHOS (no SELinux). */
#ifndef SELINUX_STUB_H
#define SELINUX_STUB_H

#include <stdio.h>

typedef char *security_context_t;

#ifdef __cplusplus
extern "C" {
#endif

int is_selinux_enabled(void);
int getcon(char **con);
int setcon(const char *con);
int getfilecon(const char *path, char **con);
int setfilecon(const char *path, const char *con);
int freecon(char *con);
int security_getenforce(void);
int security_setenforce(int value);

#ifdef __cplusplus
}
#endif

#endif /* SELINUX_STUB_H */
