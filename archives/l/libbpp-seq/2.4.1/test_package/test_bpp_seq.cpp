// Consumer test for libbpp-seq 2.4.1 — exercises the real public API.
// 8 explicit checks; each passing check prints "CHECK OK <n>/8" so the
// conanfile.py test() can count them as machine evidence (exit-0-alone
// is not proof).
#include <iostream>
#include <string>

#include <Bpp/Seq/Alphabet/AlphabetTools.h>
#include <Bpp/Seq/Alphabet/CodonAlphabet.h>
#include <Bpp/Seq/Alphabet/DNA.h>
#include <Bpp/Seq/Alphabet/ProteicAlphabet.h>
#include <Bpp/Seq/Alphabet/RNA.h>
#include <Bpp/Seq/Container/VectorSequenceContainer.h>
#include <Bpp/Seq/SequenceTools.h>

namespace {
int g_check = 0;
bool Require(bool condition, const char* message) {
  ++g_check;
  if (!condition) {
    std::cerr << "CHECK FAIL " << g_check << "/8: " << message << std::endl;
    return false;
  }
  std::cout << "CHECK OK " << g_check << "/8: " << message << std::endl;
  return true;
}
}  // namespace

int main() {
  using namespace bpp;

  // 1-2: alphabet instantiation + type detection (mirrors test_alphabets.cpp).
  DNA dna;
  RNA rna;
  ProteicAlphabet proteic;
  if (!Require(AlphabetTools::isDNAAlphabet(&dna), "DNA recognised as DNA alphabet")) return 1;
  if (!Require(AlphabetTools::isRNAAlphabet(&rna), "RNA recognised as RNA alphabet")) return 1;

  // 3: codon alphabet over RNA.
  CodonAlphabet codon(&rna);
  if (!Require(AlphabetTools::isCodonAlphabet(&codon), "CodonAlphabet recognised")) return 1;

  // 4-5: BasicSequence motif search (mirrors test_sequences.cpp).
  BasicSequence seq("test DNA", "ATTTCGTCGTTGATCA", &AlphabetTools::DNA_ALPHABET);
  BasicSequence motif("motif", "TCG", &AlphabetTools::DNA_ALPHABET);
  const size_t pos = SequenceTools::findFirstOf(seq, motif);
  if (!Require(pos == 3, "motif TCG found at position 3")) return 1;
  if (!Require(seq.size() == 16, "sequence length is 16")) return 1;

  // 6-8: proteic alphabet + sequence container round-trip.
  if (!Require(AlphabetTools::isProteicAlphabet(&proteic), "proteic alphabet recognised")) return 1;
  VectorSequenceContainer container(&AlphabetTools::DNA_ALPHABET);
  container.addSequence(seq, false);
  if (!Require(container.getNumberOfSequences() == 1, "container holds 1 sequence")) return 1;

  // 8: container sequence content survives the round-trip.
  const Sequence& back = container.getSequence(0);
  if (!Require(back.toString() == "ATTTCGTCGTTGATCA", "container round-trip preserves content")) return 1;

  return 0;
}
