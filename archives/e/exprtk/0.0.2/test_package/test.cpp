#include <cmath>
#include <cstdio>
#include <string>

#include "exprtk.hpp"

static int failures = 0;

static void check(bool cond, const char* what)
{
    if (!cond)
    {
        std::printf("FAIL: %s\n", what);
        ++failures;
    }
}

int main()
{
    typedef exprtk::symbol_table<double> symbol_table_t;
    typedef exprtk::expression<double>   expression_t;
    typedef exprtk::parser<double>       parser_t;

    symbol_table_t symbol_table;
    expression_t   expression;
    parser_t       parser;

    double x = 1.0;
    double y = 2.0;

    symbol_table.add_variable("x", x);
    symbol_table.add_variable("y", y);
    symbol_table.add_constants();

    expression.register_symbol_table(symbol_table);

    check(parser.compile("x + y * 2 + sqrt(16)", expression),
          "compile basic expression");
    check(std::fabs(expression.value() - (1.0 + 2.0 * 2.0 + 4.0)) < 1e-12,
          "evaluate x + y*2 + sqrt(16) == 9");

    x = 3.0;
    check(std::fabs(expression.value() - (3.0 + 4.0 + 4.0)) < 1e-12,
          "re-evaluate after x=3 == 11");

    check(parser.compile("min(x, y) + max(x, y) + pi / 2", expression),
          "compile min/max/pi expression");
    check(std::fabs(expression.value() - (2.0 + 3.0 + 1.5707963267948966)) < 1e-12,
          "evaluate min(x,y)+max(x,y)+pi/2");

    check(!parser.compile("1 + * 2", expression),
          "invalid expression must fail to compile");

    if (failures == 0)
    {
        std::printf("exprtk consumer test: all checks passed\n");
        return 0;
    }
    std::printf("exprtk consumer test: %d check(s) failed\n", failures);
    return 1;
}
