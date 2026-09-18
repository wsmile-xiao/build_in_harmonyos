/* test_package 消费者测试：通过公开头文件 fec.h 调用 libfec 公开 API
 * 验证 Reed-Solomon (255,223) 编解码往返正确性（真实可观察结果）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fec.h"

#define NN 255
#define KK 223
#define NROOTS 32

int main(void) {
    void *rs;
    unsigned char data[NN];
    unsigned char parity[NROOTS];
    int i, r;
    int errors = 0;

    rs = init_rs_char(8, 0x11d, 0, 1, NROOTS, 0);
    if (rs == NULL) {
        fprintf(stderr, "init_rs_char failed\n");
        return 1;
    }

    memset(data, 0, NN);
    for (i = 0; i < KK; i++)
        data[i] = (unsigned char)(i * 13 % 256);

    encode_rs_char(rs, data, parity);
    for (i = 0; i < NROOTS; i++)
        data[KK + i] = parity[i];

    /* 无错码字应解码为 0 个错误 */
    r = decode_rs_char(rs, data, NULL, 0);
    if (r != 0) {
        fprintf(stderr, "clean codeword decode returned %d errors\n", r);
        errors++;
    }

    /* 注入 8 个错误后应全部纠正 */
    for (i = 0; i < 8; i++)
        data[i * 3] ^= (unsigned char)(i + 1);
    r = decode_rs_char(rs, data, NULL, 0);
    if (r != 8) {
        fprintf(stderr, "decode after 8 errors returned %d (expected 8)\n", r);
        errors++;
    }

    free_rs_char(rs);

    if (errors == 0) {
        printf("libfec test_package: RS(255,223) encode/decode OK\n");
        return 0;
    }
    printf("libfec test_package: FAIL (%d checks)\n", errors);
    return 1;
}
