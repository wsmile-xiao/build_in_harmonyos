// test_package/test.c — cheat 消费者测试
//
// 真实验证 cheat 1.0.4 的核心公开 API（CHEAT_TEST / cheat_assert /
// cheat_assert_not / cheat_assert_int 等）。每个断言失败都会使测试
// 二进制以非零退出码结束，非仅 include + return 0 的空壳测试。
#include <cheat.h>
#include <cheats.h>

CHEAT_TEST(consumer_math_still_work,
	cheat_assert(2 + 2 == 4);
	cheat_assert_not(2 + 2 == 5);
)

CHEAT_TEST(consumer_int_assertions,
	cheat_assert_int(6 * 7, 42);
	cheat_assert_int('A', 65);
)

CHEAT_TEST(consumer_ordering,
	cheat_assert('a' < 'z');
	cheat_assert(0.5f * 2.0f <= 1.0f);
)
