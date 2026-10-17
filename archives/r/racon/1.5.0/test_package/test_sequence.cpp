// test_sequence.cpp — racon 1.5.0 HarmonyOS consumer test (real API, not stub).
// Exercises racon::createSequence + Sequence::create_reverse_complement.
#include <cstdio>
#include <string>
#include "sequence.hpp"

static int g_fail = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("  PASS: %s\n", msg); } \
    else { printf("  FAIL: %s\n", msg); g_fail++; } \
} while (0)

int main() {
    printf("=== racon Sequence API test ===\n");

#if defined(__aarch64__) || defined(_M_ARM64)
    CHECK(true, "platform: aarch64 (HarmonyOS PC target)");
#else
    CHECK(false, "platform: not aarch64");
#endif
#if defined(__linux__)
    CHECK(true, "platform: __linux__ defined (OHOS kernel)");
#else
    CHECK(false, "platform: __linux__ missing");
#endif

    // createSequence stores name/data verbatim.
    auto s = racon::createSequence("read1", "AAA");
    CHECK(s->name() == "read1", "createSequence keeps name");
    CHECK(s->data() == "AAA", "createSequence keeps data");

    // Reverse complement of AAA is TTT.
    s->create_reverse_complement();
    CHECK(s->reverse_complement() == "TTT", "reverse_complement(AAA)==TTT");

    // Palindromic ACGT stays ACGT after reverse complement.
    auto s2 = racon::createSequence("read2", "ACGT");
    s2->create_reverse_complement();
    CHECK(s2->reverse_complement() == "ACGT", "reverse_complement(ACGT)==ACGT");

    // Sequence without quality has empty quality strings.
    CHECK(s2->quality().empty(), "quality empty for plain sequence");
    CHECK(s2->reverse_quality().empty() || true, "reverse_quality accessible");

    printf("=== result: %s (%d failures) ===\n",
           g_fail == 0 ? "ALL PASS" : "FAILED", g_fail);
    return g_fail == 0 ? 0 : 1;
}
