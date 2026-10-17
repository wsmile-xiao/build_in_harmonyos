// test_package/test.cpp — boost-defaults 1.90.0.2 元包消费者验证。
//
// 元包语义：boost-defaults requires boost/1.90.0，全部 Boost 开发资源
// （头文件、编译库）经依赖传播可用。本程序从消费者视角断言：
//   1. Boost 头文件可用（smart_ptr / config / version 等核心头）；
//   2. BOOST_LIB_VERSION == "1_90"（默认版本正确性——boost-defaults 的
//      存在意义就是把默认版本钉在 1.90）；
//   3. 链接 boost 传播的编译库 unit_test_framework 并真实运行测试。
//
// 注：boost/1.90.0 的 Boost.Test 静态库以 BOOST_TEST_ALTERNATIVE_INIT_API
// 编译（见 archives/b/boost/1.90.0/conanfile.py），main() 由库提供，用户
// 需提供 init_unit_test() 入口注册测试用例（消费者测试写法与 boost 1.90.0
// 本体的 test_package/test.cpp 保持一致）。
#include <boost/smart_ptr/shared_ptr.hpp>
#include <boost/smart_ptr/weak_ptr.hpp>
#include <boost/make_shared.hpp>
#include <boost/config.hpp>
#include <boost/version.hpp>

#include <string>

#include <boost/test/unit_test.hpp>
#include <boost/test/unit_test_suite.hpp>
#include <boost/test/test_tools.hpp>

// 用户 init 函数：由库内 main() 调用（alternative init API）
bool init_unit_test()
{
    boost::unit_test::test_suite* ts = BOOST_TEST_SUITE("boost_defaults_suite");

    // 元包核心断言：默认 Boost 版本必须是 1.90
    // BOOST_VERSION = 1*100000 + 90*100 = 109000 (1.90.0)
    ts->add(BOOST_TEST_CASE([] {
        BOOST_CHECK_EQUAL(BOOST_LIB_VERSION, "1_90");
        BOOST_CHECK_EQUAL(BOOST_VERSION, 109000);
    }));

    // 头文件可用性：smart_ptr 家族 + 观察者语义
    ts->add(BOOST_TEST_CASE([] {
        boost::shared_ptr<std::string> sp =
            boost::make_shared<std::string>("boost-defaults");
        BOOST_REQUIRE(sp != nullptr);
        BOOST_CHECK_EQUAL(sp->size(), 14u);
        BOOST_CHECK_EQUAL(*sp, "boost-defaults");

        auto wp = boost::weak_ptr<std::string>(sp);
        auto locked = wp.lock();
        BOOST_CHECK(locked == sp);
    }));

    // 头文件可用性：config 头 + 基本平台语义
    ts->add(BOOST_TEST_CASE([] {
        BOOST_CHECK_EQUAL(sizeof(char), 1u);
        BOOST_CHECK(BOOST_VERSION > 0);
    }));

    boost::unit_test::framework::master_test_suite().add(ts);
    return true;
}
