/* SELinux stub implementations */
#include <stdlib.h>
#include "selinux/selinux.h"

int is_selinux_enabled(void) { return 0; }
int getcon(char **con) { if (con) *con = NULL; return 0; }
int setcon(const char *con) { (void) con; return 0; }
int getfilecon(const char *path, char **con) { (void) path; if (con) *con = NULL; return 0; }
int setfilecon(const char *path, const char *con) { (void) path; (void) con; return 0; }
int freecon(char *con) { (void) con; return 0; }
int security_getenforce(void) { return 0; }
int security_setenforce(int value) { (void) value; return 0; }
