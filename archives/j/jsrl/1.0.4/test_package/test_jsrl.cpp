// jsrl 1.0.4 — test_package 消费者断言（鸿蒙特有测试行，R34/PF3/L0c）
//
// 通过 CMakeDeps 的 `jsrl::jsrl` 目标链接**打包后的库与头文件**（删掉包内
// include/jsrl/ 任一件即断编译），真实调用 jsrl 的公开解析/编码 API，全部在
// OHOS aarch64 + libc++ + C++17（库声明的最低标准）上实编译实运行。
//
// 断言覆盖（9 条，与 test_package/MANIFEST.yml 的 consumer_checks 一一对应）：
//   1. 对象解析：字符串/整数/布尔三类取值
//   2. 整数精取：as_number_sint 精确等于字面量（数字解析是本包核心卖点）
//   3. UTF-8 非 ASCII 值往返（鸿蒙PC，字节级相等；OHOS 无传统 locale）
//   4. 数组解析与 size
//   5. 对象遍历：迭代器能取到已知键
//   6. 紧凑编码 → 再解析 → 再编码的往返稳定性（encode/parse 幂等）
//   7. 高保真小数往返：30 位有效数字文本逐字保留（GeneralNumber 通路）
//   8. 类型误用走异常：对字符串调 as_number_sint 抛 Json::TypeError
//   9. 语义化 pretty_print 输出非空且含换行
//
// 末行输出 `JSRL-CONSUMER checks=<N> failures=<M>`，MANIFEST.yml 与 PR 正文的
// 「鸿蒙特有测试」行以该行数字为准。

#include <jsrl/jsrl.hpp>
#include <jsrl/jsrlpp.hpp>

#include <iostream>
#include <sstream>
#include <string>

namespace
{
int g_checks = 0;
int g_failures = 0;

void check( bool const ok, std::string const & what )
{
    ++g_checks;
    if ( ok ) {
        std::cout << "[ok]   " << what << std::endl;
    } else {
        ++g_failures;
        std::cerr << "[fail] " << what << std::endl;
    }
}
}  // namespace

int main()
{
    using jsrl::Json;

    // 鸿蒙PC 的 UTF-8 字节序列
    std::string const utf8_name = "\xe9\xb8\xbf\xe8\x92\x99PC";

    std::istringstream iss(
        R"({"name":"鸿蒙PC","age":30,"active":true,"tags":["a","b"],)"
        R"("pi":3.14159265358979323846})" );
    Json json;
    iss >> json;

    // 1) 对象解析：三类取值
    check( json["name"].as_string() == utf8_name && json["active"].as_bool(),
           "object parsed: string + bool accessors" );

    // 2) 整数精取
    check( json["age"].as_number_sint() == 30, "integer parsed exactly (as_number_sint == 30)" );

    // 3) UTF-8 非 ASCII 值往返（字节级）
    check( json["name"].as_string().size() == utf8_name.size()
               && json["name"].as_string() == utf8_name,
           "non-ASCII (UTF-8) value round-trip byte-equal (鸿蒙PC)" );

    // 4) 数组解析与 size
    check( json["tags"].as_array().size() == 2, "array parsed with expected size (2)" );

    // 5) 对象遍历：迭代器能取到已知键
    bool found_age = false;
    for ( auto const &kv : json.as_object() ) {
        if ( kv.first == "age" ) {
            found_age = true;
        }
    }
    check( found_age, "object iteration yields the known key 'age'" );

    // 6) 紧凑编码 → 再解析 → 再编码的往返稳定性
    std::ostringstream oss1;
    oss1 << json;
    std::istringstream iss2( oss1.str() );
    Json json2;
    iss2 >> json2;
    std::ostringstream oss2;
    oss2 << json2;
    check( !oss1.str().empty() && oss1.str() == oss2.str(),
           "compact encode -> reparse -> reencode is stable" );

    // 7) 高保真数字往返：29 位有效小数文本逐字保留 + 双精度不可表示的整数 2^53+1
    std::istringstream nss( R"({"d":1234567890.1234567890123456789,"i":9007199254740993})" );
    Json njson;
    nss >> njson;
    std::ostringstream noss;
    noss << njson;
    check( noss.str().find( "1234567890.1234567890123456789" ) != std::string::npos
               && noss.str().find( "9007199254740993" ) != std::string::npos,
           "high-fidelity numbers round-trip: 29-digit decimal + 2^53+1 kept exact" );

    // 8) 类型误用走异常
    bool threw_type = false;
    try {
        (void)json["name"].as_number_sint();
    } catch ( Json::TypeError const & ) {
        threw_type = true;
    } catch ( ... ) {
    }
    check( threw_type, "wrong-type accessor throws jsrl::Json::TypeError" );

    // 9) pretty_print 输出非空且多行
    std::ostringstream pss;
    pss << jsrl::pretty_print( json ).indent( "  " );
    std::string const pretty = pss.str();
    check( !pretty.empty() && pretty.find( '\n' ) != std::string::npos,
           "pretty_print produces indented multi-line output" );

    std::cout << "JSRL-CONSUMER checks=" << g_checks << " failures=" << g_failures << std::endl;
    return g_failures == 0 ? 0 : 1;
}
