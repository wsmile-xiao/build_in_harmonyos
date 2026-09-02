// HarmonyOS 专项测试 — tsl-hat-trie 0.6.0
// 覆盖实际消费入口：htrie_map/htrie_set 在 OHOS aarch64 工具链上的
// 插入、查找、前缀搜索、前缀删除与序列化（真实调用被测包 API，非空壳）。
#include <tsl/htrie_map.h>
#include <tsl/htrie_set.h>

#include <cstdio>
#include <cstring>
#include <string>

static int g_fail = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { std::printf("FAIL: %s\n", (msg)); ++g_fail; } \
    else { std::printf("PASS: %s\n", (msg)); } \
} while (0)

// Serializer/Deserializer 必须是命名空间作用域类型（局部类不能含模板成员）
struct MemSerializer {
    char* buf;
    std::size_t pos = 0;
    template<typename U> void operator()(const U& v) {
        std::memcpy(buf + pos, &v, sizeof(U));
        pos += sizeof(U);
    }
    void operator()(const char* p, std::size_t n) {
        std::memcpy(buf + pos, p, n);
        pos += n;
    }
};

struct MemDeserializer {
    const char* buf;
    std::size_t pos = 0;
    template<typename U> U operator()() {
        U v;
        std::memcpy(&v, buf + pos, sizeof(U));
        pos += sizeof(U);
        return v;
    }
    void operator()(char* out, std::size_t n) {
        std::memcpy(out, buf + pos, n);
        pos += n;
    }
};

int main() {
    // --- htrie_map 消费入口 ---
    tsl::htrie_map<char, int> map;
    map["openharmony"] = 1;
    map["ohos"] = 2;
    map["opencl"] = 3;

    CHECK(map.size() == 3, "htrie_map size == 3");
    CHECK(map.at("ohos") == 2, "htrie_map at(ohos) == 2");
    CHECK(map.count("openharmony") == 1, "htrie_map count(openharmony) == 1");
    CHECK(map.count("missing") == 0, "htrie_map count(missing) == 0");

    // 前缀搜索（HarmonyOS 场景常用：包名/路由前缀索引）
    auto range = map.equal_prefix_range("open");
    int n = 0;
    for (auto it = range.first; it != range.second; ++it) {
        ++n;
        std::printf("  prefix[open] -> %s = %d\n", it.key().c_str(), *it);
    }
    CHECK(n == 2, "equal_prefix_range(open) 命中 2 个");

    // longest_prefix：返回 iterator，命中 != end()
    auto lp = map.longest_prefix("openharmony_com_foo");
    CHECK(lp != map.end(), "longest_prefix(openharmony_...) 命中");

    // 前缀删除
    CHECK(map.erase_prefix("open") == 2, "erase_prefix(open) 删除 2 项");
    CHECK(map.size() == 1, "erase_prefix 后 size == 1");

    // --- htrie_set 消费入口 ---
    tsl::htrie_set<char> set;
    set.insert("arm64");
    set.insert("armv8");
    set.insert("x86_64");
    CHECK(set.count("armv8") == 1, "htrie_set count(armv8) == 1");
    CHECK(set.count("armv9") == 0, "htrie_set count(armv9) == 0");

    // 序列化（serialize/deserialize）往返（serializer 为写入回调，
    // deserializer 为读出回调，deserialize 是 static 工厂返回新 map）
    {
        char buf[1024];
        MemSerializer ser{buf};
        map.serialize(ser);
        MemDeserializer des{buf};
        tsl::htrie_map<char, int> restored =
            tsl::htrie_map<char, int>::deserialize(des);
        CHECK(restored.size() == map.size(), "serialize/deserialize 往返一致");
    }

    if (g_fail == 0) {
        std::printf("OHOS special test OK: tsl-hat-trie 0.6.0 consumer API verified on OHOS aarch64\n");
        return 0;
    }
    std::printf("OHOS special test FAILURES: %d\n", g_fail);
    return 1;
}
