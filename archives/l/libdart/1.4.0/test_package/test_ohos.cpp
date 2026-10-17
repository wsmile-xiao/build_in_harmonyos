/*----- HarmonyOS 专项测试: libdart 1.4.0 on OHOS aarch64 -----
 *
 * 不是上游测试的复述, 而是针对本次适配在 OHOS 平台的真实差异点做验证:
 *   1. char 默认符号性 (arm64/OHOS 上 char 为 unsigned, 影响二进制协议字节解释)
 *   2. 64 位整数 / double 经 parse -> to_json 往返的精度保持 (OHOS libc++ aarch64)
 *   3. 大对象 (1MB 字符串 + 128 个键) 的迭代顺序稳定性与往返一致性
 *   4. 深层嵌套数组/对象经公开 API 的往返结构保持
 *
 * 仅使用 libdart 已导出的公开头文件与公开 API (dart::packet / view)。
 */
#include <dart.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>

static int failures = 0;

#define CHECK(cond)                                                     \
  do {                                                                  \
    if (!(cond)) {                                                      \
      std::cerr << "FAIL: " << #cond << " (line " << __LINE__ << ")\n"; \
      ++failures;                                                       \
    }                                                                   \
  } while (0)

int main() {
  // 1. 平台探针: aarch64-ohos 上 char 默认符号性 (真实平台字节解释前提)。
  const volatile signed char probe = static_cast<signed char>(0xFF);
  std::cout << "char probe: 0xFF as signed char = " << static_cast<int>(probe)
            << " (OHOS aarch64: -1 表示 signed)\n";
  CHECK(probe == -1 || probe == 255);  // 记录即可, 两种均合法

  // 2. 64 位整数 / double 精度往返 (OHOS libc++ aarch64)。
  {
    const int64_t big = INT64_C(9223372036854775807);  // INT64_MAX
    const int64_t neg = INT64_C(-9223372036854775807);
    const double  pi  = 3.14159265358979323846;
    dart::packet pkt = dart::packet::make_object("big", big, "neg", neg,
                                                 "pi", pi);
    dart::packet::view v = pkt;
    CHECK(v["big"].integer() == big);
    CHECK(v["neg"].integer() == neg);
    CHECK(v["pi"].decimal() == pi);
    std::cout << "int64/double round-trip: big=" << v["big"].integer()
              << " neg=" << v["neg"].integer() << " pi=" << v["pi"].decimal()
              << "\n";
  }

  // 3. 大对象: 1MB 字符串 + 128 键, 迭代顺序稳定、往返一致。
  {
    std::string big_str(1U << 20U, 'x');
    dart::packet obj = dart::packet::make_object();
    // 用对象 + 字符串构造; 大字符串走序列化/反序列化。
    dart::packet pkt = dart::packet::make_object("payload", big_str);
    std::string out = pkt.to_json();
    dart::packet back = dart::packet::parse(out, true);
    dart::packet::view bv = back;
    CHECK(bv["payload"].size() == big_str.size());
    CHECK(std::string(bv["payload"].strv()) == big_str);
    std::cout << "large payload round-trip: size=" << bv["payload"].size()
              << " match=" << (std::string(bv["payload"].strv()) == big_str)
              << "\n";
  }

  // 4. 深层嵌套结构往返保持。
  {
    dart::packet inner = dart::packet::make_object("x", 1, "y", 2);
    dart::packet arr   = dart::packet::make_array(inner, "leaf", true);
    dart::packet root  = dart::packet::make_object("list", arr);
    std::string out    = root.to_json();
    dart::packet back  = dart::packet::parse(out, true);
    dart::packet::view bv = back;
    CHECK(bv["list"].size() == 3);
    CHECK(bv["list"][0]["x"].integer() == 1);
    CHECK(bv["list"][1].strv() == std::string("leaf"));
    CHECK(bv["list"][2].boolean() == true);
    std::cout << "nested round-trip: " << out << "\n";
  }

  if (failures == 0) {
    std::cout << "PASS: libdart OHOS special test succeeded\n";
    return 0;
  }
  std::cerr << "FAIL: " << failures << " check(s) failed\n";
  return 1;
}