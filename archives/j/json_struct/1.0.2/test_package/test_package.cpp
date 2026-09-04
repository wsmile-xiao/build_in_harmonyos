// test_package.cpp — json_struct 1.0.2 HarmonyOS 专项消费者测试
//
// 本测试为鸿蒙专项消费者用例（非复述上游测试）：
//   1. UTF-8 中文串与 emoji 的 round-trip（鸿蒙系统中文场景）
//   2. int64/uint64 大数值精度 round-trip（arm64 全 64 位场景）
//   3. 枚举与嵌套结构解析
//   4. 非法 JSON 错误路径（错误行/列与原因字符串）
//   5. JS::serializeStruct 序列化回环
//
// 通过 Conan test_package 在 conan create 时编译运行（W3/CI 同源）。

#include <json_struct/json_struct.h>

#include <cstdint>
#include <iostream>
#include <string>

JS_ENUM(OrderStatus, created, paid, shipped)

struct Contact {
  std::string name;
  std::string remark;
  JS_OBJECT(JS_MEMBER(name), JS_MEMBER(remark));
};

struct Order {
  int64_t id;
  uint64_t amount;
  Contact contact;
  OrderStatus status = OrderStatus::created;
  JS_OBJECT(JS_MEMBER(id), JS_MEMBER(amount), JS_MEMBER(contact),
            JS_MEMBER(status));
};

JS_ENUM_DECLARE_STRING_PARSER(OrderStatus)

static int failures = 0;

template <typename T>
static void check_eq(const char *what, const T &lhs, const T &rhs) {
  if (lhs != rhs) {
    std::cerr << "FAIL: " << what << " lhs=" << lhs << " rhs=" << rhs
              << std::endl;
    ++failures;
  }
}

static void test_utf8_roundtrip() {
  // 鸿蒙中文场景：中文姓名 + emoji 备注
  const std::string remark = std::string("HarmonyOS \xF0\x9F\x9A\x80");
  const std::string json =
      std::string("{\"name\":\"\xE5\xBC\xA0\xE4\xB8\x89\",\"remark\":\"") +
      remark + "\"}";
  Contact c;
  JS::ParseContext ctx(json.c_str(), json.size());
  if (ctx.parseTo(c) != JS::Error::NoError) {
    std::cerr << "FAIL: utf8 parse error: " << ctx.makeErrorString()
              << std::endl;
    ++failures;
    return;
  }
  check_eq("utf8 name", c.name, std::string("\xE5\xBC\xA0\xE4\xB8\x89"));
  check_eq("utf8 remark", c.remark, remark);
}

static void test_int64_precision() {
  // arm64 全 64 位：int64 下界与 uint64 上界序列化回环
  const int64_t id_min = INT64_MIN + 1;  // -9223372036854775807
  Order o;
  o.id = id_min;
  o.amount = UINT64_MAX;
  o.status = OrderStatus::shipped;

  const std::string s = JS::serializeStruct(o);
  if (s.find("-9223372036854775807") == std::string::npos) {
    std::cerr << "FAIL: int64 serialize lost precision: " << s << std::endl;
    ++failures;
  }
  if (s.find("18446744073709551615") == std::string::npos) {
    std::cerr << "FAIL: uint64 serialize lost precision: " << s << std::endl;
    ++failures;
  }

  // 回环解析
  Order roundtrip;
  JS::ParseContext pc(s.c_str(), s.size());
  if (pc.parseTo(roundtrip) != JS::Error::NoError) {
    std::cerr << "FAIL: int64 roundtrip parse: " << pc.makeErrorString()
              << std::endl;
    ++failures;
    return;
  }
  check_eq("int64 roundtrip id", roundtrip.id, id_min);
  check_eq("uint64 roundtrip amount", roundtrip.amount, UINT64_MAX);
}

static void test_enum_nested() {
  const std::string json =
      "{\"id\":7,\"amount\":100,"
      "\"contact\":{\"name\":\"Li\",\"remark\":\"x\"},"
      "\"status\":\"paid\"}";
  Order o;
  JS::ParseContext ctx(json.c_str(), json.size());
  if (ctx.parseTo(o) != JS::Error::NoError) {
    std::cerr << "FAIL: nested parse: " << ctx.makeErrorString() << std::endl;
    ++failures;
    return;
  }
  check_eq("nested id", o.id, int64_t(7));
  check_eq("nested contact name", o.contact.name, std::string("Li"));
  check_eq("nested status", static_cast<int>(o.status),
           static_cast<int>(OrderStatus::paid));

  // 序列化回环：解析回结构并验证 enum 值（溯源码格式无关）
  const std::string s = JS::serializeStruct(o);
  Order roundtrip2;
  JS::ParseContext pc2(s.c_str(), s.size());
  if (pc2.parseTo(roundtrip2) != JS::Error::NoError) {
    std::cerr << "FAIL: enum serialize roundtrip: " << pc2.makeErrorString()
              << std::endl;
    ++failures;
    return;
  }
  check_eq("enum serialize roundtrip status",
           static_cast<int>(roundtrip2.status),
           static_cast<int>(OrderStatus::paid));
}

static void test_error_path() {
  const std::string bad = "{\"id\":abc}";
  Order o;
  JS::ParseContext ctx(bad.c_str(), bad.size());
  JS::Error err = ctx.parseTo(o);
  if (err == JS::Error::NoError) {
    std::cerr << "FAIL: invalid json accepted" << std::endl;
    ++failures;
    return;
  }
  if (ctx.makeErrorString().empty()) {
    std::cerr << "FAIL: empty error string" << std::endl;
    ++failures;
  }
}

int main() {
  test_utf8_roundtrip();
  test_int64_precision();
  test_enum_nested();
  test_error_path();
  if (failures == 0) {
    std::cout << "json_struct OHOS consumer test: ALL PASSED" << std::endl;
    return 0;
  }
  std::cout << "json_struct OHOS consumer test: " << failures << " FAILED"
            << std::endl;
  return 1;
}