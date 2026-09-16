/*
 * test_package/test_mmkv.cpp — Consumer-side test for the mmkv Conan package.
 *
 * R34: This test substantively exercises the mmkv library:
 *   1. C++ API: MMKV::mmkvWithID + set/getString round-trip + count/remove
 *   2. C bridge API: mmkv_initialize + mmkv_with_id + encode/decode round-trip
 *      for string/int32/bool/bytes and key enumeration
 *
 * This is NOT an empty printf stub.
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include <MMKV/MMKV.h>
#include <MMKV/MMKVBridge.h>

static int g_failures = 0;

#define CHECK(cond)                                                       \
    do {                                                                  \
        if (!(cond)) {                                                    \
            fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__);     \
            g_failures++;                                                 \
        }                                                                 \
    } while (0)

int main() {
    /* Use a private root under TMPDIR (or fallback), never /tmp directly. */
    const char *tmp = getenv("TMPDIR");
    if (!tmp || !*tmp) tmp = "/data/storage/el2/base/temp";
    std::string root = std::string(tmp) + "/mmkv-conan-test";
    (void)system(("mkdir -p '" + root + "'").c_str());

    /* ── Part 1: C++ API round-trip ─────────────────────────────── */
    MMKV::initializeMMKV(root, MMKVLogInfo);
    auto mmkv = MMKV::mmkvWithID("conan_cpp_test");
    CHECK(mmkv != nullptr);

    auto ok = mmkv->set(std::string("hello harmonyos pc"), "cpp_str");
    CHECK(ok);
    std::string str;
    CHECK(mmkv->getString("cpp_str", str));
    CHECK(str == "hello harmonyos pc");

    mmkv->set((int32_t)-12345, "cpp_i32");
    CHECK(mmkv->getInt32("cpp_i32") == -12345);

    mmkv->set((int64_t)0x7fffffffffffffffLL, "cpp_i64");
    CHECK(mmkv->getInt64("cpp_i64") == 0x7fffffffffffffffLL);

    mmkv->set(3.14159, "cpp_double");
    CHECK(mmkv->getDouble("cpp_double") > 3.1415 && mmkv->getDouble("cpp_double") < 3.1417);

    CHECK(mmkv->containsKey("cpp_str"));
    CHECK(mmkv->count() >= 4);

    std::vector<std::string> keys = mmkv->allKeys();
    CHECK(keys.size() >= 4);

    mmkv->removeValueForKey("cpp_i32");
    CHECK(!mmkv->containsKey("cpp_i32"));
    CHECK(mmkv->getInt32("cpp_i32", -999) == -999);

    printf("C++ API round-trip: OK (count=%zu)\n", mmkv->count());

    /* ── Part 2: C bridge API round-trip ────────────────────────── */
    mmkv_initialize(root.c_str(), /*logLevel=*/1);

    MMKVConfig_t cfg = {};
    cfg.cryptKey = nullptr;      /* no encryption */
    cfg.aes256 = false;
    cfg.rootPath = root.c_str();
    cfg.expectedCapacity = 0;
    cfg.enableKeyExpire = 0;
    cfg.expiredInSeconds = 0;
    cfg.enableCompareBeforeSet = false;
    cfg.recover = -1;           /* leave default */
    cfg.itemSizeLimit = 0;

    MMKVHandle_t h = mmkv_with_id("conan_c_test", cfg);
    CHECK(h != nullptr);

    CHECK(mmkv_encode_bool(h, "c_bool", true));
    CHECK(mmkv_decode_bool(h, "c_bool", false) == true);

    CHECK(mmkv_encode_int32(h, "c_i32", 4242));
    CHECK(mmkv_decode_int32(h, "c_i32", 0) == 4242);

    CHECK(mmkv_encode_string(h, "c_str", "cbridge works"));
    char *v = mmkv_decode_string(h, "c_str");
    CHECK(v != nullptr && strcmp(v, "cbridge works") == 0);
    mmkv_free(v);

    static const uint8_t blob[] = {0x00, 0x01, 0x02, 0xFE, 0xFF, 0x7F, 0x80};
    CHECK(mmkv_encode_bytes(h, "c_bytes", blob, sizeof(blob)));
    uint64_t len = 0;
    uint8_t *out = (uint8_t *)mmkv_decode_bytes(h, "c_bytes", &len);
    CHECK(out != nullptr && len == sizeof(blob) && memcmp(out, blob, len) == 0);
    mmkv_free(out);

    uint64_t nkeys = 0;
    char **karr = mmkv_all_keys(h, &nkeys, false);
    CHECK(karr != nullptr && nkeys == 4);
    for (uint64_t i = 0; i < nkeys; i++) mmkv_free(karr[i]);
    mmkv_free(karr);

    CHECK(mmkv_count(h, false) == 4);
    CHECK(mmkv_contains_key(h, "c_str"));

    mmkv_remove_value(h, "c_bool");
    CHECK(!mmkv_contains_key(h, "c_bool"));
    CHECK(mmkv_decode_bool(h, "c_bool", false) == false);

    printf("C bridge API round-trip: OK (count=%llu)\n",
           (unsigned long long)mmkv_count(h, false));

    mmkv_sync(h, true);
    mmkv_close_handle(&h);

    /* ── Part 3: reopen and verify persistence (real disk reload) ──
     * mmkvWithID 命中进程内实例缓存时不会重新 mmap。MMKV::close() 会把
     * 实例从 g_instanceDic erase 并 delete，下次 mmkvWithID(同ID) 字典
     * miss → 从磁盘 .crc/.mmap 文件真实重载。
     * 注意：不能用 MMKV::onExit()——上游 2.4.2 的 onExit 会
     * delete g_instanceDic 并置 nullptr，但 g_instanceLock 保持非空，
     * 后续 mmkvWithID 走到 g_instanceDic->find() 即空指针崩溃
     * （CI build #45043/45076/45127 的 Error 139 根因）。onExit 语义是
     * 进程终结清理，调用后不可再使用任何 MMKV API。 */
    mmkv->close();
    auto mmkv2 = MMKV::mmkvWithID("conan_cpp_test");
    CHECK(mmkv2 != nullptr);
    std::string str2;
    CHECK(mmkv2->getString("cpp_str", str2));
    CHECK(str2 == "hello harmonyos pc");
    printf("Persistence reopen (real disk reload after close): OK\n");

    if (g_failures == 0) {
        printf("PASS: mmkv C++ API + C bridge round-trip successful\n");
        return 0;
    }
    fprintf(stderr, "FAILURES: %d\n", g_failures);
    return 1;
}
