/* Consumer of the real installed theme bytes; no GRUB boot configuration changes. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define FILE_COUNT 23
#define PATH_CAP 4096

struct entry { char name[128]; unsigned long size; unsigned int crc; };

static int join(char *out, const char *root, const char *name)
{
    int n = snprintf(out, PATH_CAP, "%s/%s", root, name);
    return n < 0 || n >= PATH_CAP ? -1 : 0;
}

static int read_entries(const char *path, struct entry *entries)
{
    FILE *f = fopen(path, "r");
    char extra;
    int i;
    if (!f) return -1;
    for (i = 0; i < FILE_COUNT; ++i) {
        if (fscanf(f, "%x %lu %127s", &entries[i].crc, &entries[i].size,
                   entries[i].name) != 3 || strchr(entries[i].name, '/') ||
            strchr(entries[i].name, '\\') || strstr(entries[i].name, "..")) {
            fclose(f);
            return -1;
        }
    }
    i = fscanf(f, " %c", &extra);
    if (fclose(f) != 0) return -1;
    return i == EOF ? 0 : -1;
}

static int check_file(const char *path, const struct entry *entry)
{
    unsigned char buffer[8192];
    uint32_t crc = UINT32_C(0xffffffff);
    unsigned long total = 0;
    size_t n, i;
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    while ((n = fread(buffer, 1, sizeof(buffer), f)) != 0) {
        total += (unsigned long)n;
        for (i = 0; i < n; ++i) {
            unsigned bit;
            crc ^= buffer[i];
            for (bit = 0; bit < 8; ++bit)
                crc = (crc >> 1) ^ (UINT32_C(0xedb88320) & (0u - (crc & 1u)));
        }
    }
    i = (size_t)ferror(f);
    if (fclose(f) != 0 || i || total != entry->size || ~crc != entry->crc) return -1;
    return 0;
}

static int check_tree(const char *root, const struct entry *entries)
{
    char path[PATH_CAP];
    int i;
    for (i = 0; i < FILE_COUNT; ++i) {
        if (join(path, root, entries[i].name) || check_file(path, &entries[i])) {
            fprintf(stderr, "Invalid resource: %s\n", entries[i].name);
            return -1;
        }
    }
    return 0;
}

#ifdef __OHOS__
static int copy_file(const char *src, const char *dst)
{
    unsigned char buffer[8192];
    size_t n;
    int failed = 0;
    FILE *in = fopen(src, "rb"), *out;
    if (!in) return -1;
    out = fopen(dst, "wb");
    if (!out) { fclose(in); return -1; }
    while ((n = fread(buffer, 1, sizeof(buffer), in)) != 0) {
        if (fwrite(buffer, 1, n, out) != n) { failed = 1; break; }
    }
    if (ferror(in)) failed = 1;
    if (fclose(in)) failed = 1;
    if (fclose(out)) failed = 1;
    return failed ? -1 : 0;
}

static int sandbox(const char *root, const struct entry *entries)
{
    const char *tmp = getenv("TMPDIR");
    char base[PATH_CAP], first[PATH_CAP], moved[PATH_CAP];
    char src[PATH_CAP], dst[PATH_CAP];
    const char *active;
    int i, result = -1;
    if (!tmp || !*tmp || join(base, tmp, "breeze-XXXXXX") || !mkdtemp(base)) return -1;
    if (join(first, base, "theme with spaces") || join(moved, base, "Breeze-鸿蒙")) {
        rmdir(base);
        return -1;
    }
    active = first;
    if (mkdir(first, 0700)) { rmdir(base); return -1; }
    for (i = 0; i < FILE_COUNT; ++i) {
        if (join(src, root, entries[i].name) || join(dst, first, entries[i].name) ||
            copy_file(src, dst)) goto cleanup;
    }
    if (check_tree(first, entries) || rename(first, moved)) goto cleanup;
    active = moved;
    if (check_tree(moved, entries)) goto cleanup;
    result = 0;
cleanup:
    for (i = 0; i < FILE_COUNT; ++i)
        if (!join(dst, active, entries[i].name) && unlink(dst) && errno != ENOENT) result = -1;
    if (rmdir(active) || rmdir(base)) result = -1;
    return result;
}
#endif

int main(int argc, char **argv)
{
    struct entry entries[FILE_COUNT];
    int result;
    if (argc != 4 || read_entries(argv[3], entries)) {
        fprintf(stderr, "Usage: test_breeze --check|--sandbox theme-directory expected.tsv\n");
        return 2;
    }
    if (!strcmp(argv[1], "--check")) {
        result = check_tree(argv[2], entries);
        if (!result) puts("[ok] target resources: 23/23 byte counts and CRC32");
    } else if (!strcmp(argv[1], "--sandbox")) {
#ifdef __OHOS__
        result = sandbox(argv[2], entries);
        if (!result) puts("[ok] HarmonyOS TMPDIR copy/rename/reopen: 23/23 resources");
#else
        fputs("HarmonyOS sandbox test requires an OHOS SDK build\n", stderr);
        result = -1;
#endif
    } else return 2;
    return result ? 1 : 0;
}
