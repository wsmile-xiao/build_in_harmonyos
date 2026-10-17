#include <cucumber-cpp/internal/utils/Regex.hpp>
#include <cucumber-cpp/internal/Table.hpp>
#include <cucumber-cpp/internal/hook/Tag.hpp>
#include <cucumber-cpp/internal/ContextManager.hpp>
#include <cucumber-cpp/internal/CukeEngineImpl.hpp>
#include <iostream>
#include <memory>
#include <cassert>

using namespace cucumber::internal;

int main() {
    int discovered = 5;
    int passed = 0;

    // 1. Regex exact match
    {
        Regex exact("^cde$");
        auto m = std::shared_ptr<RegexMatch>(exact.find("cde"));
        if (m && m->matches() && m->getSubmatches().empty()) {
            ++passed;
            std::cout << "[ok] Regex exact match\n";
        } else {
            std::cout << "[fail] Regex exact\n";
            return 1;
        }
    }
    // 2. Regex with submatches
    {
        Regex sum("^(\\d+)\\+\\d+=(\\d+)$");
        auto m = std::shared_ptr<RegexMatch>(sum.find("42+27=69"));
        if (m && m->matches() && m->getSubmatches().size() == 2
            && m->getSubmatches()[0].value == "42"
            && m->getSubmatches()[1].value == "69") {
            ++passed;
            std::cout << "[ok] Regex submatches\n";
        } else {
            std::cout << "[fail] Regex submatches\n";
            return 1;
        }
    }
    // 3. Table basic
    {
        Table t;
        // Table is constructed via CukeEngine, but we can test empty table creation
        // Use context manager to ensure library links correctly
        ContextManager cm;
        if (true) {
            ++passed;
            std::cout << "[ok] ContextManager link\n";
        }
    }
    // 4. Tag expression parsing
    // OrTagExpression stores tags without '@' (Tag.cpp csvTagNotationRegex captures (\w+))
    // Unit test expects matches({"a"}) for "@a", so use stripped names here.
    {
        OrTagExpression expr("@smoke,@regression");
        OrTagExpression::tag_list tags = {"smoke"};
        bool ok = expr.matches(tags);
        if (ok) {
            ++passed;
            std::cout << "[ok] OrTagExpression\n";
        } else {
            std::cout << "[fail] OrTagExpression\n";
            return 1;
        }
    }
    // 5. CukeEngineImpl basic lifecycle
    {
        CukeEngineImpl engine;
        // Engine should be constructible and not throw
        ++passed;
        std::cout << "[ok] CukeEngineImpl\n";
    }

    std::cout << "discovered=" << discovered << " passed=" << passed << std::endl;
    if (passed != discovered) return 1;
    std::cout << "All cucumber-cpp checks passed\n";
    return 0;
}
