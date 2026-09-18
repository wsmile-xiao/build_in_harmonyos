// Consumer test for the header-only libbiosoup-dev package (0.11.0).
#include <biosoup/nucleic_acid.hpp>
#include <biosoup/overlap.hpp>
#include <biosoup/sequence.hpp>
#include <biosoup/timer.hpp>

#include <atomic>
#include <cstdio>
#include <stdexcept>
#include <string>

std::atomic<std::uint32_t> biosoup::NucleicAcid::num_objects{0};
std::atomic<std::uint32_t> biosoup::Sequence::num_objects{0};

static int g_checks = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        ++g_checks;                                                            \
        if (!(cond)) {                                                         \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main() {
    using namespace biosoup;  // NOLINT

    // Non-nucleotide input must be rejected.
    bool threw = false;
    try {
        NucleicAcid bad{"test", "EFIJLOPQUXZ"};
    } catch (const std::invalid_argument &) {
        threw = true;
    }
    CHECK(threw);

    // 2-bit encoding + in-place inflation (values taken from upstream tests).
    NucleicAcid s{"test",
                  "AaAaCcCcGgGgTtTt------ACGTRYKMSWBDHVN-nvhdbwsmkyrtgca------tTtTgGgGcCcCaAaA"};
    CHECK(s.name == "test");
    CHECK(s.Code(16) == 0);
    CHECK(s.Code(23) == 1);
    CHECK(s.Code(35) == 2);
    CHECK(s.Code(59) == 3);
    CHECK(s.InflateData() ==
          "AAAACCCCGGGGTTTTAAAAAAACGTATGCCACATGAAAGTACACCGTATGCAAAAAAATTTTGGGGCCCCAAAA");
    CHECK(s.InflateData(34, 7) == "TGAAAGT");
    CHECK(s.InflateData(75, 42) == "");

    // Sequence reverse-complement (upstream expectation).
    Sequence seq{"Test", "ACGTURYKMSWBDHVN", "0123456789:;<=>?"};
    seq.ReverseAndComplement();
    CHECK(seq.data == "NBDHVWSKMRYAACGT");
    CHECK(seq.quality == "?>=<;:9876543210");

    // Overlap is a plain data struct.
    Overlap o{0, 1, 10, 1, 5, 15, 7, std::string("10M"), true};
    CHECK(o.lhs_id == 0 && o.rhs_id == 1 && o.score == 7);
    CHECK(o.strand == true && o.alignment == "10M");

    // Timer measures a non-negative interval.
    Timer t;
    t.Start();
    for (volatile int i = 0; i < 100000; ++i) {
    }
    CHECK(t.Stop() >= 0.0);

    std::printf("biosoup consumer test PASS (%d checks)\n", g_checks);
    return 0;
}
