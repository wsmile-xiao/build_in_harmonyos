#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* 验证 LV2 插件 bundle：dlopen 加载 sherlock.so 并调用 lv2_descriptor()
 * 验证插件入口点（R34 非空壳——调用被测库 API），并检查 manifest.ttl
 * 含插件声明（bundle 完整性） */
int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: test_sherlock <bundle-dir>\n");
        return 2;
    }
    char ttl[1024], so[1024];
    snprintf(ttl, sizeof(ttl), "%s/manifest.ttl", argv[1]);
    snprintf(so, sizeof(so), "%s/sherlock.so", argv[1]);
    /* manifest.ttl 检查（bundle 完整性：含插件 URI 声明） */
    FILE *fp = fopen(ttl, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: %s 不存在\n", ttl);
        return 1;
    }
    char buf[8192];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    fclose(fp);
    if (strstr(buf, "sherlock") == NULL) {
        fprintf(stderr, "FAIL: manifest.ttl 缺插件声明\n");
        return 1;
    }
    /* dlopen 加载 sherlock.so 并调用 lv2_descriptor()（LV2 插件入口 API） */
    void *h = dlopen(so, RTLD_NOW);
    if (!h) {
        fprintf(stderr, "FAIL: dlopen(%s) 失败: %s\n", so, dlerror());
        return 1;
    }
    void *(*lv2_descriptor)(uint32_t) =
        (void *(*)(uint32_t))dlsym(h, "lv2_descriptor");
    if (!lv2_descriptor) {
        fprintf(stderr, "FAIL: dlsym(lv2_descriptor) 失败: %s\n", dlerror());
        dlclose(h);
        return 1;
    }
    void *desc = lv2_descriptor(0);
    dlclose(h);
    if (!desc) {
        fprintf(stderr, "FAIL: lv2_descriptor(0) 返回 NULL（插件入口无效）\n");
        return 1;
    }
    printf("PASS: manifest.ttl 含插件声明 + dlopen 加载 sherlock.so 且 lv2_descriptor() 入口有效\n");
    return 0;
}
