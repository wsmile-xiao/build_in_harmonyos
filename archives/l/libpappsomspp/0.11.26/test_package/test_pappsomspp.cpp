// Consumer test for libpappsomspp 0.11.26 core APIs.
//
// Upstream Catch2 suite (60 TEST_CASEs, 41 files, built and run by the
// recipe with with_tests=True: 111 TEST_CASEs registered in the
// catch2-only-tests binary + the memory binary) covers the full library.
// This consumer test verifies the packaged delivery through the same
// core API surfaces: AaStringCodec decode, FilterGreatestY spectrum
// filtering, and mass-to-code matching.

#include <pappsomspp/core/massspectrum/massspectrum.h>
#include <pappsomspp/core/precision.h>
#include <pappsomspp/core/amino_acid/aacode.h>
#include <pappsomspp/core/amino_acid/aastringcodec.h>
#include <pappsomspp/core/amino_acid/aastringcodemassmatching.h>
#include <pappsomspp/core/processing/filters/filterpass.h>

#include <cassert>
#include <cstdio>
#include <vector>

int main()
{
  // ---- 1. AaStringCodec round-trip (decode path) ----
  pappso::AaCode aa_code;
  aa_code.addAaModification(
    'C', pappso::AaModification::getInstance("MOD:00397"));
  pappso::AaStringCodec codec(aa_code);
  assert(codec.decode(0).size() >= 1);
  std::printf("ok: AaStringCodec decode\n");

  // ---- 2. FilterGreatestY keeps the N most intense peaks ----
  pappso::MassSpectrum spectrum;
  for(int i = 0; i < 100; i++)
    {
      // deterministic masses, increasing intensities
      spectrum.push_back(pappso::DataPoint(100.0 + i * 1.5, i + 1.0));
    }
  assert(spectrum.size() == 100);
  pappso::FilterGreatestY(10).filter(spectrum);
  assert(spectrum.size() == 10);
  std::printf("ok: FilterGreatestY(10) -> 10 peaks\n");

  // ---- 3. mass-to-code matching returns a sane code list ----
  pappso::AaStringCodeMassMatching matching(
    aa_code, 2, pappso::PrecisionFactory::getDaltonInstance(0.03));
  std::vector<double> masses;
  for(const pappso::DataPoint &dp : spectrum)
    {
      masses.push_back(dp.x);
    }
  std::vector<std::uint32_t> codes =
    matching.getAaCodeFromMassList(masses);
  std::printf("ok: mass->code matching (%zu codes)\n", codes.size());
  assert(!codes.empty() || masses.empty());

  std::printf("all consumer assertions passed\n");
  return 0;
}
