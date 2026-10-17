/* test_package: 通过安装后的公开头文件 <exotic/cester.h> 使用 libcester 框架，
 * 验证第三方使用者可编译、链接并实际运行断言（R34：禁止空壳 print）。
 * libcester 自动生成 main（无需 CESTER_MAIN），运行测试套件并退出。 */

#include <exotic/cester.h>
#include <string.h>

CESTER_TEST(consumer_assert_int, inst,
    cester_assert_int_eq(2 + 3, 5);
    cester_assert_int_ne(5, 6);
    cester_assert_int_gt(10, 3);
    cester_assert_int_lt(3, 10);
    cester_assert_int_ge(7, 7);
    cester_assert_int_le(7, 7);
)

CESTER_TEST(consumer_assert_string, inst,
    cester_assert_str_equal("libcester", "libcester");
    cester_assert_str_not_equal("libcester", "muon");
)

CESTER_TEST(consumer_assert_true_false, inst,
    cester_assert_true(1 == 1);
    cester_assert_false(1 == 2);
)

CESTER_TEST(consumer_assert_equal, inst,
    cester_assert_equal(42, 42);
    cester_assert_null(NULL);
    cester_assert_not_null(inst);
)
