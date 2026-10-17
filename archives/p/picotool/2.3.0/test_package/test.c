/* test_package/test.c — picotool 2.3.0 consumer test (R34 合规)
 *
 * L1 test（同 2.2.0/audispd 先例）：
 * 1. 校验包内 bin/picotool 存在；
 * 2. 读取文件头校验为有效 64 位 ELF（magic + EI_CLASS）——真实读取
 *    产物验证。
 */
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *path = "bin/picotool";
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        printf("picotool 2.3.0 consumer test FAILED: %s not found\n", path);
        return 1;
    }
    unsigned char buf[20] = {0};
    size_t n = fread(buf, 1, 20, fp);
    fclose(fp);
    if (n < 20 || buf[0] != 0x7f || buf[1] != 'E' || buf[2] != 'L' ||
        buf[3] != 'F' || buf[4] != 2 /* EI_CLASS 64-bit */) {
        printf("picotool 2.3.0 consumer test FAILED: invalid ELF\n");
        return 1;
    }
    printf("picotool 2.3.0 consumer test OK (valid 64-bit ELF "
           "bin/picotool)\n");
    return 0;
}
