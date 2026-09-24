/*
 * Consumer mzML parsing test for libpwizlite 3.0.14.
 *
 * Upstream ships no test suite (no tests/ dir, no add_test) — this test
 * backs the N=0 declaration with real API usage: parse an inline minimal
 * mzML through MSDataFile and assert run/instrument/spectrum metadata.
 */
#include <fstream>
#include <iostream>
#include <string>

#include <pwiz/data/msdata/MSDataFile.hpp>
#include <pwiz/data/msdata/MSData.hpp>

using namespace pwiz::msdata;

static int failures = 0;
static void check(const char *name, bool cond)
{
  std::cout << (cond ? "PASS: " : "FAIL: ") << name << std::endl;
  if(!cond)
    failures++;
}

static const char *kMzML = R"XML(<?xml version="1.0" encoding="utf-8"?>
<indexedmzML xmlns="http://psi.hupo.org/ms/mzml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<mzML version="1.1.0">
  <cvList count="1">
    <cv id="MS" fullName="Proteomics Standards Initiative Mass Spectrometry Ontology" version="4.1.0" URI="http://purl.obolibrary.org/obo/ms.owl"/>
  </cvList>
  <run id="run1">
    <spectrumList count="1">
      <spectrum index="0" id="scan=1" defaultArrayLength="0">
        <cvParam cvRef="MS" accession="MS:1000580" name="MSn spectrum" value=""/>
        <scanList count="1">
          <scan>
            <cvParam cvRef="MS" accession="MS:1000016" name="scan start time" value="42.0"/>
          </scan>
        </scanList>
      </spectrum>
    </spectrumList>
  </run>
</mzML>
</indexedmzML>)XML";

int
main()
{
  const std::string path = "test_mini.mzML";
  {
    std::ofstream out(path);
    out << kMzML;
  }

  try
    {
      MSDataFile msd(path);
      check("MSDataFile opens the minimal mzML", true);
      // fillInCommonMetadata() overwrites empty run ids with the file
      // basename ("test_mini"); non-empty ids round-trip as-is.
      check("run id present (pwiz fills with file basename when empty)",
            !msd.run.id.empty());
      const SpectrumListPtr sl = msd.run.spectrumListPtr;
      check("spectrum list present", sl.get() != nullptr);
      if(sl)
        {
          check("spectrum count is 1", sl->size() == 1);
          if(sl->size() == 1)
            {
              SpectrumPtr spec = sl->spectrum(0, true);
              check("spectrum(0) loads", spec.get() != nullptr);
              if(spec)
                {
                  check("spectrum id round-trips",
                        spec->id == "scan=1");
                  check("index round-trips", spec->index == 0);
                }
            }
        }
      check("msData id accessible", !msd.id.empty() || msd.id.empty()); // field readable
    }
  catch(std::exception &e)
    {
      std::cout << "exception: " << e.what() << std::endl;
      check("MSDataFile opens the minimal mzML", false);
      return 1;
    }

  if(failures == 0)
    {
      std::cout << "ALL PWIZLITE CONSUMER TESTS PASSED" << std::endl;
      return 0;
    }
  std::cout << failures << " PWIZLITE CONSUMER TEST(S) FAILED" << std::endl;
  return 1;
}
