// test_botan.c — 消费者用例：模拟上层组件调用 Botan 公开 API
//
// 验证：
//   1. botan/botan.h 可包含（公开头）
//   2. 链接 libbotan-2.a 成功
//   3. 调用跑通：Botan::AutoSeeded_RNG 生成随机数 +
//      Botan::SHA_256 哈希（可验证的确定结果），真实功能验证
#include <botan/botan.h>
#include <botan/hash.h>
#include <botan/hex.h>
#include <botan/rng.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    /* 断言 1：版本宏可用 */
    if (Botan::version_major() == 0 && Botan::version_minor() == 0) {
        fprintf(stderr, "FAIL: version API returned 0\n");
        return 1;
    }

    /* 断言 2：RNG 生成随机数（运行期真实调用） */
    Botan::AutoSeeded_RNG rng;
    std::vector<uint8_t> buf(32);
    rng.randomize(buf.data(), buf.size());
    bool nonzero = false;
    for (uint8_t b : buf)
        if (b != 0) { nonzero = true; break; }
    if (!nonzero) {
        fprintf(stderr, "FAIL: RNG produced all zeros\n");
        return 1;
    }

    /* 断言 3：SHA-256 哈希（可验证的确定结果） */
    std::unique_ptr<Botan::HashFunction> h(Botan::HashFunction::create("SHA-256"));
    if (!h) {
        fprintf(stderr, "FAIL: SHA-256 not available\n");
        return 1;
    }
    h->update("abc");
    /* hex_encode 第 3 参 uppercase=true：默认小写，与大写 expected 常量匹配 */
    std::string digest = Botan::hex_encode(h->final(), true);
    const char* expected = "BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD";
    if (digest != expected) {
        fprintf(stderr, "FAIL: SHA-256(abc)=%s, expected %s\n",
                digest.c_str(), expected);
        return 1;
    }

    printf("test_botan: OK (version=%d.%d.%d, SHA-256(abc) verified)\n",
           Botan::version_major(), Botan::version_minor(),
           Botan::version_patch());
    return 0;
}
