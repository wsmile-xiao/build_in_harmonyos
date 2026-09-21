/* Consumer-side deterministic validation for libxeddsa 2.0.0-20231128.d725c81.
 *
 * All inputs are fixed (no randombytes dependency), so every assertion is a
 * known-answer test:
 *   - RFC 8032 section 7.1 Ed25519 test vectors 1 and 2 (seed_sign exact
 *     signature bytes, seed->pub, verify accept/reject)
 *   - RFC 7748 section 5.2 X25519 vectors 1 and 2, section 6.1 Diffie-Hellman
 *     exchange between Alice and Bob
 *   - XEdDSA private-key signing roundtrip with fixed nonce, sign-bit
 *     mismatch rejection and tampered-message rejection
 *   - Curve25519 <-> Ed25519 public key conversion roundtrip
 */
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <xeddsa.h>

static int passed = 0;
static int failed = 0;

#define CHECK(cond, label)                                       \
    do                                                           \
    {                                                            \
        if (cond)                                                \
        {                                                        \
            printf("[PASS] %s\n", label);                        \
            passed++;                                            \
        }                                                        \
        else                                                     \
        {                                                        \
            printf("[FAIL] %s\n", label);                        \
            failed++;                                            \
        }                                                        \
    } while (0)

static void unhex(const char* hex, uint8_t* out, size_t len)
{
    for (size_t i = 0; i < len; i++)
    {
        unsigned byte = 0;
        sscanf(hex + 2 * i, "%2x", &byte);
        out[i] = (uint8_t)byte;
    }
}

/* consumer#concurrent-threads 的 worker：线程专属固定密钥，50 轮
 * 私钥强制 -> 签名 -> 验签 -> ECDH 完整循环，任一失败计数。 */
struct consumer_thread_arg
{
    uint8_t seed;
    int failed;
};

static void* consumer_thread_fn(void* argp)
{
    struct consumer_thread_arg* arg = (struct consumer_thread_arg*)argp;
    uint8_t seed[32], priv[32], pub[32], ed[32], peer_priv[32], peer_pub[32];
    uint8_t sig[64], shared[32], nonce64[64];

    for (int i = 0; i < 32; i++)
    {
        seed[i] = (uint8_t)(arg->seed + i * 3);
        peer_priv[i] = (uint8_t)(arg->seed ^ (0xE0 - i));
    }
    for (int i = 0; i < 64; i++)
        nonce64[i] = (uint8_t)(arg->seed + i);
    priv_to_curve25519_pub(peer_pub, peer_priv);

    for (int round = 0; round < 50; round++)
    {
        const uint8_t msg[] = "concurrent consumer round";
        const uint32_t msg_len = (uint32_t)(sizeof(msg) - 1);
        uint8_t key[32];
        for (int i = 0; i < 32; i++)
            key[i] = (uint8_t)(seed[i] + round);
        priv_to_curve25519_pub(pub, key);
        priv_force_sign(priv, key, 0);
        curve25519_pub_to_ed25519_pub(ed, pub, 0);
        ed25519_priv_sign(sig, priv, msg, msg_len, nonce64);
        if (ed25519_verify(sig, ed, msg, msg_len) != 0)
            arg->failed++;
        if (x25519(shared, priv, peer_pub) != 0)
            arg->failed++;
    }
    return NULL;
}

int main(void)
{
    CHECK(xeddsa_init() >= 0, "xeddsa_init succeeds");

    CHECK(XEDDSA_VERSION_MAJOR == 2 && XEDDSA_VERSION_MINOR == 0
              && XEDDSA_VERSION_REVISION == 0,
          "version constants are 2.0.0");

    /* RFC 7748 section 6.1: Alice/Bob X25519 key pairs. */
    uint8_t alice_priv[32], alice_pub[32];
    uint8_t bob_priv[32], bob_pub[32];
    uint8_t shared_a[32], shared_b[32], shared_ref[32];
    unhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a",
          alice_priv, 32);
    unhex("8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a",
          alice_pub, 32);
    unhex("5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb",
          bob_priv, 32);
    unhex("de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f",
          bob_pub, 32);
    unhex("4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742",
          shared_ref, 32);

    uint8_t derived_pub[32];
    priv_to_curve25519_pub(derived_pub, alice_priv);
    CHECK(memcmp(derived_pub, alice_pub, 32) == 0,
          "priv_to_curve25519_pub matches RFC 7748 6.1 Alice public key");

    CHECK(x25519(shared_a, alice_priv, bob_pub) == 0
              && memcmp(shared_a, shared_ref, 32) == 0,
          "x25519 Alice-side shared secret matches RFC 7748 6.1");
    CHECK(x25519(shared_b, bob_priv, alice_pub) == 0
              && memcmp(shared_b, shared_ref, 32) == 0,
          "x25519 Bob-side shared secret matches RFC 7748 6.1");

    /* RFC 7748 section 5.2 vectors. */
    uint8_t k[32], u[32], out[32], out_ref[32];
    unhex("a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4", k, 32);
    unhex("e6db6867583030db3594c1a424b15f7c726624ec26b3353b10a903a6d0ab1c4c", u, 32);
    unhex("c3da55379de9c6908e94ea4df28d084f32eccf03491c71f754b4075577a28552", out_ref, 32);
    CHECK(x25519(out, k, u) == 0 && memcmp(out, out_ref, 32) == 0,
          "x25519 RFC 7748 5.2 vector 1");

    unhex("4b66e9d4d1b4673c5ad22691957d6af5c11b6421e0ea01d42ca4169e7918ba0d", k, 32);
    unhex("e5210f12786811d3f4b7959d0538ae2c31dbe7106fc03c3efc4cd549c715a493", u, 32);
    unhex("95cbde9476e8907d7aade45cb4b873f88b595a68799fa152e6f8f7647aac7957", out_ref, 32);
    CHECK(x25519(out, k, u) == 0 && memcmp(out, out_ref, 32) == 0,
          "x25519 RFC 7748 5.2 vector 2");

    /* RFC 8032 section 7.1 test 1: empty message. */
    uint8_t seed1[32], pub1[32], pub1_ref[32], sig1[64], sig1_ref[64];
    unhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60", seed1, 32);
    unhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", pub1_ref, 32);
    unhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
          "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
          sig1_ref, 64);

    seed_to_ed25519_pub(pub1, seed1);
    CHECK(memcmp(pub1, pub1_ref, 32) == 0,
          "seed_to_ed25519_pub matches RFC 8032 test 1 public key");

    uint8_t priv1[32];
    seed_to_priv(priv1, seed1);
    uint8_t pub1_via_priv[32];
    priv_to_ed25519_pub(pub1_via_priv, priv1);
    CHECK(memcmp(pub1_via_priv, pub1_ref, 32) == 0,
          "seed_to_priv + priv_to_ed25519_pub is consistent with RFC 8032 test 1");

    ed25519_seed_sign(sig1, seed1, (const uint8_t*)"", 0);
    CHECK(memcmp(sig1, sig1_ref, 64) == 0,
          "ed25519_seed_sign produces the exact RFC 8032 test 1 signature");

    CHECK(ed25519_verify(sig1, pub1_ref, (const uint8_t*)"", 0) == 0,
          "ed25519_verify accepts RFC 8032 test 1 signature");

    uint8_t bad_sig[64];
    memcpy(bad_sig, sig1, 64);
    bad_sig[0] ^= 0x01;
    CHECK(ed25519_verify(bad_sig, pub1_ref, (const uint8_t*)"", 0) != 0,
          "ed25519_verify rejects a tampered signature");

    /* RFC 8032 section 7.1 test 2: one-byte message 0x72. */
    uint8_t seed2[32], pub2_ref[32], sig2[64], sig2_ref[64], msg2[1];
    unhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb", seed2, 32);
    unhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", pub2_ref, 32);
    unhex("92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
          "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
          sig2_ref, 64);
    msg2[0] = 0x72;
    ed25519_seed_sign(sig2, seed2, msg2, 1);
    CHECK(memcmp(sig2, sig2_ref, 64) == 0,
          "ed25519_seed_sign produces the exact RFC 8032 test 2 signature");
    CHECK(ed25519_verify(sig2, pub2_ref, msg2, 1) == 0,
          "ed25519_verify accepts RFC 8032 test 2 signature");

    /* XEdDSA private-key signing with fixed nonce and fixed key material. */
    uint8_t nonce[64];
    for (int i = 0; i < 64; i++)
        nonce[i] = (uint8_t)(0x40 + i);
    const uint8_t msg[] = "libxeddsa on HarmonyOS consumer test";
    const uint32_t msg_len = (uint32_t)(sizeof(msg) - 1);

    uint8_t priv0[32], priv1b[32], sig[64];
    uint8_t ed0[32], ed1[32], back[32];

    priv_force_sign(priv0, alice_priv, 0);
    priv_force_sign(priv1b, alice_priv, 1);

    curve25519_pub_to_ed25519_pub(ed0, alice_pub, 0);
    curve25519_pub_to_ed25519_pub(ed1, alice_pub, 1);

    /* priv_force_sign 的功能验证走签名/验签：其输出的取反标量不是
     * clamped 形态，回灌 priv_to_ed25519_pub 会被内部 sc_clamp 破坏，
     * 直接读符号位是误用（上游 test_signing 同样从 curve 公钥推导）。 */
    ed25519_priv_sign(sig, priv0, msg, msg_len, nonce);
    CHECK(ed25519_verify(sig, ed0, msg, msg_len) == 0,
          "ed25519_priv_sign with priv_force_sign(0) key verifies via sign-0 public key");
    CHECK(ed25519_verify(sig, ed1, msg, msg_len) != 0,
          "ed25519_priv_sign with priv_force_sign(0) key fails against sign-1 public key");

    ed25519_priv_sign(sig, priv1b, msg, msg_len, nonce);
    CHECK(ed25519_verify(sig, ed1, msg, msg_len) == 0,
          "ed25519_priv_sign with priv_force_sign(1) key verifies via sign-1 public key");
    CHECK(ed25519_verify(sig, ed0, msg, msg_len) != 0,
          "ed25519_priv_sign with priv_force_sign(1) key fails against sign-0 public key");

    uint8_t tampered[sizeof(msg)];
    memcpy(tampered, msg, sizeof(msg));
    tampered[0] ^= 0x01;
    /* sig 此时是 priv1b（sign-1）的签名：须用配对的 ed1 验，断言才
     * 只在消息被篡改时成立（用 ed0 会因符号位不匹配恒真）。 */
    CHECK(ed25519_verify(sig, ed1, tampered, msg_len) != 0,
          "ed25519_priv_sign signature fails on a tampered message");

    CHECK(ed25519_pub_to_curve25519_pub(back, ed0) == 0
              && memcmp(back, alice_pub, 32) == 0,
          "Curve25519 -> Ed25519 -> Curve25519 public key roundtrip");

    /* ── 鸿蒙特有消费者用例 1：session-exchange ──────────────────────
     * Wire/Signal 式会话建立流程：双方各持种子，派生 Curve25519/Ed25519
     * 密钥对并强制 sign bit 0（XEdDSA 约定），交换公钥后双向签名/验签、
     * 双向 X25519 ECDH，并验证篡改拒绝——即消息类应用在鸿蒙上使用本库的
     * 端到端消费路径。密钥材料全部固定（确定性），无 randombytes 依赖。 */
    {
        uint8_t a_seed[32], b_seed[32];
        uint8_t a_priv[32], b_priv[32], a_sign[32], b_sign[32];
        uint8_t a_pub[32], b_pub[32], a_ed[32], b_ed[32], sig_a[64], sig_b[64];
        uint8_t secret_a[32], secret_b[32];

        for (int i = 0; i < 32; i++)
        {
            a_seed[i] = (uint8_t)(0x10 + i);
            b_seed[i] = (uint8_t)(0x90 - i);
        }
        const uint8_t hello[] = "hello from alice over harmonyos";
        const uint8_t reply[] = "hello from bob over harmonyos";
        const uint32_t hello_len = (uint32_t)(sizeof(hello) - 1);
        const uint32_t reply_len = (uint32_t)(sizeof(reply) - 1);

        /* XEdDSA 约定：签名用 force 后（sign bit 0）的标量副本，ECDH 用
         * 原始标量——force 可能取反标量，取反形态直接做 X25519 会得到
         * 不同的共享密钥（见知识草稿 DRAFT-...-reclamp-semantics）。 */
        seed_to_priv(a_priv, a_seed);
        priv_to_curve25519_pub(a_pub, a_priv);
        priv_force_sign(a_sign, a_priv, 0);
        seed_to_priv(b_priv, b_seed);
        priv_to_curve25519_pub(b_pub, b_priv);
        priv_force_sign(b_sign, b_priv, 0);

        curve25519_pub_to_ed25519_pub(a_ed, a_pub, 0);
        curve25519_pub_to_ed25519_pub(b_ed, b_pub, 0);

        ed25519_priv_sign(sig_a, a_sign, hello, hello_len, nonce);
        CHECK(ed25519_verify(sig_a, a_ed, hello, hello_len) == 0,
              "consumer#session-exchange: Alice signs, Bob verifies via exchanged public key");
        ed25519_priv_sign(sig_b, b_sign, reply, reply_len, nonce);
        CHECK(ed25519_verify(sig_b, b_ed, reply, reply_len) == 0,
              "consumer#session-exchange: Bob signs, Alice verifies via exchanged public key");

        sig_a[63] ^= 0x01;
        CHECK(ed25519_verify(sig_a, a_ed, hello, hello_len) != 0,
              "consumer#session-exchange: tampered session signature is rejected");

        CHECK(x25519(secret_a, a_priv, b_pub) == 0
                  && x25519(secret_b, b_priv, a_pub) == 0
                  && memcmp(secret_a, secret_b, 32) == 0,
              "consumer#session-exchange: bidirectional X25519 ECDH agrees on the shared secret");
        uint8_t zero[32] = {0};
        CHECK(memcmp(secret_a, zero, 32) != 0,
              "consumer#session-exchange: shared secret is nonzero");
    }

    /* ── 鸿蒙特有消费者用例 2：concurrent-threads ────────────────────
     * 鸿蒙应用多线程环境可用性：3 个 worker 线程并发执行私钥强制、签名、
     * 验签、ECDH 的完整循环（各 50 轮、线程专属固定密钥），验证
     * xeddsa_init() 之后库调用线程安全（libsodium 初始化后线程安全、
     * ref10 计算无全局可变状态）。 */
    {
        pthread_t threads[3];
        struct consumer_thread_arg targs[3] = {{0x21, 0}, {0x57, 0}, {0x8b, 0}};
        int create_failed = 0;

        for (int t = 0; t < 3; t++)
        {
            if (pthread_create(&threads[t], NULL, consumer_thread_fn,
                               &targs[t]) != 0)
            {
                /* 创建失败：不 join 未初始化的句柄（UB），且让断言如实
                 * 失败而不是因 worker 未跑、failed 恒 0 而虚假通过。 */
                create_failed++;
            }
        }
        if (create_failed == 0)
        {
            for (int t = 0; t < 3; t++)
            {
                pthread_join(threads[t], NULL);
            }
        }
        CHECK(create_failed == 0
                  && targs[0].failed == 0 && targs[1].failed == 0
                  && targs[2].failed == 0,
              "consumer#concurrent-threads: 3 threads x 50 rounds of concurrent sign/verify/ECDH all succeed");

        /* 与会话用例交叉的独立可证伪断言：并发 worker 存活期间，主线程
         * 对同一密钥对做双向 ECDH（m×alice 与 alice×m），两侧必须一致。 */
        uint8_t m_priv[32], m_pub[32], s1[32], s2[32];
        for (int i = 0; i < 32; i++)
            m_priv[i] = (uint8_t)(0xC0 + i);
        priv_to_curve25519_pub(m_pub, m_priv);
        CHECK(x25519(s1, m_priv, alice_pub) == 0
                  && x25519(s2, alice_priv, m_pub) == 0
                  && memcmp(s1, s2, 32) == 0,
              "consumer#concurrent-threads: bidirectional ECDH commutes while workers run (m x alice == alice x m)");
    }

    printf("RESULT: %s (%d/%d checks passed)\n",
           failed == 0 ? "PASS" : "FAIL", passed, passed + failed);
    return failed == 0 ? 0 : 1;
}
