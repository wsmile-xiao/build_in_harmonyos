// test_daw_json_link.cpp — L1 smoke test for daw_json_link 3.38.1 header-only library
// 验证 daw/json/daw_json_link.h 核心 API：
//   - json_data_contract 数据契约定义
//   - from_json（解析）/ to_json（序列化）往返
//   - json_value 动态访问
// 参考 upstream readme.md 基本用法示例
#include <daw/json/daw_json_link.h>
#include <daw/json/daw_from_json.h>
#include <daw/json/daw_to_json.h>
#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>

namespace ns {
  struct MyClass {
    int member_a;
    float member_b;
    std::string member_c;
    std::vector<int> member_d;
  };
}

namespace daw::json {
  template<>
  struct json_data_contract<ns::MyClass> {
    static constexpr char const member_a[] = "a";
    static constexpr char const member_b[] = "b";
    static constexpr char const member_c[] = "c";
    static constexpr char const member_d[] = "d";
    using type = json_member_list<
      json_number<member_a, int>,
      json_number<member_b, float>,
      json_string<member_c>,
      json_array<member_d, int>>;

    static inline auto to_json_data( ns::MyClass const &value ) {
      return std::forward_as_tuple( value.member_a, value.member_b, value.member_c, value.member_d );
    }
  };
}

int main( ) {
    // 测试 1: from_json 解析（上游 readme 基本用法）
    constexpr std::string_view json_data = R"({
      "a": 42,
      "b": 3.25,
      "c": "hello world",
      "d": [1, 2, 3, 4, 5]
    })";
    auto const result = daw::json::from_json<ns::MyClass>( json_data );
    if( result.member_a != 42 ) {
        std::cerr << "FAIL: member_a should be 42, got " << result.member_a << std::endl;
        return 1;
    }
    if( std::abs( result.member_b - 3.25f ) > 0.001f ) {
        std::cerr << "FAIL: member_b should be 3.25, got " << result.member_b << std::endl;
        return 1;
    }
    if( result.member_c != "hello world" ) {
        std::cerr << "FAIL: member_c mismatch: " << result.member_c << std::endl;
        return 1;
    }
    if( result.member_d.size( ) != 5 || result.member_d[0] != 1 || result.member_d[4] != 5 ) {
        std::cerr << "FAIL: member_d array mismatch" << std::endl;
        return 1;
    }

    // 测试 2: to_json 序列化（daw-utf-range 依赖路径覆盖）
    std::string const serialized = daw::json::to_json( result );
    if( serialized.find( "\"a\":42" ) == std::string::npos
        && serialized.find( "\"a\": 42" ) == std::string::npos ) {
        std::cerr << "FAIL: serialized output missing a:42 — got: " << serialized << std::endl;
        return 1;
    }
    if( serialized.find( "hello world" ) == std::string::npos ) {
        std::cerr << "FAIL: serialized output missing string member" << std::endl;
        return 1;
    }

    // 测试 3: json_value 动态访问（无契约路径，find_member 返回值语义）
    auto jv = daw::json::json_value( json_data );
    auto const a_val = jv.find_member( "a" );
    if( not a_val or a_val.template as<int>( ) != 42 ) {
        std::cerr << "FAIL: json_value dynamic member access failed" << std::endl;
        return 1;
    }

    // 测试 4: 序列化往返完整性——重新解析序列化结果
    auto const roundtrip = daw::json::from_json<ns::MyClass>( serialized );
    if( roundtrip.member_a != result.member_a
        or roundtrip.member_c != result.member_c
        or roundtrip.member_d.size( ) != result.member_d.size( ) ) {
        std::cerr << "FAIL: roundtrip via serialized output mismatch" << std::endl;
        return 1;
    }

    std::cout << "PASS: daw_json_link header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
