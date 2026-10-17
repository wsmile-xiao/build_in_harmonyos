/* Minimal stub of sys/capability.h for OHOS (no libcap). */
#ifndef SYS_CAPABILITY_STUB_H
#define SYS_CAPABILITY_STUB_H

typedef void *cap_t;

#define CAP_CHOWN 0
#define CAP_DAC_OVERRIDE 1
#define CAP_DAC_READ_SEARCH 2
#define CAP_SETUID 7
#define CAP_SETGID 6
#define CAP_NET_RAW 13
#define CAP_SYS_ADMIN 21
#define CAP_LAST_CAP 40

#ifdef __cplusplus
extern "C" {
#endif

cap_t cap_get_proc(void);
cap_t cap_get_file(const char *path);
int cap_set_proc(cap_t cap);
int cap_free(void *obj);
int cap_clear(cap_t cap);
int cap_set_flag(cap_t cap, int flag, int ncap, const int *caps, int value);
char *cap_to_text(cap_t cap, unsigned int *len);
cap_t cap_from_text(const char *text);
int cap_get_flag(cap_t cap, int capvalue, int flag, unsigned int *ret);

#ifdef __cplusplus
}
#endif

#endif /* SYS_CAPABILITY_STUB_H */
