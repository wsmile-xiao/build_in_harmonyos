#include <stdio.h>
#include <libdevmapper.h>

int main(void) {
    /* 消费者视角验证: 链接 libdevmapper 并取运行时库版本
     * int dm_get_library_version(char *version, size_t size)
     * 返回约定: 1=成功 0=失败 (dm_strncpy 布尔语义, lvm2 惯例) */
    char ver[64];
    if (dm_get_library_version(ver, sizeof(ver)) == 0 || ver[0] == '\0') {
        fprintf(stderr, "FAIL: dm_get_library_version() returned empty/err\n");
        return 1;
    }
    printf("libdevmapper version: %s\n", ver);
    printf("test lvm2 2.03.42: OK\n");
    return 0;
}
