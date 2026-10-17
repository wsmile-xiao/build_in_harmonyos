// test_package for seqan 2.3.2 (header-only C++ library)
// R34: actually include and exercise SeqAn public API
#include <seqan/seq_io.h>
#include <seqan/align.h>
#include <seqan/sequence.h>

#include <string>
#include <sstream>
#include <cassert>

int main()
{
    // --- exercise seqan sequence + alignment API (real usage) ---
    seqan::Dna5String seqA = "ACGTACGT";
    seqan::Dna5String seqB = "ACGTACGT";

    // Global alignment, expect identical sequences to align end-to-end
    seqan::Align<seqan::Dna5String> align;
    seqan::resize(seqan::rows(align), 2);
    seqan::assignSource(seqan::row(align, 0), seqA);
    seqan::assignSource(seqan::row(align, 1), seqB);
    int score = seqan::globalAlignment(align, seqan::Score<int, seqan::Simple>());

    // identical 8bp sequences => perfect match score = length = 8
    assert(score == 8);

    // --- exercise seq_io: parse a small FASTQ record from memory ---
    std::stringstream ss;
    ss << "@read1\nACGTACGTACGT\n+\nIIIIIIIIIIII\n";
    seqan::SeqFileIn seqFileIn;
    if (open(seqFileIn, ss))
    {
        seqan::CharString id;
        seqan::Dna5String seq;
        readRecord(id, seq, seqFileIn);
        assert(length(seq) == 12);
    }

    // --- version sanity ---
    assert(SEQAN_VERSION_MAJOR == 2);
    assert(SEQAN_VERSION_MINOR == 3);
    assert(SEQAN_VERSION_PATCH == 2);

    return 0;
}