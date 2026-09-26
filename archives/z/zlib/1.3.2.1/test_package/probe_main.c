/*
 * test_package/probe_main.c — 鸿蒙特有验证运行器（E539/E541）。
 * dlopen 上一步链好的 libzpic_probe.so，真实调用其导出的 zlib-backed
 * compress/uncompress 往返，并校验数据完整性。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <zlib.h>

typedef int (*roundtrip_fn)(const unsigned char *, unsigned long,
                            unsigned char *, unsigned long *);
typedef const char *(*version_fn)(void);

int main(void) {
    void *h = dlopen("./libzpic_probe.so", RTLD_NOW);
    if (!h) { fprintf(stderr, "FAIL: dlopen: %s\n", dlerror()); return 1; }
    version_fn ver = (version_fn)dlsym(h, "zpic_probe_version");
    roundtrip_fn rt = (roundtrip_fn)dlsym(h, "zpic_probe_roundtrip");
    if (!ver || !rt) { fprintf(stderr, "FAIL: dlsym\n"); return 1; }
    printf("probe zlib version: %s\n", ver());
    const char *msg = "HarmonyOS PC zlib static-PIC DSO probe";
    unsigned long in_len = strlen(msg);
    unsigned char out[1024];
    unsigned long out_len = sizeof(out);
    int rc = rt((const unsigned char *)msg, in_len, out, &out_len);
    if (rc != Z_OK) { fprintf(stderr, "FAIL: roundtrip rc=%d\n", rc); return 1; }
    if (out_len != in_len || memcmp(out, msg, in_len) != 0) {
        fprintf(stderr, "FAIL: data mismatch out_len=%lu in_len=%lu\n", out_len, in_len);
        return 1;
    }
    printf("PASS: compress/uncompress roundtrip via static-PIC DSO OK (%lu bytes)\n", out_len);
    dlclose(h);
    return 0;
}
