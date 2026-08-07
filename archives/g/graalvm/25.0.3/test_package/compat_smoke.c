#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <grp.h>
#include <link.h>
#include <pwd.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef RTLD_DI_LMID
#define RTLD_DI_LMID 1
#endif

struct passwd *fgetpwent(FILE *stream);
struct group *fgetgrent(FILE *stream);
int fgetpwent_r(FILE *stream, struct passwd *pwd, char *buf, size_t len,
                struct passwd **result);
int fgetgrent_r(FILE *stream, struct group *grp, char *buf, size_t len,
                struct group **result);
const unsigned short **__ctype_b_loc(void);
const int32_t **__ctype_tolower_loc(void);
const int32_t **__ctype_toupper_loc(void);
int dlinfo(void *handle, int request, void *result);

static int assertions;

#ifdef GCOMPAT_SMOKE_TRACE
#define TRACE_ASSERTION(condition)                                               \
    fprintf(stderr, "checking assertion %d: %s\n", assertions, #condition)
#else
#define TRACE_ASSERTION(condition) ((void)0)
#endif

#define CHECK(condition)                                                        \
    do {                                                                        \
        ++assertions;                                                           \
        TRACE_ASSERTION(condition);                                             \
        if (!(condition)) {                                                     \
            fprintf(stderr, "assertion %d failed: %s\n", assertions,           \
                    #condition);                                                \
            return assertions;                                                  \
        }                                                                       \
    } while (0)

static int range_in_buffer(const void *value, size_t length,
                           const char *buffer, size_t size)
{
    uintptr_t address = (uintptr_t)value;
    uintptr_t start = (uintptr_t)buffer;

    return address >= start && length <= size && address - start <= size - length;
}

static int string_in_buffer(const char *value, const char *buffer, size_t size)
{
    uintptr_t address = (uintptr_t)value;
    uintptr_t start = (uintptr_t)buffer;
    size_t offset;

    if (address < start || address - start >= size) {
        return 0;
    }
    offset = (size_t)(address - start);
    return memchr(value, '\0', size - offset) != NULL;
}

static int environment_contains(char **environment, const char *entry)
{
    char **cursor;

    if (environment == NULL) {
        return 0;
    }
    for (cursor = environment; *cursor != NULL; ++cursor) {
        if (strcmp(*cursor, entry) == 0) {
            return 1;
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    FILE *stream;
    struct passwd *passwd_result;
    struct passwd passwd_storage;
    struct group *group_result;
    struct group group_storage;
    const unsigned short *ctype_bits;
    const int32_t *ctype_tolower;
    const int32_t *ctype_toupper;
    char ***runtime_environ;
    void *handle;
    struct link_map *map = NULL;
    Dl_info info;
    long lmid = -1;
    char buffer[512];
    int status;

    CHECK(argc == 3);
    runtime_environ = (char ***)dlsym(RTLD_DEFAULT, "__environ");
    CHECK(setenv("GRAALVM_GCOMPAT_ENVIRON", "updated", 1) == 0);
    CHECK(runtime_environ != NULL && *runtime_environ == environ &&
          environment_contains(*runtime_environ,
                               "GRAALVM_GCOMPAT_ENVIRON=updated"));
    CHECK(unsetenv("GRAALVM_GCOMPAT_ENVIRON") == 0 &&
          !environment_contains(*runtime_environ,
                                "GRAALVM_GCOMPAT_ENVIRON=updated"));
    stream = fopen(argv[1], "w+");
    CHECK(stream != NULL);
    CHECK(fputs("alice:x:1001:1002:Alice:/home/alice:/system/bin/sh\n",
                stream) >= 0);
    CHECK(fseek(stream, 0, SEEK_SET) == 0);
    passwd_result = fgetpwent(stream);
    CHECK(passwd_result != NULL);
    CHECK(strcmp(passwd_result->pw_name, "alice") == 0);
    CHECK(strcmp(passwd_result->pw_passwd, "x") == 0);
    CHECK(passwd_result->pw_uid == 1001);
    CHECK(passwd_result->pw_gid == 1002);
    CHECK(strcmp(passwd_result->pw_gecos, "Alice") == 0);
    CHECK(strcmp(passwd_result->pw_dir, "/home/alice") == 0);
    CHECK(strcmp(passwd_result->pw_shell, "/system/bin/sh") == 0);
    CHECK(fgetpwent(stream) == NULL && feof(stream));
    clearerr(stream);
    CHECK(fseek(stream, 0, SEEK_SET) == 0);
    status = fgetpwent_r(stream, &passwd_storage, buffer, sizeof(buffer),
                         &passwd_result);
    CHECK(status == 0 && passwd_result == &passwd_storage);
    CHECK(strcmp(passwd_storage.pw_name, "alice") == 0 &&
          passwd_storage.pw_uid == 1001 && passwd_storage.pw_gid == 1002);
    CHECK(string_in_buffer(passwd_storage.pw_name, buffer, sizeof(buffer)) &&
          string_in_buffer(passwd_storage.pw_passwd, buffer, sizeof(buffer)) &&
          string_in_buffer(passwd_storage.pw_gecos, buffer, sizeof(buffer)) &&
          string_in_buffer(passwd_storage.pw_dir, buffer, sizeof(buffer)) &&
          string_in_buffer(passwd_storage.pw_shell, buffer, sizeof(buffer)));
    CHECK(fclose(stream) == 0);

    stream = fopen(argv[2], "w+");
    CHECK(stream != NULL);
    CHECK(fputs("builders:x:2001:alice,bob\n", stream) >= 0);
    CHECK(fseek(stream, 0, SEEK_SET) == 0);
    group_result = fgetgrent(stream);
    CHECK(group_result != NULL);
    CHECK(strcmp(group_result->gr_name, "builders") == 0);
    CHECK(strcmp(group_result->gr_passwd, "x") == 0);
    CHECK(group_result->gr_gid == 2001);
    CHECK(strcmp(group_result->gr_mem[0], "alice") == 0);
    CHECK(strcmp(group_result->gr_mem[1], "bob") == 0);
    CHECK(group_result->gr_mem[2] == NULL);
    CHECK(fgetgrent(stream) == NULL && feof(stream));
    clearerr(stream);
    CHECK(fseek(stream, 0, SEEK_SET) == 0);
    status = fgetgrent_r(stream, &group_storage, buffer, sizeof(buffer),
                         &group_result);
    CHECK(status == 0 && group_result == &group_storage);
    CHECK(strcmp(group_storage.gr_name, "builders") == 0 &&
          group_storage.gr_gid == 2001);
    CHECK(strcmp(group_storage.gr_mem[0], "alice") == 0 &&
          strcmp(group_storage.gr_mem[1], "bob") == 0 &&
          group_storage.gr_mem[2] == NULL);
    CHECK(string_in_buffer(group_storage.gr_name, buffer, sizeof(buffer)) &&
          string_in_buffer(group_storage.gr_passwd, buffer, sizeof(buffer)));
    CHECK(range_in_buffer(group_storage.gr_mem,
                          3 * sizeof(*group_storage.gr_mem),
                          buffer, sizeof(buffer)) &&
           string_in_buffer(group_storage.gr_mem[0], buffer, sizeof(buffer)) &&
           string_in_buffer(group_storage.gr_mem[1], buffer, sizeof(buffer)));
    stream = freopen(argv[2], "w+", stream);
    CHECK(stream != NULL);
    CHECK(fputs("other:x:2002:charlie\n", stream) >= 0);
    CHECK(fseek(stream, 0, SEEK_SET) == 0);
    group_result = fgetgrent(stream);
    CHECK(group_result != NULL && strcmp(group_result->gr_name, "other") == 0 &&
          strcmp(group_result->gr_mem[0], "charlie") == 0);
    CHECK(strcmp(group_storage.gr_name, "builders") == 0 &&
          strcmp(group_storage.gr_mem[0], "alice") == 0 &&
          strcmp(group_storage.gr_mem[1], "bob") == 0);
    CHECK(fclose(stream) == 0);

    ctype_bits = *__ctype_b_loc();
    ctype_tolower = *__ctype_tolower_loc();
    ctype_toupper = *__ctype_toupper_loc();
    CHECK(ctype_bits != NULL && ctype_tolower != NULL && ctype_toupper != NULL);
    CHECK(ctype_tolower[EOF] == EOF);
    CHECK(ctype_toupper[EOF] == EOF);
    CHECK(ctype_tolower[0] == 0 && ctype_toupper[0] == 0);
    CHECK(ctype_tolower[0x80] == 0x80);
    CHECK(ctype_tolower[0xff] == 0xff);
    CHECK(ctype_toupper[0x80] == 0x80);
    CHECK(ctype_toupper[0xff] == 0xff);
    CHECK(ctype_tolower['A'] == 'a');
    CHECK(ctype_toupper['z'] == 'Z');
    CHECK((ctype_bits['A'] & 0x0508) == 0x0508);
    CHECK(ctype_bits[0x80] == 0 && ctype_bits[0xff] == 0);
    CHECK(ctype_tolower[(signed char)0x80] == 0x80 &&
          ctype_toupper[(signed char)0x80] == 0x80);
    CHECK(ctype_tolower[(signed char)0xfe] == 0xfe &&
          ctype_toupper[(signed char)0xfe] == 0xfe);

    handle = dlopen(NULL, RTLD_NOW);
    CHECK(handle != NULL);
    CHECK(dladdr((void *)&main, &info) != 0 && info.dli_fbase != NULL);
    CHECK(dlinfo(handle, RTLD_DI_LMID, &lmid) == 0 && lmid == 0);
    errno = 0;
    CHECK(dlinfo(handle, RTLD_DI_LINKMAP, &map) == -1 && errno == ENOTSUP);
    CHECK(map == NULL);
    errno = 0;
    CHECK(dlinfo(handle, -1, &map) == -1 && errno == EINVAL);
    CHECK(dlclose(handle) == 0);

    CHECK(assertions == 66);
    printf("GCOMPAT_ABI_ASSERTIONS=%d/%d\n", assertions, assertions);
    return 0;
}
