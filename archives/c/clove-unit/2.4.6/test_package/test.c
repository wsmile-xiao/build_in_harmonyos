// test.c — clove-unit 2.4.6 消费者冒烟测试（R34：实质调用被测包公开 API）
//
// 通过 conan `find_package(clove-unit)` 拿到**已安装的** `include/clove-unit.h`
// （不是源码树里那一份），按上游 README 的标准用法：
//   1) 单个 TU 内 `#define CLOVE_IMPLEMENTATION` 展开实现；
//   2) `#define CLOVE_SUITE_NAME <名字>` + `CLOVE_TEST(<标题>)` 声明用例；
//   3) `CLOVE_RUNNER()` 生成 `main()`，由 runner 的 ELF 符号表扫描自动发现用例。
// 进程退出码即用例结果（ctest 按 rc 判绿），共 3 用例 / 8 断言。
#define CLOVE_IMPLEMENTATION
#include <clove-unit.h>

#define CLOVE_SUITE_NAME ConsumerSmoke

CLOVE_TEST(IntArithmetic)
{
    CLOVE_INT_EQ(40 + 2, 42);
    CLOVE_INT_NE(41, 42);
    CLOVE_INT_GT(42, 41);
}

CLOVE_TEST(StringHandling)
{
    CLOVE_STRING_EQ("clove-unit", "clove-unit");
    CLOVE_STRING_NE("2.4.5", "2.4.6");
}

CLOVE_TEST(BoolAndNull)
{
    CLOVE_IS_TRUE(1 == 1);
    CLOVE_IS_FALSE(1 == 2);
    int local = 0;
    CLOVE_NOT_NULL(&local);
}

CLOVE_RUNNER()
