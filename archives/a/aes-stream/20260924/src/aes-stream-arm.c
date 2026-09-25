/* aes_stream_arm.c — aes-stream 官方 API 的 ARMv8 crypto extension 移植实现
 * 逐位镜像上游 x86 AES-NI 版构造（AES-PRF + key erasure），
 * 语义等价性由 aes_stream_oracle.c（已验证标量参考）bit-exact 对拍保证。
 * 仅面向 aarch64 OHOS（armv8-a+crypto）。
 */
#include "aes-stream.h"

#include <arm_neon.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* 内部状态：与上游 _aes_stream_state 布局一致
 * (AES_STREAM_ROUNDS+1)*16 字节轮密钥 + 16 字节 counter */
typedef struct arm_state {
    uint8_t round_keys[(AES_STREAM_ROUNDS + 1) * 16];
    uint8_t counter[16];
} arm_state;

/* ---------- FIPS-197 密钥扩展（与上游 AESKEYGENASSIST 版等价，oracle 已 KAT 验证） ---------- */
static uint8_t g_sbox[256];
static uint8_t gf_mul(uint8_t a, uint8_t b) {
    uint8_t r = 0;
    while (b) {
        if (b & 1) r ^= a;
        uint8_t hi = a & 0x80;
        a <<= 1;
        if (hi) a ^= 0x1b;
        b >>= 1;
    }
    return r;
}
static uint8_t gf_inv(uint8_t a) {
    if (a == 0) return 0;
    for (int i = 1; i < 256; i++)
        if (gf_mul(a, (uint8_t)i) == 1) return (uint8_t)i;
    return 0;
}
static void sbox_init(void) {
    if (g_sbox[1] == 0x7c) return;  /* 已初始化 */
    for (int i = 0; i < 256; i++) {
        uint8_t b = gf_inv((uint8_t)i);
        uint8_t x = (uint8_t)(b
                              ^ ((b << 1) | (b >> 7))
                              ^ ((b << 2) | (b >> 6))
                              ^ ((b << 3) | (b >> 5))
                              ^ ((b << 4) | (b >> 4)));
        g_sbox[i] = (uint8_t)(x ^ 0x63);
    }
}
static uint8_t sbox(uint8_t x) { return g_sbox[x]; }

static void expand_words(const uint8_t key[], uint8_t w[], int Nk, int Nr) {
    int i;
    for (i = 0; i < Nk; i++) {
        w[4*i+0] = key[4*i+0]; w[4*i+1] = key[4*i+1];
        w[4*i+2] = key[4*i+2]; w[4*i+3] = key[4*i+3];
    }
    static const uint8_t rcon[11] = {0,1,2,4,8,16,32,64,128,27,54};
    for (i = Nk; i < 4*(Nr+1); i++) {
        uint8_t t[4] = {w[4*(i-1)+0], w[4*(i-1)+1], w[4*(i-1)+2], w[4*(i-1)+3]};
        if (i % Nk == 0) {
            uint8_t tmp = t[0];
            t[0] = sbox(t[1]); t[1] = sbox(t[2]); t[2] = sbox(t[3]); t[3] = sbox(tmp);
            t[0] ^= rcon[i / Nk];
        } else if (Nk > 6 && i % Nk == 4) {
            t[0] = sbox(t[0]); t[1] = sbox(t[1]); t[2] = sbox(t[2]); t[3] = sbox(t[3]);
        }
        for (int b = 0; b < 4; b++)
            w[4*i+b] = w[4*(i-Nk)+b] ^ t[b];
    }
}

/* ---------- AES 轮函数（ARMv8 crypto，实证校正） ----------
 * 本平台 AESE 指令语义：先 AddRoundKey 再 SubBytes 再 ShiftRows（与 x86 相反）。
 * 标准 AES 轮（SubBytes->ShiftRows->MixColumns->AddRoundKey）只能通过
 * AESE(0 密钥) 提供 SB+SR、AESMC 提供 MC、veor 在最后加入轮密钥来精确复现：
 *   内部轮: st' = veor( AESMC( AESE(st, 0) ), rk_i )
 *   末  轮: st' = veor( AESE(st, 0), rk_Nr )
 * 已用穷举 + FIPS-197 KAT 实证（arm_brute.c：唯一命中组合）。 */
static inline uint8x16_t aes_enc_round(uint8x16_t d, const uint8_t rk[16]) {
    return veorq_u8(vaesmcq_u8(vaeseq_u8(d, vdupq_n_u8(0))), vld1q_u8(rk));
}

/* x86 AESENCLAST = SubBytes, ShiftRows, AddRoundKey */
static inline uint8x16_t aes_enc_last(uint8x16_t d, const uint8_t rk[16]) {
    return veorq_u8(vaeseq_u8(d, vdupq_n_u8(0)), vld1q_u8(rk));
}

/* ---------- 每块构造输出：s(第4轮后状态) XOR 最终密文 ---------- */
static inline void prf_block(const uint8_t *rk, const uint8_t c[16], uint8_t out[16]) {
    uint8x16_t st = veorq_u8(vld1q_u8(c), vld1q_u8(rk)); /* AddRoundKey rk0 */
    for (int round = 1; round <= 4; round++)
        st = aes_enc_round(st, rk + round * 16);
    uint8x16_t s = st;
    for (int round = 5; round < AES_STREAM_ROUNDS; round++)
        st = aes_enc_round(st, rk + round * 16);
    uint8x16_t fin = aes_enc_last(st, rk + AES_STREAM_ROUNDS * 16);
    vst1q_u8(out, veorq_u8(s, fin));
}

static void ctr_add64(uint8_t c[16], uint64_t n) {
    uint64_t lo, hi;
    memcpy(&lo, c, 8); memcpy(&hi, c + 8, 8);
    lo += n;
    memcpy(c, &lo, 8); memcpy(c + 8, &hi, 8);
}

/* ---------- 官方 API 实现 ---------- */
void
aes_stream_init(aes_stream_state *st, const unsigned char seed[AES_STREAM_SEEDBYTES])
{
    arm_state *a = (arm_state *) (void *) st;
    uint8_t w[4 * 60];
    sbox_init();
#if AES_STREAM_ROUNDS == 10
    expand_words(seed, w, 4, 10);
    memcpy(a->round_keys, w, 11 * 16);
    memcpy(a->counter, seed + 16, 16);
#elif AES_STREAM_ROUNDS == 14
    expand_words(seed, w, 8, 14);
    memcpy(a->round_keys, w, 15 * 16);
    memset(a->counter, 0, 16);
#else
#error "AES_STREAM_ROUNDS must be 10 or 14"
#endif
}

void
aes_stream(aes_stream_state *st, unsigned char *buf, size_t buf_len)
{
    arm_state *a = (arm_state *) (void *) st;
    uint8_t c[16];
    memcpy(c, a->counter, 16);
    size_t remaining = buf_len;
    uint8_t *dst = buf;

    while (remaining > 128) {
        for (int n = 0; n < 8; n++) {
            uint8_t cc[16];
            memcpy(cc, c, 16); ctr_add64(cc, (uint64_t) n);
            prf_block(a->round_keys, cc, dst + n * 16);
        }
        ctr_add64(c, 8);
        dst += 128; remaining -= 128;
    }
    while (remaining > 32) {
        for (int n = 0; n < 2; n++) {
            uint8_t cc[16];
            memcpy(cc, c, 16); ctr_add64(cc, (uint64_t) n);
            prf_block(a->round_keys, cc, dst + n * 16);
        }
        ctr_add64(c, 2);
        dst += 32; remaining -= 32;
    }
    while (remaining > 16) {
        prf_block(a->round_keys, c, dst);
        ctr_add64(c, 1);
        dst += 16; remaining -= 16;
    }
    if (remaining > 0) {
        uint8_t t[16];
        prf_block(a->round_keys, c, t);
        ctr_add64(c, 1);
        for (size_t i = 0; i < remaining; i++) dst[i] = t[i];
    }
    memcpy(a->counter, c, 16);

    /* key erasure：c ^= (1<<63)（counter 高 64 位道） */
    uint8_t ec[16];
    memcpy(ec, c, 16);
    {
        uint64_t hi;
        memcpy(&hi, ec + 8, 8);
        hi ^= (1ULL << 63);
        memcpy(ec + 8, &hi, 8);
    }
#if AES_STREAM_ROUNDS == 10
    {
        uint8_t r0[16];
        prf_block(a->round_keys, ec, r0);
        uint8_t w[4 * 44];
        expand_words(r0, w, 4, 10);
        memcpy(a->round_keys, w, 11 * 16);
    }
#elif AES_STREAM_ROUNDS == 14
    {
        uint8_t r0[16], r1[16];
        uint8_t cc[16];
        memcpy(cc, ec, 16);
        prf_block(a->round_keys, cc, r0);
        ctr_add64(cc, 1);
        prf_block(a->round_keys, cc, r1);
        uint8_t key32[32];
        memcpy(key32, r0, 16); memcpy(key32 + 16, r1, 16);
        uint8_t w[4 * 60];
        expand_words(key32, w, 8, 14);
        memcpy(a->round_keys, w, 15 * 16);
    }
#endif
}