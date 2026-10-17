#ifndef UTEST_OHOS_TEST_TMPFILE_H
#define UTEST_OHOS_TEST_TMPFILE_H
#if !defined(__OHOS__)
#error This test compatibility backend is only for native OHOS
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#ifdef __cplusplus
#if __cplusplus >= 201103L
#define UTEST_OHOS_NULL nullptr
#else
#define UTEST_OHOS_NULL NULL
#endif
#else
#define UTEST_OHOS_NULL NULL
#endif

/* Test-only stdio stream backend: preserve write/seek/read/close semantics.
 * OHOS tmpfile() may use inaccessible /tmp regardless of TMPDIR. Never write
 * shared /tmp or change the installed utest.h/public libc API. */
static __attribute__((unused)) FILE *utest_ohos_tmpfile(void) {
  const char *dir = getenv("TMPDIR");
  const char suffix[] = "/utest-stream-XXXXXX";
  size_t length;
  char *name;
  int fd, saved;
  FILE *stream;
  if (!dir || strncmp(dir, "/storage/Users/", 15) != 0) {
    errno = EINVAL;
    return UTEST_OHOS_NULL;
  }
  length = strlen(dir) + sizeof(suffix);
#ifdef __cplusplus
  name = static_cast<char *>(malloc(length));
#else
  name = (char *)malloc(length);
#endif
  if (!name) return UTEST_OHOS_NULL;
  (void)snprintf(name, length, "%s%s", dir, suffix);
  fd = mkstemp(name);
  if (fd < 0) { saved = errno; free(name); errno = saved; return UTEST_OHOS_NULL; }
  stream = fdopen(fd, "w+b");
  if (!stream) {
    saved = errno;
    (void)close(fd); (void)unlink(name); free(name); errno = saved;
    return UTEST_OHOS_NULL;
  }
  if (unlink(name) != 0) {
    saved = errno;
    (void)fclose(stream); (void)unlink(name); free(name); errno = saved;
    return UTEST_OHOS_NULL;
  }
  free(name);
  return stream;
}
#define tmpfile utest_ohos_tmpfile
#endif
