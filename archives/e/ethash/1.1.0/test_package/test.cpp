#include <ethash/ethash.h>
#include <ethash/keccak.h>
#include <ethash/version.h>

#include <cstdio>
#include <cstring>

static bool bytes_eq(const uint8_t* a, const uint8_t* b, size_t n) noexcept
{
    return std::memcmp(a, b, n) == 0;
}

static void print_hash(const char* label, const union ethash_hash256* h) noexcept
{
    std::printf("  %s: ", label);
    for (int i = 0; i < 32; ++i)
        std::printf("%02x", h->bytes[i]);
    std::printf("\n");
}

int main() noexcept
{
    int failures = 0;

    /* 1. 版本宏 */
    if (std::strcmp(ETHASH_VERSION, "1.1.0") != 0)
    {
        std::printf("FAIL: ETHASH_VERSION=%s expected 1.1.0\n", ETHASH_VERSION);
        return 1;
    }

    /* 2. keccak256 已知向量：空串 */
    {
        const uint8_t empty[] = "";
        union ethash_hash256 expected{};
        const uint8_t exp_bytes[32] = {
            0xc5, 0xd2, 0x46, 0x01, 0x86, 0xf7, 0x23, 0x3c,
            0x92, 0x7e, 0x7d, 0xb2, 0xdc, 0xc7, 0x03, 0xc0,
            0xe5, 0x00, 0xb6, 0x53, 0xca, 0x82, 0x27, 0x3b,
            0x7b, 0xfa, 0xd8, 0x04, 0x5d, 0x85, 0xa4, 0x70,
        };
        std::memcpy(expected.bytes, exp_bytes, 32);
        union ethash_hash256 got = ethash_keccak256(empty, 0);
        print_hash("keccak256(\"\")", &got);
        if (!bytes_eq(got.bytes, expected.bytes, 32))
        {
            std::printf("FAIL: keccak256 empty vector mismatch\n");
            ++failures;
        }
    }

    /* 3. seed / cache item 计数（公开纯函数） */
    {
        union ethash_hash256 seed0 = ethash_calculate_epoch_seed(0);
        int items = ethash_calculate_light_cache_num_items(0);
        print_hash("epoch(0) seed", &seed0);
        if (seed0.word64s[0] != 0 || seed0.word64s[1] != 0 ||
            seed0.word64s[2] != 0 || seed0.word64s[3] != 0)
        {
            std::printf("FAIL: epoch 0 seed must be zero\n");
            ++failures;
        }
        if (items <= 0)
        {
            std::printf("FAIL: light cache items(epoch 0)=%d\n", items);
            ++failures;
        }
    }

    /* 4. 完整 Ethash 哈希链路（轻量 context，约 16MB 缓存） */
    {
        struct ethash_epoch_context* ctx = ethash_create_epoch_context(0);
        if (!ctx)
        {
            std::printf("FAIL: ethash_create_epoch_context(0) returned NULL\n");
            return 1;
        }
        union ethash_hash256 header{};
        header.bytes[0] = 0x11;
        header.bytes[31] = 0x77;
        struct ethash_result r = ethash_hash(ctx, &header, 0);

        print_hash("ethash_hash final_hash", &r.final_hash);
        int nonzero = 0;
        for (int i = 0; i < 32; ++i)
        {
            if (r.final_hash.bytes[i] != 0)
            {
                nonzero = 1;
                break;
            }
        }
        if (!nonzero)
        {
            std::printf("FAIL: final_hash is all zeros\n");
            ++failures;
        }

        /* 5. 边界校验：boundary=2^256（最大）应通过，并复算 mix_hash 一致性 */
        union ethash_hash256 boundary{};
        std::memset(boundary.bytes, 0xff, 32);
        ethash_errc err = ethash_verify_against_boundary(
            ctx, &header, &r.mix_hash, 0, &boundary);
        if (err != ETHASH_SUCCESS)
        {
            std::printf("FAIL: verify against max boundary error=%d\n", (int)err);
            ++failures;
        }
        ethash_destroy_epoch_context(ctx);
    }

    if (failures == 0)
    {
        std::printf("test ethash %s: OK (all 4 checks passed)\n", ETHASH_VERSION);
        return 0;
    }
    std::printf("test ethash %s: FAIL (%d checks failed)\n", ETHASH_VERSION, failures);
    return 1;
}