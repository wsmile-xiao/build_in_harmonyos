#include <cppunit/TestFixture.h>
#include <cppunit/extensions/HelperMacros.h>
#include <cppunit/extensions/TestFactoryRegistry.h>
#include <cppunit/ui/text/TestRunner.h>

class ArithmeticTest : public CppUnit::TestFixture {
    CPPUNIT_TEST_SUITE(ArithmeticTest);
    CPPUNIT_TEST(testMultiplication);
    CPPUNIT_TEST_SUITE_END();

public:
    void testMultiplication() {
        CPPUNIT_ASSERT_EQUAL(42, 6 * 7);
    }
};

CPPUNIT_TEST_SUITE_REGISTRATION(ArithmeticTest);

int main() {
    CppUnit::TextUi::TestRunner runner;
    runner.addTest(CppUnit::TestFactoryRegistry::getRegistry().makeTest());
    return runner.run("", false) ? 0 : 1;
}
