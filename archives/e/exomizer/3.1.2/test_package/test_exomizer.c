/* test_exomizer.c — exomizer R34 consumer test.
 *
 * 真实执行安装的 exomizer 二进制并做 raw 压缩/解压 roundtrip:
 *   1. exomizer raw -q -C <sample> -o <out>/sample.exo
 *   2. exomizer raw -q -d <out>/sample.exo -o <out>/restored.bin
 *   3. 字节级比对 sample 与 restored.bin
 * 任何一步失败(含二进制缺失/exec 失败)即非零退出 — 非空壳测试。
 *
 * usage: test_exomizer <exomizer-bin> <sample> <out-dir>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int read_file(const char *path, unsigned char **buf, long *len) {
    FILE *f = fopen(path, "rb");
    long n;
    if (!f) { fprintf(stderr, "cannot open %s\n", path); return -1; }
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return -1; }
    n = ftell(f);
    if (n < 0 || fseek(f, 0, SEEK_SET) != 0) { fclose(f); return -1; }
    *buf = (unsigned char *)malloc((size_t)n);
    if (!*buf) { fclose(f); return -1; }
    if (fread(*buf, 1, (size_t)n, f) != (size_t)n) {
        free(*buf); fclose(f); return -1;
    }
    fclose(f);
    *len = n;
    return 0;
}

int main(int argc, char **argv) {
    char cmd[2048];
    int rc;
    unsigned char *orig = NULL, *restored = NULL;
    long orig_len = 0, rest_len = 0;

    if (argc != 4) {
        fprintf(stderr, "usage: test_exomizer <exomizer-bin> <sample> <out-dir>\n");
        return 2;
    }

    snprintf(cmd, sizeof(cmd), "\"%s\" raw -q -C \"%s\" -o \"%s/sample.exo\"",
             argv[1], argv[2], argv[3]);
    rc = system(cmd);
    if (rc != 0) {
        fprintf(stderr, "FAIL: exomizer compress rc=%d\n", rc);
        return 1;
    }

    snprintf(cmd, sizeof(cmd), "\"%s\" raw -q -d \"%s/sample.exo\" -o \"%s/restored.bin\"",
             argv[1], argv[3], argv[3]);
    rc = system(cmd);
    if (rc != 0) {
        fprintf(stderr, "FAIL: exomizer decompress rc=%d\n", rc);
        return 1;
    }

    char rest_path[1200];
    snprintf(rest_path, sizeof(rest_path), "%s/restored.bin", argv[3]);
    if (read_file(argv[2], &orig, &orig_len) != 0 ||
        read_file(rest_path, &restored, &rest_len) != 0) {
        fprintf(stderr, "FAIL: cannot read sample/restored files\n");
        return 1;
    }
    if (orig_len != rest_len || memcmp(orig, restored, (size_t)orig_len) != 0) {
        fprintf(stderr, "FAIL: roundtrip mismatch orig=%ld restored=%ld\n",
                orig_len, rest_len);
        return 1;
    }
    printf("OK: exomizer roundtrip %ld bytes identical\n", orig_len);
    return 0;
}
