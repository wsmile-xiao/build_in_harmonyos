// test_package/test_cxxtest.h — consumer test suite for cxxtest 4.1 (R34)
// A real CxxTest suite exercising the packaged headers the way a downstream
// project does: TS_ASSERT / TS_ASSERT_EQUALS / TS_ASSERT_DIFFERS /
// TS_ASSERT_LESS_THAN / TS_ASSERT_THROWS Anything assertions drive the
// framework for real (no stubs).
#include <cxxtest/TestSuite.h>

class ConsumerSuite : public CxxTest::TestSuite
{
public:
    void testArithmetic( void )
    {
        TS_ASSERT( 1 + 1 > 1 );
        TS_ASSERT_EQUALS( 1 + 1, 2 );
        TS_ASSERT_DIFFERS( 1 + 1, 3 );
        TS_ASSERT_LESS_THAN( 2, 3 );
    }

    void testStrings( void )
    {
        const char* name = "cxxtest";
        TS_ASSERT_EQUALS( std::string(name).size(), 7u );
        TS_ASSERT_SAME_DATA( name, "cxxtest", 8 );  // includes the NUL byte
    }

    void testExceptions( void )
    {
        TS_ASSERT_THROWS( throw std::runtime_error("boom"), std::runtime_error );
        TS_ASSERT_THROWS_NOTHING( (void)0 );
    }

    void testFloatingPoint( void )
    {
        TS_ASSERT_DELTA( 0.1 + 0.2, 0.3, 1e-9 );
    }
};
