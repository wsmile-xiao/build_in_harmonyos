// Consumer test for the LocARNA C++ library (libLocARNA-2.0).
//
// Links the installed static libLocARNA-2.0 (which pulls ViennaRNA
// transitively) and actually constructs a LocARNA::Sequence, then exercises
// the MultipleAlignment / SeqEntry API (name() and seq() round-trip) to prove
// the library's header + link interface is consumable end-to-end on OHOS.
//
// The full Aligner/Scoring end-to-end pipeline is covered by the upstream
// Catch2 unit suite (test_locarna_lib: 22 test cases / 175 assertions) that
// runs during `make check` in the build step.
#include <LocARNA/sequence.hh>
#include <string>

int main() {
    LocARNA::Sequence s("test", "ACGUACGU");
    // LocARNA::Sequence derives from MultipleAlignment; the per-sequence name is
    // exposed via SeqEntry::name(), reached through seqentry(0).
    std::string n = s.seqentry(0).name();
    // SeqEntry::seq() returns the LocARNA 1-based string1 type; .str() yields
    // the underlying std::string.
    std::string seq = s.seqentry(0).seq().str();
    // Verify both the name and the sequence payload round-trip through the
    // LocARNA data model — a real consumer use of the library API.
    if (n != "test") return 1;
    if (seq != "ACGUACGU") return 2;
    return 0;
}
