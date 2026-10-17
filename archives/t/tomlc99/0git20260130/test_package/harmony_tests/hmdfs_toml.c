/* One HarmonyOS PC case: real UTF-8 TOML I/O and parser on private HMDFS. */
#if !defined(__OHOS__) || !defined(__aarch64__)
#error Native HarmonyOS PC ARM64 is required
#endif
#include <toml.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

int main(int argc, char **argv) {
    const char input[] = "\"标题\" = \"鸿蒙✓\"\ncount = 42\n";
    struct utsname platform;
    struct stat parent, actual;
    char path[4096], error[256];
    FILE *file = NULL;
    toml_table_t *table = NULL;
    toml_datum_t title = {0};
    int rc = 1, created = 0, stage = 1;
    if (argc != 2 || uname(&platform) || strcmp(platform.sysname, "HarmonyOS") ||
        strcmp(platform.machine, "aarch64") || strncmp(argv[1], "/storage/Users/", 15)) goto cleanup;
    if (stat(argv[1], &parent) || !S_ISDIR(parent.st_mode)) goto cleanup;
    int n = snprintf(path, sizeof(path), "%s/鸿蒙-解析-%ld.toml", argv[1], (long)getpid());
    if (n < 0 || n >= (int)sizeof(path)) goto cleanup;
    stage = 2;
    file = fopen(path, "wx");
    if (!file) goto cleanup;
    created = 1;
    if (fwrite(input, 1, sizeof(input) - 1, file) != sizeof(input) - 1 || fflush(file)) goto cleanup;
    if (fclose(file)) { file = NULL; goto cleanup; }
    file = NULL;
    stage = 3;
    /* HMDFS reports a projected storage owner, not necessarily the process UID. */
    if (stat(path, &actual) || !S_ISREG(actual.st_mode) || actual.st_uid != parent.st_uid ||
        actual.st_size != (off_t)(sizeof(input) - 1)) goto cleanup;
    file = fopen(path, "r");
    if (!file) goto cleanup;
    table = toml_parse_file(file, error, sizeof(error));
    if (fclose(file)) { file = NULL; goto cleanup; }
    file = NULL;
    if (!table) goto cleanup;
    stage = 4;
    title = toml_string_in(table, "标题");
    toml_datum_t count = toml_int_in(table, "count");
    if (!title.ok || strcmp(title.u.s, "鸿蒙✓") || !count.ok || count.u.i != 42) goto cleanup;
    if (unlink(path)) goto cleanup;
    created = 0;
    errno = 0;
    if (stat(path, &actual) != -1 || errno != ENOENT) goto cleanup;
    rc = 0;
cleanup:
    if (title.ok) free(title.u.s);
    if (table) toml_free(table);
    if (file && fclose(file)) rc = 1;
    if (created && unlink(path)) rc = 1;
    if (rc) fprintf(stderr, "Harmony HMDFS TOML FAIL stage=%d errno=%d\n", stage, errno);
    else puts("HARMONY_TEST_PASS=1/1 PASS");
    return rc;
}
