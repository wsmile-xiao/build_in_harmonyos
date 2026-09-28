// test_daw_utf_range.cpp — L1 smoke test for daw_utf_range 2.2.6 header-only library
// 验证 daw/utf_range/daw_utf_range.h / daw/utf_range/daw_utf_string.h / daw/utf8/*.h
// 头文件可正常包含与核心 API（char_range 遍历 / utf_string 比较 / utf8 校验）
#include <daw/utf_range/daw_utf_range.h>
#include <daw/utf_range/daw_utf_string.h>
#include <daw/utf8/unchecked.h>
#include <daw/utf8/checked.h>
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

int main() {
    // 测试 1: daw::range::create_char_range 构造与 UTF-8 码点遍历
    // "Привет" — 6 个西里尔字母，每个占 2 字节 UTF-8，共 12 字节 → 6 码点
    auto const rng = daw::range::create_char_range( "Привет" );
    std::size_t count = 0;
    for( auto c : rng ) {
        (void)c;
        ++count;
    }
    if( count != 6 ) {
        std::cerr << "FAIL: char_range should yield 6 code points, got " << count << std::endl;
        return 1;
    }

    // 测试 2: ASCII 文本遍历（字节数 == 码点数）
    auto const rng2 = daw::range::create_char_range( "hello world" );
    std::size_t count2 = 0;
    for( auto c : rng2 ) {
        (void)c;
        ++count2;
    }
    if( count2 != 11 ) {
        std::cerr << "FAIL: ASCII char_range should yield 11 code points, got " << count2 << std::endl;
        return 1;
    }

    // 测试 3: daw::utf_string 基本比较（同 daw_json_link 上游 daw_utf_string_test.cpp 用例）
    daw::utf_string const a = "a";
    daw::utf_string const aa = "aa";
    daw::utf_string const bb = "bb";
    if( !( a == a ) ) {
        std::cerr << "FAIL: utf_string self equality failed" << std::endl;
        return 1;
    }
    if( !( a != bb ) ) {
        std::cerr << "FAIL: utf_string inequality failed" << std::endl;
        return 1;
    }
    if( !( a < aa && a < bb && aa < bb && bb > aa ) ) {
        std::cerr << "FAIL: utf_string lexicographic comparison failed" << std::endl;
        return 1;
    }

    // 测试 4: daw::utf_string 构造/size/empty（多文种码点计数）
    // 注: 上游 sort() 存在缺陷（to_u32string 后重复 std::copy 追加，size 翻倍），
    //     非适配问题，详见 notes.md——本消费者测试不覆盖 sort 路径
    daw::utf_string multi = "Привет";  // 6 个西里尔字母 = 6 码点
    daw::utf_string empty_str = "";
    if( multi.empty( ) || multi.size( ) != 6 ) {
        std::cerr << "FAIL: utf_string multi size should be 6, got " << multi.size( ) << std::endl;
        return 1;
    }
    if( !empty_str.empty( ) || empty_str.size( ) != 0 ) {
        std::cerr << "FAIL: utf_string empty invariant failed" << std::endl;
        return 1;
    }

    // 测试 5: utf8 unchecked 迭代器基本使用（daw_json_link 序列化路径同款头）
    // "日本語テキスト" = 日/本/語/テ/キ/ス/ト → 7 个码点
    std::string const utf8_text = u8"日本語テキスト";
    auto first = utf8_text.data( );
    auto const last = utf8_text.data( ) + utf8_text.size( );
    std::size_t cp_count = 0;
    while( first != last ) {
        auto const cp = daw::utf8::unchecked::next( first );
        (void)cp;
        ++cp_count;
    }
    if( cp_count != 7 ) {
        std::cerr << "FAIL: unchecked utf8 iteration should yield 7 code points, got " << cp_count << std::endl;
        return 1;
    }

    std::cout << "PASS: daw_utf_range header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
