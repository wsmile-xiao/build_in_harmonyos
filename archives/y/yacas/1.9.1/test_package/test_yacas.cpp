/* Consumer test for yacas/1.9.1: drives the CYacas engine API with
 * arithmetic and algebra expressions, asserting exact results.
 * argv[1] = path to the package's share/yacas/scripts directory
 * (the infix operators live in the script library — same as the
 * upstream console, which declares the rootdir then loads
 * yacasinit.ys).
 */
#include <iostream>
#include <sstream>
#include <string>

#include <yacas/yacas.h>

static int failures = 0;

static void check(CYacas &engine, const char *expr, const char *expected) {
    engine.Evaluate(expr);
    std::string got = engine.Result();
    if (!got.empty() && got.back() == ';')
        got.pop_back();
    if (!engine.IsError() && got == expected) {
        std::cout << "ok: " << expr << " => " << got << "\n";
    } else {
        std::cout << "FAIL: " << expr << " => \"" << got << "\" (want \""
                  << expected << "\") err=" << engine.Error() << "\n";
        failures++;
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cout << "usage: test_yacas <scripts-dir>\n";
        return 2;
    }
    std::ostringstream sink;
    CYacas engine(sink);

    /* load the script library shipped in the package */
    std::string dir = argv[1];
    if (!dir.empty() && dir.back() != '/')
        dir += '/';
    engine.Evaluate("DefaultDirectory(\"" + dir + "\");");
    engine.Evaluate("Load(\"yacasinit.ys\");");
    if (engine.IsError()) {
        std::cout << "FAIL: loading yacasinit.ys: " << engine.Error()
                  << "\n";
        return 1;
    }
    std::cout << "ok: script library loaded\n";

    check(engine, "2+3;", "5");
    check(engine, "Expand((x+1)^2);", "x^2+2*x+1");
    check(engine, "Factor(x^2-1);", "(x+1)*(x-1)");
    check(engine, "D(x) x^3;", "3*x^2");
    check(engine, "1/3+1/6;", "1/2");

    std::cout << "failed=" << failures << "\n";
    return failures == 0 ? 0 : 1;
}
