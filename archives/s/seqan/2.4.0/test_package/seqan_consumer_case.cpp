#include <seqan/align.h>
#include <seqan/find.h>
#include <seqan/index.h>
#include <seqan/score.h>
#include <seqan/sequence.h>

#include <cstdio>

namespace {

int failures = 0;

void check(bool condition, const char* message)
{
  if (condition)
    std::printf("PASS: %s\n", message);
  else
  {
    std::printf("FAIL: %s\n", message);
    ++failures;
  }
}

} // namespace

int main()
{
  using namespace seqan;

  // Consumer workflow: prepare a read, align it to a reference, search it,
  // and inspect the aligned rows. Each stage feeds the next stage.
  Dna5String reference = "GATTACAGATTACA";
  Dna5String read = "GATTACAGATTACA";

  Align<Dna5String> align;
  appendValue(rows(align), reference);
  appendValue(rows(align), read);
  Score<int, Simple> scoringScheme(2, -1, -2);
  int score = globalAlignment(align, scoringScheme, Gotoh());
  check(score == 28, "alignment stage scores the prepared read");
  check(length(row(align, 0)) == length(row(align, 1)), "alignment rows stay paired");

  Dna5String pattern = "GATTA";
  typedef Index<Dna5String> TIndex;
  TIndex index(reference);
  Finder<TIndex> indexFinder(index);
  int hits = 0;
  while (find(indexFinder, pattern))
    ++hits;
  check(hits == 2, "index stage reports both occurrences");

  Finder<Dna5String> haystackFinder(reference);
  Pattern<Dna5String, Horspool> patternObj(pattern);
  check(find(haystackFinder, patternObj), "finder stage locates the read motif");
  check(beginPosition(haystackFinder) == 0u, "finder stage reports the first hit");

  Dna5String reverse = reference;
  reverseComplement(reverse);
  check(reverse != reference, "modifier stage transforms the reference");
  check(length(reverse) == length(reference), "transformed sequence keeps its length");

  if (failures != 0)
    return 1;

  std::printf("seqan consumer workflow passed\n");
  return 0;
}
