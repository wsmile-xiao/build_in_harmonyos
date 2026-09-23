/*  test_parser.cpp - C++ API consumer test for boolstuff on OHOS.

    Exercises the public C++ API of the installed library the same way the
    upstream examples do: parse, convert to DNF, inspect DNF terms, detect
    parse errors.  Expected DNF strings follow the library's documented
    semantics (distributive expansion with x&x -> x and x|!x deduplication,
    no absorption), as verified with the upstream booldnf tool and the
    upstream test-cases.txt file.  The exit code is the number of failures.
*/

#include <boolstuff/BoolExprParser.h>

#include <iostream>
#include <sstream>
#include <string>

using namespace boolstuff;

static int failures = 0;
static int checks = 0;

static void check(bool condition, const std::string &what)
{
    checks++;
    std::cout << (condition ? "PASS: " : "FAIL: ") << what << "\n";
    if (!condition)
        failures++;
}

/*  Parses 'input', converts it to DNF and compares the printed DNF
    against 'expected'.  A NULL DNF (logically FALSE expression) must
    be encoded as "FALSE".
*/
static void check_dnf(const std::string &input, const std::string &expected)
{
    BoolExprParser parser;
    BoolExpr<std::string> *expr = NULL;
    BoolExpr<std::string> *dnf = NULL;
    try
    {
        expr = parser.parse(input);
        check(expr != NULL, "parse(" + input + ") returns a tree");
        dnf = BoolExpr<std::string>::getDisjunctiveNormalForm(expr);
        expr = NULL;  // consumed by the DNF conversion
        std::ostringstream out;
        if (dnf != NULL)
            out << dnf;
        else
            out << "FALSE";
        check(out.str() == expected,
              "DNF(" + input + ") == " + expected + " (got " + out.str() + ")");
    }
    catch (BoolExprParser::Error &err)
    {
        checks++;
        failures++;
        std::cout << "FAIL: unexpected parse error on '" << input
                  << "': code " << err.code << " at index " << err.index << "\n";
    }
    delete dnf;
    delete expr;
}

static void check_parse_error(const std::string &input)
{
    BoolExprParser parser;
    try
    {
        BoolExpr<std::string> *expr = parser.parse(input);
        delete expr;
        check(false, "parse(" + input + ") rejects invalid input");
    }
    catch (BoolExprParser::Error &)
    {
        check(true, "parse(" + input + ") rejects invalid input");
    }
}

int main()
{
    // The canonical tree/DNF case from the upstream C API test program.
    check_dnf("a&!(b|c&d)", "a&!b&!c|a&!b&!d");

    // Distributivity, De Morgan, double negation, x&x simplification
    // (expected values verified against the upstream booldnf tool).
    check_dnf("(a|b)&(a|c)", "a|a&b|a&c|b&c");
    check_dnf("!(a&b)", "!a|!b");
    check_dnf("!!a", "a");
    check_dnf("a&!a", "a&!a");
    check_dnf("a&a", "a");
    check_dnf("a|(a&b)", "a|a&b");
    check_dnf("a|!a", "a|!a");
    check_dnf("a&(b|c)", "a&b|a&c");

    // isDisjunctiveNormalForm on a DNF built by the parser.
    {
        BoolExprParser parser;
        BoolExpr<std::string> *expr = parser.parse("a&b|!c");
        check(expr != NULL && expr->isDisjunctiveNormalForm(),
              "isDisjunctiveNormalForm(a&b|!c)");

        // DNF term roots and per-term variables on that DNF tree.
        if (expr != NULL)
        {
            typedef std::vector<const BoolExpr<std::string> *> V;
            V terms;
            expr->getDNFTermRoots(inserter(terms, terms.end()));
            check(terms.size() == 2, "DNF of a&b|!c has 2 terms");
            delete expr;
        }
    }

    // Parse errors must throw the documented exception.
    check_parse_error("a&");
    check_parse_error("(a|b");
    check_parse_error("&a");

    std::cout << checks << " checks, " << failures << " failures\n";
    return failures == 0 ? 0 : 1;
}
