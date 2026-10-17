// test_package/test_unittest.cpp — unittest 0.50-62 消费者验证（8 个用例）
//
// 只使用打包产物：<unittest/UnitTest.hpp>、<unittest/Registry.hpp>、
// <unittest/ExistingBase.hpp> 与 libunittest.a。8 个用例覆盖框架公共 API（ASSERT/ASSERT_EQUALS/
// ASSERT_EXCEPTION 宏、setUp/run/tearDown 生命周期、嵌套套件聚合、
// TestPtr 引用语义、radix 开关、ExistingBase/ExistingObject 包装），
// 全部注册进单个 UnitTest::Registry 并运行；Registry 打印确定性汇总行
// "Tests finished with N passes and M failures."，main 原样返回其退出码
//（全过 = 0）。test() 解析该汇总行并与源码注册数 8 交叉核对。
#include <unittest/UnitTest.hpp>
#include <unittest/Registry.hpp>
#include <unittest/ExistingBase.hpp>

#include <stdexcept>
#include <string>

namespace {

// 1. 基本布尔断言
class ArithmeticAssert : public UnitTest::Test {
public:
    void run() {
        int value = 40 + 2;
        ASSERT(value == 42);
        ASSERT(value > 0);
        ASSERT(!(value < 0));
    }
};

// 2. 字符串相等断言（含 const char* 重载）
class StringEquals : public UnitTest::Test {
public:
    void run() {
        std::string value("unittest-on-ohos");
        ASSERT_EQUALS(std::string("unittest-on-ohos"), value);
        ASSERT_EQUALS("unittest-on-ohos", value);
        ASSERT_EQUALS(value, "unittest-on-ohos");
    }
};

// 3. 异常断言
class ExceptionAssert : public UnitTest::Test {
public:
    void run() {
        ASSERT_EXCEPTION(throw std::runtime_error("expected"),
                         std::runtime_error);
    }
};

// 4. setUp/run/tearDown 生命周期
class Lifecycle : public UnitTest::Test {
public:
    Lifecycle() : state_(0) {}
    void setUp() {
        state_ = 41;
    }
    void run() {
        ASSERT(state_ == 41);
        state_ = 42;
    }
    void tearDown() {
        ASSERT(state_ == 42);
    }
private:
    int state_;
};

// 5. 嵌套套件的 passes/failures 聚合
class NestedSuite : public UnitTest::Test {
public:
    void run() {
        UnitTest::Suite inner;
        inner.add<ArithmeticAssert>();
        inner.add<StringEquals>();
        inner.run();
        ASSERT_EQUALS(2, inner.passes());
        ASSERT_EQUALS(0, inner.failures());
    }
};

// 6. TestPtr 引用计数语义（被引对象存活期）
class Probe : public UnitTest::Test {
public:
    Probe(int *live) : live_(live) {
        ++(*live_);
    }
    ~Probe() {
        --(*live_);
    }
    void run() {}
private:
    int *live_;
};

class TestPtrSemantics : public UnitTest::Test {
public:
    void run() {
        int live = 0;
        {
            UnitTest::TestPtr first(new Probe(&live));
            ASSERT_EQUALS(1, live);
            {
                UnitTest::TestPtr second(first);
                ASSERT_EQUALS(1, live);
            }
            ASSERT_EQUALS(1, live);
        }
        ASSERT_EQUALS(0, live);
    }
};

// 7. radix 输出进制开关
class RadixControl : public UnitTest::Test {
public:
    void run() {
        ASSERT(UnitTest::radix() == UnitTest::DECIMAL);
        UnitTest::radix(UnitTest::HEX);
        ASSERT(UnitTest::radix() == UnitTest::HEX);
        UnitTest::radix(UnitTest::DECIMAL);
        ASSERT(UnitTest::radix() == UnitTest::DECIMAL);
    }
};

// 8. ExistingBase/ExistingObject 泄漏自检包装
class Tracked : public UnitTest::ExistingObject<Tracked> {
public:
    Tracked() {}
    Tracked(const Tracked &other)
        : UnitTest::ExistingObject<Tracked>(other) {}
};

class ExistingBaseWrap : public UnitTest::Test,
                         public UnitTest::ExistingBase<Tracked> {
public:
    void run() {
        Tracked first;
        ASSERT_EQUALS(1, existing());
        {
            Tracked second(first);
            ASSERT_EQUALS(2, existing());
        }
        ASSERT_EQUALS(1, existing());
    }
};

}  // namespace

int main(int argc, char **argv) {
    UnitTest::Registry registry;
    registry.add(UnitTest::TestPtr(new ArithmeticAssert()), "arithmetic");
    registry.add(UnitTest::TestPtr(new StringEquals()), "strings");
    registry.add(UnitTest::TestPtr(new ExceptionAssert()), "exceptions");
    registry.add(UnitTest::TestPtr(new Lifecycle()), "lifecycle");
    registry.add(UnitTest::TestPtr(new NestedSuite()), "nested");
    registry.add(UnitTest::TestPtr(new TestPtrSemantics()), "testptr");
    registry.add(UnitTest::TestPtr(new RadixControl()), "radix");
    registry.add(UnitTest::TestPtr(new ExistingBaseWrap()), "existing");
    return registry.run(argc, argv);
}
