/*
 * test_package/probe_main.c — 鸿蒙特有验证运行器（参考 zlib 1.3.2.1 做法 adapated）。
 * dlopen 链接了 libtiff 的 libtiff_probe.so，真实调用写图/读图导出函数并比对像素，
 * 证明 libtiff.so 在 DSO 消费者视角 + XPM 签名环境下完整可用。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

typedef int (*write_fn)(const char *);
typedef int (*read_fn)(const char *, int, unsigned char *);
typedef const char *(*version_fn)(void);

int main(void) {
    void *h = dlopen("./libtiff_probe.so", RTLD_NOW);
    if (!h) { fprintf(stderr, "FAIL: dlopen: %s\n", dlerror()); return 1; }
    write_fn wr = (write_fn)dlsym(h, "tiff_probe_write_gray");
    read_fn rd = (read_fn)dlsym(h, "tiff_probe_read_row");
    version_fn ver = (version_fn)dlsym(h, "tiff_probe_version");
    if (!wr || !rd || !ver) { fprintf(stderr, "FAIL: dlsym\n"); return 1; }
    printf("probe libtiff: %s\n", ver());

    const char *fn = "probe_gray.tif";
    if (wr(fn) != 0) { fprintf(stderr, "FAIL: probe write\n"); return 1; }
    /* DEFLATE 压缩流不支持随机访问，须从第 0 行起顺序读（libtiff 约束）。 */
    unsigned char expect[2][4] = {{0,1,2,3},{4,5,6,7}}, got[4];
    for (int y = 0; y < 2; y++) {
        if (rd(fn, y, got) != 0) { fprintf(stderr, "FAIL: probe read row %d\n", y); return 1; }
        if (memcmp(got, expect[y], 4) != 0) {
            fprintf(stderr, "FAIL: row %d pixel mismatch\n", y); return 1;
        }
    }
    remove(fn);
    printf("PASS: DSO-consumer write/read via libtiff.so OK (DEFLATE, 4x2)\n");
    dlclose(h);
    return 0;
}
