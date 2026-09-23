/* 消费者测试：真实调用 c-siphash API，断言 SipHash 论文参考向量。
 * https://131002.net/siphash/siphash.pdf, Appendix A
 */
#include <stdint.h>
#include <c-siphash.h>

int main(void) {
    const uint8_t in[15] = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                            0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e};
    const uint8_t key[16] = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                             0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f};

    /* one-shot API：c_siphash_hash 必须复现论文参考值 */
    uint64_t out = c_siphash_hash(key, in, sizeof(in));
    if (out != 0xa129ca6149be45e5ULL) {
        return 1;
    }

    /* 流式 API：任意分块累计的结果必须与 one-shot 一致 */
    CSipHash state = C_SIPHASH_NULL;
    c_siphash_init(&state, key);
    c_siphash_append(&state, in, 7);
    c_siphash_append(&state, in + 7, 5);
    c_siphash_append(&state, in + 12, 3);
    if (c_siphash_finalize(&state) != out) {
        return 2;
    }

    return 0;
}
