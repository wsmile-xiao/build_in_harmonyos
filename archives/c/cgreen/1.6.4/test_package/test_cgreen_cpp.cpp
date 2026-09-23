/*
 * test_cgreen_cpp.cpp — NEW C++ consumer tests for the packaged libcgreen.
 * libcgreen carries C++ support (cpp_assertions/cpp_constraint objects), so a
 * C++ translation unit linking against the installed library validates the
 * C++ consumption path: STL string constraints and user-type equality.
 *
 * Test inventory: 5 test functions / 8 assertion calls, all expected-pass.
 */
#include <cgreen/cgreen.h>
#include <stdio.h>
#include <string>

using namespace cgreen;

Describe(CppConsumer);
BeforeEach(CppConsumer) {}
AfterEach(CppConsumer) {}

class Point {
public:
    int x_;
    int y_;
    Point(int x, int y) : x_(x), y_(y) {}
    bool operator==(const Point &other) const {
        return x_ == other.x_ && y_ == other.y_;
    }
    bool operator!=(const Point &other) const {
        return !(*this == other);
    }
};

Ensure(CppConsumer, cpp_int_arithmetic) {
    assert_that(2 + 2, is_equal_to(4));
    assert_that(1, is_true);
}

Ensure(CppConsumer, cpp_stl_string_equality) {
    std::string bob("bob");
    assert_that(bob, is_equal_to_string(bob));
    assert_that(bob, is_equal_to_string("bob"));
}

Ensure(CppConsumer, cpp_stl_string_contains) {
    std::string bobbob("bobbob");
    assert_that(bobbob, contains_string("obbo"));
    assert_that(bobbob, begins_with_string("bob"));
}

Ensure(CppConsumer, cpp_custom_type_equality) {
    Point first(1, 2);
    Point second(1, 2);
    assert_that(first == second);
}

Ensure(CppConsumer, cpp_custom_type_inequality) {
    Point first(1, 2);
    Point second(2, 1);
    assert_that(first != second);
}

int main(void) {
    TestSuite *suite = create_test_suite();
    TestReporter *reporter = create_text_reporter();
    int rc;
    add_test_with_context(suite, CppConsumer, cpp_int_arithmetic);
    add_test_with_context(suite, CppConsumer, cpp_stl_string_equality);
    add_test_with_context(suite, CppConsumer, cpp_stl_string_contains);
    add_test_with_context(suite, CppConsumer, cpp_custom_type_equality);
    add_test_with_context(suite, CppConsumer, cpp_custom_type_inequality);
    rc = run_test_suite(suite, reporter);
    destroy_test_suite(suite);
    destroy_reporter(reporter);
    printf("test_cgreen_cpp rc=%d\n", rc);
    return rc;
}
