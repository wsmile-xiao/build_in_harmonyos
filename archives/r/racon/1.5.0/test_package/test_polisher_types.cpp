// test_polisher_types.cpp — racon 1.5.0 HarmonyOS consumer test (real API).
// Exercises racon::PolisherType enum + Sequence transmute path.
#include <cstdio>
#include <string>
#include "sequence.hpp"
#include "polisher.hpp"

static int g_fail = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("  PASS: %s\n", msg); } \
    else { printf("  FAIL: %s\n", msg); g_fail++; } \
} while (0)

int main() {
    printf("=== racon PolisherType/Sequence test ===\n");

    // PolisherType must expose both polishing modes.
    CHECK(racon::PolisherType::kC != racon::PolisherType::kF,
          "PolisherType kC != kF");
    CHECK(static_cast<int>(racon::PolisherType::kC) == 0,
          "PolisherType::kC == 0");
    CHECK(static_cast<int>(racon::PolisherType::kF) == 1,
          "PolisherType::kF == 1");

    // Longer sequence keeps data; reverse complement is involution.
    const std::string dna = "ACGTACGTACGT";
    auto s = racon::createSequence("contig1", dna);
    CHECK(s->data().size() == dna.size(), "long sequence size kept");
    s->create_reverse_complement();
    std::string rc1 = s->reverse_complement();
    CHECK(!rc1.empty() && rc1.size() == dna.size(),
          "reverse_complement non-empty and same length");

    // Double reverse complement returns to original orientation content:
    // build a second sequence from rc1 and compare its rc with original.
    auto s2 = racon::createSequence("rc", rc1);
    s2->create_reverse_complement();
    CHECK(s2->reverse_complement() == dna,
          "double reverse_complement restores original");

    // Empty-name sequence is still constructible (parser edge case).
    auto s3 = racon::createSequence("", "A");
    CHECK(s3->name().empty(), "empty name kept");
    CHECK(s3->data() == "A", "single base data kept");

    printf("=== result: %s (%d failures) ===\n",
           g_fail == 0 ? "ALL PASS" : "FAILED", g_fail);
    return g_fail == 0 ? 0 : 1;
}
