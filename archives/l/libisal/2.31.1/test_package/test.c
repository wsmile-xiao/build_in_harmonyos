/*
 * test_package/test.c — libisal 2.31.1 consumer test.
 *
 * Known-answer CRC values were derived independently from the reference
 * tables shipped in the upstream sources (crc/crc_base.c,
 * crc/crc64_base.c: identical table-driven algorithms re-implemented and
 * executed in Python) and cross-checked against public catalogue values
 * where they exist: CRC-32/BZIP2 = 0xFC891918, zlib CRC-32 = 0xCBF43926,
 * Adler-32("Wikipedia") = 0x11E60398.
 *
 * crc32_iscsi keeps the historical Intel calling convention (buf, len,
 * init) and returns the raw (non-inverted) reflected CRC-32C-style value
 * of the upstream reference table, hence 0x58E3FA20 with init 0.
 */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <isa-l/crc.h>
#include <isa-l/crc64.h>
#include <isa-l/igzip_lib.h>
#include <isa-l/raid.h>
#include <isa-l/erasure_code.h>

static int failures = 0;

#define CHECK(desc, cond) do {                                    \
        if (cond) { printf("PASS: %s\n", desc); }                 \
        else      { printf("FAIL: %s\n", desc); failures++; }     \
} while (0)

/* Bitwise GF(2^8) multiply mod 0x11d — reference for gf_vect_mul. */
static unsigned char gf_ref_mul(unsigned char a, unsigned char b)
{
    unsigned char p = 0;
    while (b) {
        if (b & 1)
            p ^= a;
        a = (a & 0x80) ? (unsigned char)((a << 1) ^ 0x1d) : (unsigned char)(a << 1);
        b >>= 1;
    }
    return p;
}

int main(void)
{
    static const unsigned char vec9[] = "123456789";
    int rc;
    int i;

    /* ---------- CRC known-answer checks (runtime-dispatched API) ------ */
    CHECK("crc16_t10dif(\"123456789\",init 0) == 0xD0DB",
          crc16_t10dif(0, vec9, 9) == 0xD0DB);
    CHECK("crc32_ieee(\"123456789\",init 0) == 0xFC891918 (CRC-32/BZIP2)",
          crc32_ieee(0, vec9, 9) == 0xFC891918U);
    CHECK("crc32_gzip_refl(\"123456789\",init 0) == 0xCBF43926 (zlib)",
          crc32_gzip_refl(0, vec9, 9) == 0xCBF43926U);
    CHECK("crc32_iscsi(\"123456789\",init 0) == 0x58E3FA20",
          crc32_iscsi((unsigned char *)vec9, 9, 0) == 0x58E3FA20U);
    CHECK("crc64_ecma_norm(\"123456789\",init 0) == 0x62EC59E3F1A4F00A",
          crc64_ecma_norm(0, vec9, 9) == 0x62EC59E3F1A4F00AULL);
    CHECK("crc64_jones_norm(\"123456789\",init 0) == 0xDCF90FB7D3A994F3",
          crc64_jones_norm(0, vec9, 9) == 0xDCF90FB7D3A994F3ULL);

    CHECK("isal_adler32(\"Wikipedia\",init 1) == 0x11E60398",
          isal_adler32(1, (const unsigned char *)"Wikipedia", 9) == 0x11E60398U);

    /* ---------- igzip stateless round-trip over 64 KiB ---------------- */
    {
        enum { N = 64 * 1024 };
        unsigned char *in = malloc(N);
        unsigned char *comp = malloc(N + N / 16 + 64);
        unsigned char *back = malloc(N);
        struct isal_zstream stream;
        struct inflate_state state;
        uint32_t seed = 0x12345678;
        unsigned char pattern[251];

        if (!in || !comp || !back) {
            printf("FAIL: igzip buffers allocated\n");
            failures++;
            free(in); free(comp); free(back);
            return 1;
        }
        for (i = 0; i < 251; i++) {           /* pseudo-random pattern */
            seed = seed * 1103515245u + 12345u;
            pattern[i] = (unsigned char)(seed >> 16);
        }
        for (i = 0; i < N; i++)               /* highly compressible data */
            in[i] = pattern[i % 251];

        memset(&stream, 0, sizeof(stream));
        isal_deflate_stateless_init(&stream);
        stream.end_of_stream = 1;
        stream.flush = NO_FLUSH;
        stream.level = 1;                     /* level 1 needs no level_buf */
        stream.next_in = in;
        stream.avail_in = N;
        stream.next_out = comp;
        stream.avail_out = N + N / 16 + 64;
        rc = isal_deflate_stateless(&stream);
        CHECK("isal_deflate_stateless returns COMP_OK", rc == COMP_OK);
        CHECK("compressed output smaller than input",
              stream.total_out > 0 && stream.total_out < N);

        memset(&state, 0, sizeof(state));
        isal_inflate_init(&state);
        state.next_in = comp;
        state.avail_in = stream.total_out;
        state.next_out = back;
        state.avail_out = N;
        rc = isal_inflate(&state);
        CHECK("isal_inflate returns ISAL_DECOMP_OK", rc == ISAL_DECOMP_OK);
        CHECK("decompressed length matches input", state.total_out == N);
        CHECK("round-trip bytes identical", memcmp(in, back, N) == 0);
        CHECK("adler32(decompressed) == adler32(original)",
              isal_adler32(1, in, N) == isal_adler32(1, back, N));

        free(in); free(comp); free(back);
    }

    /* ---------- raid xor_gen: sources XORed into last vector --------- */
    {
        static unsigned char a[4096] __attribute__((aligned(32)));
        static unsigned char b[4096] __attribute__((aligned(32)));
        static unsigned char x[4096] __attribute__((aligned(32)));
        unsigned char ok = 1;
        uint32_t seed = 0xC0FFEE;
        void *vects[3] = {a, b, x};

        for (i = 0; i < 4096; i++) {
            seed = seed * 1103515245u + 12345u;
            a[i] = (unsigned char)(seed >> 16);
            seed = seed * 1103515245u + 12345u;
            b[i] = (unsigned char)(seed >> 24);
        }
        rc = xor_gen(3, 4096, vects);
        for (i = 0; i < 4096; i++)
            if (x[i] != (unsigned char)(a[i] ^ b[i]))
                ok = 0;
        CHECK("raid xor_gen(3 x 4096B) parity correct", rc == 0 && ok);
    }

    /* ---------- erasure_code gf_vect_mul vs bitwise reference --------- */
    {
        unsigned char src[64], dst[64], gftbl[64];
        const unsigned char coef = 0x53;
        unsigned char ok = 1;
        uint32_t seed = 0xBEEF;

        for (i = 0; i < 64; i++) {
            seed = seed * 1103515245u + 12345u;
            src[i] = (unsigned char)(seed >> 16);
        }
        gf_vect_mul_init(coef, gftbl);
        rc = gf_vect_mul(64, gftbl, src, dst);
        for (i = 0; i < 64; i++)
            if (dst[i] != gf_ref_mul(coef, src[i]))
                ok = 0;
        CHECK("erasure_code gf_vect_mul(0x53) matches GF(2^8) reference",
              rc == 0 && ok);
    }

    /* ---------- 消费者用例 1: 产出标准 gzip 流并与本库解压器互通 -------
     * 场景：消费方用 igzip 把数据压成 gzip 归档（gzip_flag=IGZIP_GZIP 写入
     * 标准 magic+trailer），产物可被任何 gzip 生态工具消费；此处验证
     * magic 字节、trailer 中的 CRC32 与长度字段（RFC 1952），再用
     * isal_inflate(ISAL_GZIP) 解回并比对。 */
    {
        enum { N = 32 * 1024 };
        unsigned char *in = malloc(N);
        unsigned char *gz = malloc(N + N / 16 + 64);
        unsigned char *back = malloc(N);
        struct isal_zstream stream;
        struct inflate_state state;
        uint32_t seed = 0x5EED;

        if (!in || !gz || !back) {
            printf("FAIL: gzip consumer buffers allocated\n");
            failures++;
            free(in); free(gz); free(back);
            return 1;
        }
        for (i = 0; i < N; i++) {           /* 混合可压缩内容 */
            seed = seed * 1103515245u + 12345u;
            in[i] = (unsigned char)((seed >> 16) & 0x07);
        }
        for (i = 0; i < N; i += 997)
            in[i] ^= 0xA5;

        memset(&stream, 0, sizeof(stream));
        isal_deflate_stateless_init(&stream);
        stream.end_of_stream = 1;
        stream.flush = NO_FLUSH;
        stream.level = 1;
        stream.gzip_flag = IGZIP_GZIP;      /* 完整 gzip header+trailer */
        stream.next_in = in;
        stream.avail_in = N;
        stream.next_out = gz;
        stream.avail_out = N + N / 16 + 64;
        rc = isal_deflate_stateless(&stream);
        CHECK("consumer: gzip stream produced (COMP_OK)",
              rc == COMP_OK && stream.total_out >= 18);

        /* RFC 1952: magic 1f 8b, deflate method 08 */
        CHECK("consumer: gzip magic bytes 1f 8b 08",
              gz[0] == 0x1f && gz[1] == 0x8b && gz[2] == 0x08);

        /* trailer: CRC32(未压缩数据) + ISIZE，小端 */
        {
            uint32_t trailer_crc, trailer_len, expect_crc;
            memcpy(&trailer_crc, gz + stream.total_out - 8, 4);
            memcpy(&trailer_len, gz + stream.total_out - 4, 4);
            expect_crc = crc32_gzip_refl(0, in, N);
            CHECK("consumer: gzip trailer CRC32 matches crc32_gzip_refl",
                  trailer_crc == expect_crc);
            CHECK("consumer: gzip trailer ISIZE matches input length",
                  trailer_len == N);
        }

        memset(&state, 0, sizeof(state));
        isal_inflate_init(&state);
        state.crc_flag = ISAL_GZIP;         /* 输入含完整 gzip 包装 */
        state.next_in = gz;
        state.avail_in = stream.total_out;
        state.next_out = back;
        state.avail_out = N;
        rc = isal_inflate(&state);
        CHECK("consumer: isal_inflate(ISAL_GZIP) round-trip identical",
              rc == ISAL_DECOMP_OK && state.total_out == N &&
              memcmp(in, back, N) == 0);

        free(in); free(gz); free(back);
    }

    /* ---------- 消费者用例 2: crc16_t10dif_copy 缝合函数（存储 DIF）------
     * 场景：存储栈在搬运数据的同时计算 T10 CRC（读路径校验/写路径 DIF），
     * 一趟完成 copy+CRC；验证 dst 与 src 一致且 CRC 与 crc16_t10dif 相等。 */
    {
        enum { M = 4096 };
        static unsigned char src[M], dst[M];
        uint32_t seed = 0xD1F;
        uint16_t c_stitch, c_plain;

        for (i = 0; i < M; i++) {
            seed = seed * 1103515245u + 12345u;
            src[i] = (unsigned char)(seed >> 16);
        }
        memset(dst, 0, sizeof(dst));
        c_stitch = crc16_t10dif_copy(0, dst, src, M);
        c_plain = crc16_t10dif(0, src, M);
        CHECK("consumer: crc16_t10dif_copy copies the buffer",
              memcmp(dst, src, M) == 0);
        CHECK("consumer: crc16_t10dif_copy CRC equals crc16_t10dif",
              c_stitch == c_plain);
    }

    if (failures) {
        printf("libisal test: %d FAILURE(S)\n", failures);
        return 1;
    }
    printf("libisal test: all checks passed\n");
    return 0;
}
