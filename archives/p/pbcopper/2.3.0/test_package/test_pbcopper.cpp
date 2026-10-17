// test_pbcopper.cpp - consumer verification for pbcopper 2.3.0.
// Exercises real public APIs: Data::Interval, Data::Cigar,
// Utility::Join/SIStringToInt and Pbcopper::LibraryInfo.
// Prints one CHECK line per assertion and a final "N/M checks passed" line
// parsed by test_package/conanfile.py (cppdap precedent). No empty stub:
// every check calls into libpbcopper and has a failure exit path.
#include <pbcopper/LibraryInfo.h>
#include <pbcopper/data/Cigar.h>
#include <pbcopper/data/Interval.h>
#include <pbcopper/utility/StringUtils.h>

#include <iostream>
#include <string>
#include <vector>

static int g_checks = 0;
static int g_passed = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        ++g_checks;                                                   \
        if (cond) {                                                   \
            ++g_passed;                                               \
            std::cout << "CHECK " << g_checks << " passed: " << msg   \
                      << "\n";                                        \
        } else {                                                      \
            std::cout << "CHECK " << g_checks << " FAILED: " << msg   \
                      << "\n";                                        \
        }                                                             \
    } while (0)

int main()
{
    // 1: Interval explicit construction retains endpoints.
    {
        const PacBio::Data::Interval iv{5, 8};
        CHECK(iv.Start() == 5 && iv.End() == 8, "Interval{5,8} endpoints");
    }
    // 2: Interval equality / inequality operators.
    {
        const PacBio::Data::Interval a{5, 8};
        const PacBio::Data::Interval b{5, 8};
        const PacBio::Data::Interval c{20, 40};
        CHECK(a == b && !(a == c), "Interval equality operators");
    }
    // 3: Cigar string round-trip through the real parser.
    {
        const PacBio::Data::Cigar cigar =
            PacBio::Data::Cigar::FromStdString("10=5X");
        CHECK(cigar.ToStdString() == "10=5X", "Cigar 10=5X round-trip");
    }
    // 4: CigarOperation enum/char mapping (no stub: validates AM/Insertion).
    {
        using Op = PacBio::Data::CigarOperation;
        using Type = PacBio::Data::CigarOperationType;
        CHECK(Op::TypeToChar(Type::ALIGNMENT_MATCH) == 'M' &&
                  Op::TypeToChar(Type::INSERTION) == 'I',
              "CigarOperation TypeToChar M/I");
    }
    // 5: Utility::Join with string separator.
    {
        const std::string joined = PacBio::Utility::Join(
            std::vector<std::string>{"a", "b", "c"}, ",");
        CHECK(joined == "a,b,c", "Utility::Join string separator");
    }
    // 6: Utility::SIStringToInt SI suffix parsing.
    {
        CHECK(PacBio::Utility::SIStringToInt("20k") == 20000,
              "Utility::SIStringToInt 20k");
    }
    // 7: LibraryInfo reports a non-empty release string.
    {
        const PacBio::Library::Info info = PacBio::Pbcopper::LibraryInfo();
        CHECK(!info.Release.empty() && !info.Name.empty(),
              "LibraryInfo name/release non-empty");
    }
    // 8: ScientificNotationToInt handles exponent input.
    {
        CHECK(PacBio::Utility::ScientificNotationToInt("1e3") == 1000,
              "Utility::ScientificNotationToInt 1e3");
    }

    std::cout << g_passed << "/" << g_checks << " checks passed\n";
    return (g_passed == g_checks && g_checks == 8) ? 0 : 1;
}
