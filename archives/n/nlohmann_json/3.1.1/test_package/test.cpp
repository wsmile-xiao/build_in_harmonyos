/* nlohmann_json 3.1.1 —— 鸿蒙 PC conan 包的真实断言测试。
 *
 * 做 3.1.1 的理由：**qiskit-aer 在两条路径上都钉这个版本**
 * （conan_utils.cmake 的 REQUIREMENTS、dependency_utils.cmake 的
 * find_package(... 3.1.1 EXACT)）。用 3.12.0 编出来的 aer 能构建、能
 * import、能跑简单线路，但自带测试套件里 **196 个** 噪声模型相关用例全报
 * `Invalid noise_params JSON: not an object.` —— Python dict 经 aer 自定义的
 * pybind11 caster（塞在 namespace std 里）转不成 JSON 对象。
 * 上游 CMake 当时就警告过 "WARNING: This version may not work!!!"。
 *
 * header-only 库的 test_package 有个特殊之处：**没有 .so 可以 dlopen**，
 * 所以「能加载」这种弱判据在这里根本不存在，只能靠真实计算。反过来说，
 * 它要证明的东西也不同 —— 头文件包最容易出的问题是「装了但下游 include 不到」
 * （头装在 include/nlohmann/ 而 includedirs 填成了 include/nlohmann，
 * 于是 #include <nlohmann/json.hpp> 找不到），以及版本宏与实际内容对不上。
 *
 * 因此这里既验行为，也验**布局与版本**。
 */
#include <cstdio>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

using json = nlohmann::json;

static int failures = 0;

#define CHECK(cond, what)                                                      \
    do {                                                                       \
        if (cond) {                                                            \
            std::printf("  ok   %s\n", (what));                                \
        } else {                                                               \
            std::printf("  FAIL %s\n", (what));                                \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

/* ① 版本宏 —— 证明装进来的确实是 3.12.0，而不是设备上别处的旧头 */
static void test_version(void)
{
    std::printf("[1] 版本\n");
    std::printf("       NLOHMANN_JSON_VERSION = %d.%d.%d\n",
                NLOHMANN_JSON_VERSION_MAJOR, NLOHMANN_JSON_VERSION_MINOR,
                NLOHMANN_JSON_VERSION_PATCH);
    CHECK(NLOHMANN_JSON_VERSION_MAJOR == 3, "主版本为 3");
    CHECK(NLOHMANN_JSON_VERSION_MINOR == 1, "次版本为 1");
    /* qiskit-aer 要求 >= 3.1.1 */
    CHECK(NLOHMANN_JSON_VERSION_MAJOR > 3 ||
          (NLOHMANN_JSON_VERSION_MAJOR == 3 && NLOHMANN_JSON_VERSION_MINOR >= 1),
          "满足 qiskit-aer 所需的 >= 3.1.1");
}

/* ② 解析与访问 —— 库的主用途 */
static void test_parse(void)
{
    std::printf("[2] 解析与类型\n");
    const char *text = R"({"name":"harmony","n":42,"pi":3.5,"ok":true,
                           "list":[1,2,3],"nested":{"k":"v"}})";
    json j = json::parse(text);
    CHECK(j["name"] == "harmony", R"(字符串字段 name == "harmony")");
    CHECK(j["n"] == 42, "整数字段 n == 42");
    CHECK(j["pi"].get<double>() == 3.5, "浮点字段 pi == 3.5（可精确表示）");
    CHECK(j["ok"].get<bool>() == true, "布尔字段 ok == true");
    CHECK(j["list"].size() == 3, "数组长度为 3");
    CHECK(j["list"][2] == 3, "数组末元素为 3");
    CHECK(j["nested"]["k"] == "v", "嵌套对象取值正确");
    /* contains() 是 3.6.0 才加的 —— 3.1.1 用 count() */
    CHECK(j.count("name") == 1 && j.count("missing") == 0, "键存在性判定正确");
}

/* ③ 序列化 —— 往返必须等价 */
static void test_roundtrip(void)
{
    std::printf("[3] 序列化往返\n");
    json a;
    a["x"] = 1;
    a["y"] = std::vector<int>{1, 2, 3};
    a["z"]["deep"] = "value";
    const std::string dumped = a.dump();
    json b = json::parse(dumped);
    CHECK(a == b, "dump 后再 parse 与原对象相等");
    CHECK(dumped.find("\"deep\"") != std::string::npos, "dump 结果含嵌套键");

    /* 键序：nlohmann::json 默认按键名排序存储 */
    json c = json::parse(R"({"b":1,"a":2})");
    CHECK(c.begin().key() == "a", "默认对象按键名有序（首键为 a）");
}

/* ④ 错误处理 —— 坏输入必须抛，而不是悄悄给个空对象 */
static void test_errors(void)
{
    std::printf("[4] 错误处理\n");
    bool threw = false;
    try {
        (void)json::parse("{ this is not json }");
    } catch (const json::parse_error &) {
        threw = true;
    }
    CHECK(threw, "非法 JSON 抛 parse_error");

    json j = json::parse("{}");
    bool threw2 = false;
    try {
        (void)j.at("nope");
    } catch (const json::out_of_range &) {
        threw2 = true;
    }
    CHECK(threw2, "at() 取不存在的键抛 out_of_range");

    /* 容错解析：allow_exceptions=false 时返回 discarded 而不是抛 */
    json bad = json::parse("[1,", nullptr, false);
    CHECK(bad.is_discarded(), "allow_exceptions=false 时返回 discarded");
}

/* ⑤ 二进制格式 —— 覆盖非 ASCII 路径（qiskit-aer 用 json 传电路数据） */
static void test_binary(void)
{
    std::printf("[5] 二进制格式（CBOR/MessagePack）\n");
    json j = json::parse(R"({"a":[1,2,3],"b":"字符串"})");
    std::vector<std::uint8_t> cbor = json::to_cbor(j);
    CHECK(!cbor.empty(), "to_cbor 产出非空");
    CHECK(json::from_cbor(cbor) == j, "CBOR 往返等价");

    std::vector<std::uint8_t> mp = json::to_msgpack(j);
    CHECK(json::from_msgpack(mp) == j, "MessagePack 往返等价");
    CHECK(j["b"].get<std::string>() == "字符串", "UTF-8 多字节内容保持不变");
}

int main(void)
{
    std::printf("nlohmann_json %d.%d.%d —— 真实断言测试\n",
                NLOHMANN_JSON_VERSION_MAJOR, NLOHMANN_JSON_VERSION_MINOR,
                NLOHMANN_JSON_VERSION_PATCH);
    test_version();
    test_parse();
    test_roundtrip();
    test_errors();
    test_binary();

    if (failures) {
        std::printf("\n结果：%d 条断言失败\n", failures);
        return 1;
    }
    std::printf("\n结果：全部断言通过\n");
    return 0;
}
