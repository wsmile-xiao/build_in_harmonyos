/* test_package for ancient 2.3.0 — 实质消费者测试
 * 调用被测包公开 API (ancient::Decompressor) 解压内嵌的 ICE 压缩样例，
 * 并对解压结果做 SHA-256 完整性校验（与官方测试向量 test_neo.raw 一致）。
 */
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <memory>
#include <vector>
#include <ancient/ancient.hpp>

#include "packed.h"

static uint32_t rot_r(uint32_t x, unsigned n) { return (x >> n) | (x << (32 - n)); }

static void sha256_block(uint32_t h[8], const uint8_t *p)
{
    static const uint32_t K[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    uint32_t w[64];
    for (int i = 0; i < 16; i++)
        w[i] = (uint32_t(p[i*4]) << 24) | (uint32_t(p[i*4+1]) << 16) | (uint32_t(p[i*4+2]) << 8) | uint32_t(p[i*4+3]);
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = rot_r(w[i-15],7) ^ rot_r(w[i-15],18) ^ (w[i-15] >> 3);
        uint32_t s1 = rot_r(w[i-2],17) ^ rot_r(w[i-2],19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    uint32_t a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],hh=h[7];
    for (int i = 0; i < 64; i++) {
        uint32_t S1 = rot_r(e,6) ^ rot_r(e,11) ^ rot_r(e,25);
        uint32_t ch = (e & f) ^ (~e & g);
        uint32_t t1 = hh + S1 + ch + K[i] + w[i];
        uint32_t S0 = rot_r(a,2) ^ rot_r(a,13) ^ rot_r(a,22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t t2 = S0 + maj;
        hh=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    h[0]+=a; h[1]+=b; h[2]+=c; h[3]+=d; h[4]+=e; h[5]+=f; h[6]+=g; h[7]+=hh;
}

static void sha256(const uint8_t *data, size_t len, uint8_t out[32])
{
    uint32_t h[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    size_t n = 0;
    uint8_t block[64];
    while (len - n >= 64) { sha256_block(h, data + n); n += 64; }
    size_t rem = len - n;
    memset(block, 0, 64);
    memcpy(block, data + n, rem);
    block[rem] = 0x80;
    if (rem >= 56) { sha256_block(h, block); memset(block, 0, 64); }
    uint64_t bits = uint64_t(len) * 8;
    for (int i = 0; i < 8; i++) block[63-i] = uint8_t(bits >> (i*8));
    sha256_block(h, block);
    for (int i = 0; i < 8; i++) {
        out[i*4]   = uint8_t(h[i] >> 24);
        out[i*4+1] = uint8_t(h[i] >> 16);
        out[i*4+2] = uint8_t(h[i] >> 8);
        out[i*4+3] = uint8_t(h[i]);
    }
}

int main()
{
    // 期望值来自官方测试向量 testing/test_files/test_neo.raw（ancient v2.3.0 tag）
    static const uint8_t expected[32] = {
        0xf7,0x85,0x27,0xe1,0xbe,0x36,0x58,0x57,0xd0,0x0c,0x36,0xd5,0xa7,0xa0,0x27,0xfa,
        0xb6,0xf2,0x2a,0x94,0xae,0x28,0x21,0x04,0x78,0xc7,0x75,0xd4,0x60,0x86,0x9f,0x15
    };
    try {
        // 公开 API: ancient::Decompressor —— 构造 + 解压 + 大小/偏移查询
        std::vector<uint8_t> packed(g_packed, g_packed + g_packed_len);
        ancient::Decompressor dec(packed, true, true);
        if (dec.getPackedSize() && *dec.getPackedSize() != g_packed_len) {
            fprintf(stderr, "FAIL: packed size mismatch\n");
            return 1;
        }
        auto raw = dec.decompress(true);
        if (raw.size() != 32128) {
            fprintf(stderr, "FAIL: decompressed size=%zu expected 32128\n", raw.size());
            return 1;
        }
        uint8_t digest[32];
        sha256(raw.data(), raw.size(), digest);
        if (memcmp(digest, expected, 32) != 0) {
            fprintf(stderr, "FAIL: decompressed SHA-256 mismatch\n");
            return 1;
        }
        printf("PASS: ancient %s decompressed 1708 -> 32128 bytes, SHA-256 verified (files match)\n",
               dec.getName().c_str());
        return 0;
    } catch (const ancient::Error &e) {
        fprintf(stderr, "FAIL: ancient::Error: %s\n", e.what());
        return 1;
    } catch (const std::exception &e) {
        fprintf(stderr, "FAIL: exception: %s\n", e.what());
        return 1;
    }
}
