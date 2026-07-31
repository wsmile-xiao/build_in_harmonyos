#include <dlfcn.h>
#include <grp.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef NSS_WRAPPER_TEST_LIBRARY
#error "NSS_WRAPPER_TEST_LIBRARY is not defined"
#endif

static int write_text_file(const char *path, const char *content)
{
    FILE *fp = fopen(path, "w");
    if (fp == NULL) {
        perror(path);
        return 1;
    }
    if (fputs(content, fp) < 0) {
        perror(path);
        fclose(fp);
        return 1;
    }
    if (fclose(fp) != 0) {
        perror(path);
        return 1;
    }
    return 0;
}

static int expect_string(const char *label, const char *actual, const char *expected)
{
    if (actual == NULL || strcmp(actual, expected) != 0) {
        fprintf(stderr, "%s mismatch: got '%s', expected '%s'\n",
                label, actual ? actual : "(null)", expected);
        return 1;
    }
    return 0;
}

int main(void)
{
    const char *passwd_path = getenv("NSS_WRAPPER_PASSWD");
    const char *group_path = getenv("NSS_WRAPPER_GROUP");
    struct passwd *pwd;
    struct group *grp;
    char hostname[128];
    void *handle = dlopen(NSS_WRAPPER_TEST_LIBRARY, RTLD_LAZY);

    if (handle == NULL) {
        fprintf(stderr, "dlopen failed for %s: %s\n",
                NSS_WRAPPER_TEST_LIBRARY,
                dlerror());
        return 1;
    }
    dlclose(handle);

    if (passwd_path == NULL || group_path == NULL) {
        fprintf(stderr, "NSS_WRAPPER_PASSWD and NSS_WRAPPER_GROUP must be set\n");
        return 1;
    }

    if (write_text_file(passwd_path,
                        "ohosuser:x:4242:4242:OHOS Test User:/data/ohosuser:/bin/false\n") != 0) {
        return 1;
    }
    if (write_text_file(group_path,
                        "ohosgrp:x:4242:ohosuser\n") != 0) {
        return 1;
    }

    pwd = getpwnam("ohosuser");
    if (pwd == NULL || pwd->pw_uid != 4242 || pwd->pw_gid != 4242 ||
        expect_string("pw_name", pwd->pw_name, "ohosuser") ||
        expect_string("pw_dir", pwd->pw_dir, "/data/ohosuser") ||
        expect_string("pw_shell", pwd->pw_shell, "/bin/false")) {
        return 1;
    }

    pwd = getpwuid(4242);
    if (pwd == NULL || expect_string("getpwuid name", pwd->pw_name, "ohosuser")) {
        return 1;
    }

    grp = getgrnam("ohosgrp");
    if (grp == NULL || grp->gr_gid != 4242 ||
        expect_string("gr_name", grp->gr_name, "ohosgrp") ||
        grp->gr_mem == NULL || grp->gr_mem[0] == NULL ||
        expect_string("group member", grp->gr_mem[0], "ohosuser")) {
        return 1;
    }

    grp = getgrgid(4242);
    if (grp == NULL || expect_string("getgrgid name", grp->gr_name, "ohosgrp")) {
        return 1;
    }

    if (gethostname(hostname, sizeof(hostname)) != 0 ||
        expect_string("hostname", hostname, "nss-wrapper-ohos-test")) {
        return 1;
    }

    puts("nss-wrapper LD_PRELOAD passwd/group/hostname checks passed");
    return 0;
}
