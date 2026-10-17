// Consumer test for cpptest 2.0.0: exercises the real public API.
// Two suites, each with passing asserts. Unlike upstream test/mytest.cpp
// (a demo whose main() always returns EXIT_SUCCESS), this program returns
// the Suite::run() verdict so failures actually fail the binary.
#include <cstdlib>
#include <string>

#include <cpptest.h>

class MathSuite : public Test::Suite {
public:
    MathSuite() {
        TEST_ADD(MathSuite::test_assert);
        TEST_ADD(MathSuite::test_delta);
    }

private:
    void test_assert() {
        TEST_ASSERT(1 + 1 == 2);
        TEST_ASSERT(6 * 7 == 42);
    }

    void test_delta() {
        TEST_ASSERT_DELTA(0.5, 0.7, 0.3);
        TEST_ASSERT_DELTA(1.0, 1.05, 0.1);
    }
};

class ThrowSuite : public Test::Suite {
public:
    ThrowSuite() {
        TEST_ADD(ThrowSuite::test_throws);
        TEST_ADD(ThrowSuite::test_no_throw);
    }

private:
    static void throw_int() { throw 13; }
    static void no_throw() {}

    void test_throws() {
        TEST_THROWS(throw_int(), int);
        TEST_THROWS_ANYTHING(throw_int());
    }

    void test_no_throw() {
        TEST_THROWS_NOTHING(no_throw());
        TEST_ASSERT(no_throw_helper() == std::string("ok"));
    }

    static std::string no_throw_helper() { return "ok"; }
};

int main() {
    Test::Suite ts;
    ts.add(std::unique_ptr<Test::Suite>(new MathSuite));
    ts.add(std::unique_ptr<Test::Suite>(new ThrowSuite));
    Test::TextOutput output(Test::TextOutput::Verbose);
    bool ok = ts.run(output, true);
    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
