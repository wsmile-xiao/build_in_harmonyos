/* test_package/test.c — asterisk-espeak 5.0-1 consumer test (R34 合规)
 *
 * L1 test:
 * 1. 真实读取包内产物 app_espeak.so（Asterisk eSpeak 模块）；
 * 2. 校验其为有效 64 位 ELF 共享库（magic + EI_CLASS）；
 * 3. 注：不能用 dlopen 完整加载——app_espeak.so 依赖 Asterisk 运行时
 *    符号（ast_module_register 等），仅由 Asterisk 主程序提供，独立
 *    dlopen（RTLD_NOW）必然失败属预期。
 */
#include <stdio.h>

int main(void) {
    FILE *f = fopen("app_espeak.so", "rb");
    if (f == NULL) {
        fprintf(stderr, "asterisk-espeak consumer test FAILED: "
                        "cannot open app_espeak.so\n");
        return 1;
    }
    unsigned char hdr[16] = {0};
    size_t n = fread(hdr, 1, sizeof(hdr), f);
    fclose(f);
    if (n < 16 || hdr[0] != 0x7f || hdr[1] != 'E' || hdr[2] != 'L' ||
        hdr[3] != 'F') {
        fprintf(stderr, "asterisk-espeak consumer test FAILED: "
                        "app_espeak.so is not a valid ELF\n");
        return 1;
    }
    if (hdr[4] != 2) { /* EI_CLASS 2 = 64-bit */
        fprintf(stderr, "asterisk-espeak consumer test FAILED: "
                        "app_espeak.so is not 64-bit ELF\n");
        return 1;
    }
    printf("asterisk-espeak 5.0-1 consumer test OK "
           "(valid ELF app_espeak.so)\n");
    return 0;
}
