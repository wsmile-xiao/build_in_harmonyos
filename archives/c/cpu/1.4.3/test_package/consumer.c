/*
 * consumer.c -- consumer test for the cpu/1.4.3 package (HarmonyOS PC port).
 *
 * The cpu tarball installs no public headers (there is no install rule for
 * src/include), so the declarations below are copied verbatim from the upstream
 * sources of release 1.4.3:
 *
 *   Strdup/Free   src/include/util/xmem.h
 *   md5_buffer    src/include/util/cmd5.h
 *   sha_buffer    src/include/util/csha1.h
 *   cgetpwent     src/include/util/password.h (pfile_t PASSWORD == 0)
 *
 * The program is linked against the package's libcputil.so and drives that
 * library -- not the cpu front end -- with known-answer assertions:
 *
 *   1. Strdup()/Free() : allocation round trip
 *   2. md5_buffer()    : MD5("abc")  == 900150983cd24fb0d6963f7d28e17f72
 *   3. sha_buffer()    : SHA1("abc") == a9993e364706816aba3e25717850c26c9cd0d89d
 *   4. cgetpwent()     : parses a credentials file; found and not-found cases
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

/* --- upstream declarations (see the header comment) --- */
extern char *Strdup(const char *s, const char *msg, ...);
extern void Free(void *ptr);
extern void *md5_buffer(const char *buffer, size_t len, void *resblock);
extern void *sha_buffer(const char *buffer, size_t len, void *resblock);

typedef enum { PASSWORD, SHADOW } pfile_t;

struct cpass {
    char *pw_name;
    char *pw_passwd;
    uid_t pw_uid;
    gid_t pw_gid;
    char *pw_gecos;
    char *pw_dir;
    char *pw_shell;
    int sp_min;
    int sp_max;
    int sp_warn;
    int sp_inact;
    int sp_expire;
    int sp_flag;
};

extern struct cpass *cgetpwent(char *filename, char *name, pfile_t ftype);

static int failures;

static void check(int ok, const char *what)
{
    printf("%s  %s\n", ok ? "PASS " : "FAIL ", what);
    if (!ok)
        failures++;
}

static void hex(const unsigned char *bytes, size_t n, char *out)
{
    static const char digits[] = "0123456789abcdef";
    size_t i;

    for (i = 0; i < n; i++) {
        out[2 * i] = digits[bytes[i] >> 4];
        out[2 * i + 1] = digits[bytes[i] & 0x0f];
    }
    out[2 * n] = '\0';
}

int main(int argc, char **argv)
{
    unsigned char digest[20];
    char text[64];
    char path[512];
    char root_user[] = "root";
    char missing_user[] = "nosuchuser";
    struct cpass *pw;
    char *copy;
    const char *tmpdir;
    FILE *fp;
    int fd;

    /* /tmp is not reliably writable on OHOS (E002); the caller passes the test
     * work directory, with TMPDIR and /tmp as fallbacks. */
    tmpdir = argc > 1 ? argv[1] : getenv("TMPDIR");
    if (tmpdir == NULL || tmpdir[0] == '\0')
        tmpdir = "/tmp";
    snprintf(path, sizeof path, "%s/cpu-consumer-XXXXXX", tmpdir);

    /* 1. string helpers */
    copy = Strdup("cpu", "consumer test");
    check(copy != NULL && strcmp(copy, "cpu") == 0,
          "Strdup() returns a copy of its argument");
    if (copy != NULL) {
        Free(copy);
        check(1, "Free() releases the copy");
    } else {
        check(0, "Free() releases the copy");
    }

    /* 2. MD5 known answer */
    memset(digest, 0, sizeof digest);
    check(md5_buffer("abc", 3, digest) != NULL, "md5_buffer() digests a buffer");
    hex(digest, 16, text);
    check(strcmp(text, "900150983cd24fb0d6963f7d28e17f72") == 0,
          "md5_buffer(\"abc\") == 900150983cd24fb0d6963f7d28e17f72");

    /* 3. SHA-1 known answer */
    memset(digest, 0, sizeof digest);
    check(sha_buffer("abc", 3, digest) != NULL, "sha_buffer() digests a buffer");
    hex(digest, 20, text);
    check(strcmp(text, "a9993e364706816aba3e25717850c26c9cd0d89d") == 0,
          "sha_buffer(\"abc\") == a9993e364706816aba3e25717850c26c9cd0d89d");

    /* 4. credentials file parser */
    fd = mkstemp(path);
    check(fd >= 0, "mkstemp() created a credentials file");
    if (fd >= 0) {
        fp = fdopen(fd, "w");
        fputs("root:x:0:0:root:/root:/bin/sh\n"
              "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n", fp);
        fclose(fp);

        pw = cgetpwent(path, root_user, PASSWORD);
        check(pw != NULL, "cgetpwent() finds an existing entry");
        check(pw != NULL && pw->pw_uid == 0 && strcmp(pw->pw_name, "root") == 0,
              "cgetpwent(\"root\") reports uid 0 and the name from the file");

        pw = cgetpwent(path, missing_user, PASSWORD);
        check(pw == NULL, "cgetpwent() returns NULL for a missing entry");

        unlink(path);
    }

    printf("\n%s (%d failure(s))\n",
           failures ? "CONSUMER TEST FAILED" : "CONSUMER TEST PASSED", failures);
    return failures ? 1 : 0;
}
