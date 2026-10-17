/* test_package: 消费者视角验证 ctest 头文件可用（R34：必须实际调用被测包 API） */
#include <stdio.h>
#include <stdlib.h>

#define CTEST_MAIN
#include "ctest.h"

CTEST(smoke, pass) {
    ASSERT_EQUAL(1, 1);
}

CTEST(smoke, str) {
    ASSERT_STR("ok", "ok");
}

CTEST(smoke2, plain) {
    ASSERT_TRUE(1 == 1);
}

CTEST_DATA(smoke3) {
    int v;
};

CTEST_SETUP(smoke3) {
    data->v = 42;
}

CTEST_TEARDOWN(smoke3) {
    data->v = 0;
}

CTEST2(smoke3, setup_teardown) {
    ASSERT_EQUAL(42, data->v);
}

int main(int argc, const char *argv[])
{
    return ctest_main(argc, argv);
}
