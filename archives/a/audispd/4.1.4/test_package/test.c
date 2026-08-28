/* test_package/test.c — audispd 4.1.4 consumer test (R34 合规)
 *
 * L1 test:
 * 1. 真实读取包内产物 audisp-af_unix（audit 事件分发插件可执行）；
 * 2. 校验其为有效 64 位 ELF（magic + EI_CLASS）。
 * 注：不能无参运行——audisp 插件需完整 audit 内核环境（鸿蒙无），
 * 运行时缺依赖库属预期；以真实文件级 ELF 校验替代。
 */
#include <stdio.h>

int main(void) {
    FILE *f = fopen("audisp-af_unix", "rb");
    if (f == NULL) {
        fprintf(stderr, "audispd consumer test FAILED: "
                        "cannot open audisp-af_unix\n");
        return 1;
    }
    unsigned char hdr[16] = {0};
    size_t n = fread(hdr, 1, sizeof(hdr), f);
    fclose(f);
    if (n < 16 || hdr[0] != 0x7f || hdr[1] != 'E' || hdr[2] != 'L' ||
        hdr[3] != 'F') {
        fprintf(stderr, "audispd consumer test FAILED: "
                        "audisp-af_unix is not a valid ELF\n");
        return 1;
    }
    if (hdr[4] != 2) { /* EI_CLASS 2 = 64-bit */
        fprintf(stderr, "audispd consumer test FAILED: "
                        "audisp-af_unix is not 64-bit ELF\n");
        return 1;
    }
    printf("audispd 4.1.4 consumer test OK (valid ELF audisp-af_unix)\n");
    return 0;
}
