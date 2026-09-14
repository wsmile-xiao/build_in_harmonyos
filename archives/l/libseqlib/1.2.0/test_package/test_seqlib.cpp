#include <cassert>
#include <iostream>
#include <string>

#include "SeqLib/GenomicRegion.h"
#include "SeqLib/GenomicRegionCollection.h"
#include "SeqLib/SeqLibUtils.h"
#include "SeqLib/BamRecord.h"

int main() {
  int passed = 0;

  // 1. AddCommas formats integers with thousands separators.
  {
    std::string s = SeqLib::AddCommas(1000000);
    if (s != "1,000,000") {
      std::cerr << "FAIL AddCommas: " << s << std::endl;
      return 1;
    }
    std::cout << "PASS AddCommas: " << s << std::endl;
    ++passed;
  }

  // 2. percentCalc returns integer percentage.
  {
    int p = SeqLib::percentCalc(10, 100);
    if (p != 10) {
      std::cerr << "FAIL percentCalc: " << p << std::endl;
      return 1;
    }
    std::cout << "PASS percentCalc: " << p << std::endl;
    ++passed;
  }

  // 3. rcomplement reverse-complements a DNA string in place.
  {
    std::string seq = "ACGT";
    SeqLib::rcomplement(seq);
    if (seq != "ACGT") {  // ACGT is self reverse-complementary
      std::cerr << "FAIL rcomplement: " << seq << std::endl;
      return 1;
    }
    std::string seq2 = "AAACCC";
    SeqLib::rcomplement(seq2);
    if (seq2 != "GGGTTT") {
      std::cerr << "FAIL rcomplement2: " << seq2 << std::endl;
      return 1;
    }
    std::cout << "PASS rcomplement" << std::endl;
    ++passed;
  }

  // 4. GenomicRegion ordering and merge via GenomicRegionCollection.
  {
    SeqLib::GRC grc;
    grc.add(SeqLib::GenomicRegion(2, 10, 100));
    grc.add(SeqLib::GenomicRegion(2, 20, 110));
    grc.add(SeqLib::GenomicRegion(2, 200, 310));
    grc.MergeOverlappingIntervals();
    if (grc.size() != 2) {
      std::cerr << "FAIL GRC merge size: " << grc.size() << std::endl;
      return 1;
    }
    if (grc[0].chr != 2) {
      std::cerr << "FAIL GRC chr" << std::endl;
      return 1;
    }
    std::cout << "PASS GenomicRegionCollection merge" << std::endl;
    ++passed;
  }

  // 5. Cigar round-trip: build from string and check query length.
  {
    SeqLib::Cigar cig("10M1I10M");
    if (cig.NumQueryConsumed() != 21) {
      std::cerr << "FAIL Cigar query consumed" << std::endl;
      return 1;
    }
    std::cout << "PASS Cigar" << std::endl;
    ++passed;
  }

  std::cout << "ALL " << passed << " CHECKS PASSED" << std::endl;
  return 0;
}
