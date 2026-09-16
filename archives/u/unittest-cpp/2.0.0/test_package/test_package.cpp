#include <UnitTest++/UnitTest++.h>

TEST(InstalledFrameworkRuns) {
    CHECK_EQUAL(42, 6 * 7);
}

int main() {
    return UnitTest::RunAllTests();
}
