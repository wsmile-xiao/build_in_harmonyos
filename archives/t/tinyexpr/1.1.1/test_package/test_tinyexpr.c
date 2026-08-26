#include <tinyexpr.h>

#include <math.h>
#include <stdio.h>

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL: %s\n", message); \
        failures++; \
    } \
} while (0)

static int nearly_equal(double left, double right) {
    return fabs(left - right) < 1e-9;
}

int main(void) {
    double x = 3.0;
    double y = 4.0;
    te_variable variables[] = {
        {"x", &x, TE_VARIABLE, NULL},
        {"y", &y, TE_VARIABLE, NULL}
    };
    te_expr *expression;
    int error = -1;
    int failures = 0;

    CHECK(nearly_equal(te_interp("2 + 3 * 4", &error), 14.0),
          "evaluate operator precedence");
    CHECK(error == 0, "report no error for a valid expression");
    CHECK(nearly_equal(te_interp("sqrt(81) + sin(pi / 2)", &error), 10.0),
          "evaluate standard math functions and constants");

    expression = te_compile("sqrt(x^2 + y^2)", variables, 2, &error);
    CHECK(expression != NULL && error == 0,
          "compile an expression with bound variables");
    if (expression != NULL) {
        CHECK(nearly_equal(te_eval(expression), 5.0),
              "evaluate compiled variables");
        x = 5.0;
        y = 12.0;
        CHECK(nearly_equal(te_eval(expression), 13.0),
              "reuse a compiled expression after variable changes");
        te_free(expression);
    }

    CHECK(isnan(te_interp("2 + * 3", &error)),
          "return NaN for invalid syntax");
    CHECK(error > 0, "report the invalid syntax position");

    if (failures != 0) {
        fprintf(stderr, "TinyExpr consumer test failed: %d assertion(s)\n",
                failures);
        return 1;
    }
    puts("TinyExpr consumer test passed: 8 assertions");
    return 0;
}
