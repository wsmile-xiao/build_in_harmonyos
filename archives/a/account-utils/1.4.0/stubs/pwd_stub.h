/* Stub declarations for glibc passwd/shadow stream + lookup functions.
 * SPDX-License-Identifier: BSD-3-Clause */
#ifndef PWD_STUB_H
#define PWD_STUB_H

#include <stdio.h>
#include <pwd.h>
#include <shadow.h>

#ifdef __cplusplus
extern "C" {
#endif

struct passwd *fgetpwent(FILE *stream);
struct spwd *fgetspent(FILE *stream);
struct spwd *getspnam(const char *name);

#ifdef __cplusplus
}
#endif

#endif /* PWD_STUB_H */
