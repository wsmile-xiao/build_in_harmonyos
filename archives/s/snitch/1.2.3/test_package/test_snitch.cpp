// snitch 1.2.3 — 消费者测试（鸿蒙特有测试 / L1 test_package）。
// 从消费者视角断言已安装 snitch 制品可用：宏注册、断言求值、
// 匹配器、section 重组与 capture、**安装头自报版本指纹**（§二.19：
// 测试必须指向 package() 交付的那一份并断言版本宏/内容指纹）。
// 全部由已打包的 snitch 库驱动，with_main=ON 自带 main，
// 全过时进程退出码为 0。
#include <snitch/snitch.hpp>

#include <string>
#include <vector>

TEST_CASE("harmonyos: installed artifact version", "[harmonyos]") {
    // SNITCH_VERSION 来自已安装的 snitch_config.hpp（package() 交付面）
    CHECK(std::string{SNITCH_VERSION} == "1.2.3");
    CHECK(SNITCH_VERSION_MAJOR == 1);
    CHECK(SNITCH_VERSION_MINOR == 2);
    CHECK(SNITCH_VERSION_PATCH == 3);
}

TEST_CASE("harmonyos: basic assertions", "[harmonyos]") {
    CHECK(1 + 1 == 2);
    CHECK(2 * 3 == 6);
    CHECK(10 - 4 == 6);
    REQUIRE(4 > 2);
}

TEST_CASE("harmonyos: string matchers", "[harmonyos]") {
    std::string lib = "snitch";
    CHECK_THAT(lib, snitch::matchers::contains_substring{"nitc"});
    CHECK(std::string{"harmonyos"} != "ohos");
}

TEST_CASE("harmonyos: sections and captures", "[harmonyos]") {
    SECTION("vector sizing") {
        std::vector<int> v(3, 7);
        REQUIRE(v.size() == 3);
        CHECK(v[2] == 7);
    }
    SECTION("captured expression") {
        int x = 21;
        CAPTURE(x);
        CHECK(x * 2 == 42);
    }
}
