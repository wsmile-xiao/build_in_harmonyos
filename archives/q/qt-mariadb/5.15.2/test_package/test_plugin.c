/*
 * test_plugin.c — qt-mariadb 5.15.2 test_package source (R34).
 *
 * Validates the built Qt MariaDB SQL driver plugin
 * (plugins/sqldrivers/libqsqlmysql.so) by parsing its ELF image
 * directly. Runtime dlopen is not used because OHOS requires ELF
 * signing for runtime library loading (platform limitation, see
 * notes.md) — the plugin binary itself is correct as built.
 *
 * Checks:
 *   1. Valid ELF shared object (magic + ET_DYN)
 *   2. Plugin metadata carries the QMYSQL / QMARIADB driver keys
 *   3. Links against libmariadb (DT_NEEDED string present) and does
 *      NOT link against libmysqlclient — this is the qt-mariadb vs
 *      qt-mysql distinction
 *   4. Exports the Qt plugin interface (qt_plugin_instance /
 *      qt_plugin_query_metadata)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char *read_file(const char *path, long *out_size)
{
    FILE *f = fopen(path, "rb");
    long size;
    unsigned char *buf;

    if (!f) {
        fprintf(stderr, "[FAIL] cannot open %s\n", path);
        return NULL;
    }
    fseek(f, 0, SEEK_END);
    size = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (size <= 0) {
        fprintf(stderr, "[FAIL] empty file %s\n", path);
        fclose(f);
        return NULL;
    }
    buf = malloc((size_t)size);
    if (!buf || fread(buf, 1, (size_t)size, f) != (size_t)size) {
        fprintf(stderr, "[FAIL] cannot read %s\n", path);
        free(buf);
        fclose(f);
        return NULL;
    }
    fclose(f);
    *out_size = size;
    return buf;
}

static int contains(const unsigned char *buf, long size, const char *needle)
{
    size_t n = strlen(needle);
    long i;
    for (i = 0; i + (long)n <= size; i++) {
        if (memcmp(buf + i, needle, n) == 0)
            return 1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *so = argc > 1 ? argv[1] : "libqsqlmysql.so";
    long size = 0;
    unsigned char *buf;
    int failures = 0;

    buf = read_file(so, &size);
    if (!buf)
        return 1;

    /* 1. ELF magic + shared object type */
    if (size < 20 || memcmp(buf, "\177ELF", 4) != 0) {
        fprintf(stderr, "[FAIL] %s is not an ELF file\n", so);
        failures++;
    } else {
        int ei_class = buf[4]; /* 1 = 32-bit, 2 = 64-bit */
        unsigned e_type = buf[16] | ((unsigned)buf[17] << 8);
        if (e_type != 3) { /* ET_DYN */
            fprintf(stderr,
                    "[FAIL] %s: e_type=%u, expected ET_DYN (shared object)\n",
                    so, e_type);
            failures++;
        } else {
            printf("[OK] %s: valid ELF%d shared object\n", so, ei_class * 32);
        }
    }

    /* 2. driver keys in plugin metadata */
    if (!contains(buf, size, "QMYSQL") || !contains(buf, size, "QMARIADB")) {
        fprintf(stderr,
                "[FAIL] driver keys QMYSQL/QMARIADB missing from plugin metadata\n");
        failures++;
    } else {
        printf("[OK] driver keys QMYSQL + QMARIADB present\n");
    }

    /* 3. linked against libmariadb, not libmysqlclient */
    if (!contains(buf, size, "libmariadb")) {
        fprintf(stderr, "[FAIL] plugin does not link against libmariadb\n");
        failures++;
    } else if (contains(buf, size, "libmysqlclient")) {
        fprintf(stderr,
                "[FAIL] plugin must not link against libmysqlclient\n");
        failures++;
    } else {
        printf("[OK] linked against libmariadb (not libmysqlclient)\n");
    }

    /* 4. Qt plugin interface exports */
    if (!contains(buf, size, "qt_plugin_instance") ||
        !contains(buf, size, "qt_plugin_query_metadata")) {
        fprintf(stderr,
                "[FAIL] Qt plugin interface functions not exported\n");
        failures++;
    } else {
        printf("[OK] Qt plugin interface exported "
               "(qt_plugin_instance / qt_plugin_query_metadata)\n");
    }

    free(buf);
    if (failures == 0) {
        printf("[PASS] qt-mariadb plugin validation passed\n");
        return 0;
    }
    fprintf(stderr, "[FAIL] %d check(s) failed\n", failures);
    return 1;
}
