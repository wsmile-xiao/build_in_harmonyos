/**
 * test_package for popl 1.3.0 — real API usage of the header-only program
 * options parser (popl::OptionParser / popl::Value / popl::Switch).
 */
#include <popl.hpp>
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

int main()
{
    using namespace popl;

    OptionParser op("popl test options");
    std::vector<const char*> args = {"popl", "-n", "42", "-v"};

    auto num = op.add<Value<int>>("n", "num", "a number", 0);
    auto verbose = op.add<Switch>("v", "verbose", "verbose mode");

    op.parse(args.size(), args.data());

    assert(num->value() == 42);
    assert(verbose->is_set());

    std::cout << "popl test_package OK: num=" << num->value()
              << " verbose=" << (verbose->is_set() ? "on" : "off") << "\n";
    return 0;
}
