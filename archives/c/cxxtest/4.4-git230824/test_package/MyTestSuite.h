#include <cxxtest/TestSuite.h>

class MyTestSuite : public CxxTest::TestSuite
{
public:
    void testAddition(void)
    {
        TS_ASSERT(1 + 1 > 1);
        TS_ASSERT_EQUALS(1 + 1, 2);
    }

    void testSubtraction(void)
    {
        TS_ASSERT_EQUALS(5 - 3, 2);
        TS_ASSERT_DIFFERS(5 - 3, 3);
    }
};
