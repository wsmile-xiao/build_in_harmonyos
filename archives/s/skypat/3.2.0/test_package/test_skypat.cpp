// Consumer-side test for the skypat package (real framework API usage).
//
// Verifies, from a consumer's point of view:
//   1. test cases register (SKYPAT_F) and run through Test::Initialize/RunAll;
//   2. the assertion machinery (EXPECT_*/ASSERT_*) evaluates correctly;
//   3. the timed PERFORM() path runs and reports truthful numbers even when
//      the kernel denies perf_event_open at run time (graceful degradation:
//      intervals come from a real clock source, counters report 0, no abort);
//   4. the CSVResultPrinter output carries the post-run intervals used for
//      the checks below.
#include <skypat/skypat.h>
#include <skypat/Listeners/CSVResultPrinter.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

namespace {

volatile std::uint64_t g_Sink = 0;

void burnCpu(std::uint64_t pRounds) {
  std::uint64_t x = 1;
  for (std::uint64_t i = 0; i < pRounds; ++i)
    x = x * 1664525u + 1013904223u;
  g_Sink = x;
}

// The CSV result file lives next to the test executable.
std::string csvPathFor(const char* pArgv0) {
  std::string path(pArgv0 != NULL ? pArgv0 : "");
  const std::string::size_type pos = path.find_last_of("/\\");
  if (pos == std::string::npos)
    return "skypat-test-results.csv";
  return path.substr(0, pos + 1) + "skypat-test-results.csv";
}

// Reads the "<test name>,<interval>,..." row written by CSVResultPrinter.
bool readIntervals(const std::string& pPath, const std::string& pTestName,
                   std::vector<std::uint64_t>& pOut) {
  std::ifstream in(pPath.c_str());
  if (!in.is_open())
    return false;
  std::string line;
  while (std::getline(in, line)) {
    if (line.size() <= pTestName.size() ||
        0 != line.compare(0, pTestName.size(), pTestName) ||
        line[pTestName.size()] != ',')
      continue;
    pOut.clear();
    const char* p = line.c_str() + pTestName.size() + 1;
    while (*p != '\0') {
      char* end = NULL;
      const std::uint64_t value = std::strtoull(p, &end, 10);
      if (end == p)
        break;
      pOut.push_back(value);
      p = end;
      if (*p == ',')
        ++p;
    }
    return !pOut.empty();
  }
  return false;
}

}  // namespace

class ConsumerFixture : public skypat::Test {
public:
  ConsumerFixture() : m_Base(0) {}

  virtual void SetUp() { m_Base = 41; }
  virtual void TearDown() { m_Base = 0; }

protected:
  int m_Base;
};

SKYPAT_C(ConsumerFixture, fixture_assertions_evaluate) {
  EXPECT_EQ(2 + 2, 4);
  EXPECT_NE(1, 2);
  EXPECT_LT(3, 4);
  EXPECT_GE(4, 4);
  ASSERT_TRUE(m_Base == 41);
}

SKYPAT_F(ConsumerFixture, perform_reports_plausible_intervals) {
  PERFORM(skypat::CONTEXT_SWITCHES) {
    burnCpu(1000);
  }
  PERFORM(skypat::CONTEXT_SWITCHES) {
    skypat::Test::Sleep(20);  // at least 20 ms must elapse
  }
  EXPECT_NE(static_cast<std::uint64_t>(g_Sink), 0u);
}

int main(int argc, char* argv[]) {
  const std::string csvPath = csvPathFor(argc > 0 ? argv[0] : NULL);
  std::remove(csvPath.c_str());

  skypat::Test::Initialize(argc, argv);

  // Also collect the machine-readable result CSV (public listener API).
  skypat::CSVResultPrinter* csvPrinter = new skypat::CSVResultPrinter();
  if (csvPrinter->open(csvPath)) {
    skypat::testing::UnitTest::self()->repeater().add(csvPrinter);
  } else {
    std::fprintf(stderr, "WARNING: cannot open CSV result file '%s'\n",
                 csvPath.c_str());
    delete csvPrinter;
  }

  skypat::Test::RunAll();

  skypat::testing::UnitTest* unitTest = skypat::testing::UnitTest::self();
  if (unitTest->getNumOfTests() != 2) {
    std::fprintf(stderr, "FAIL: expected 2 registered tests, got %u\n",
                 unitTest->getNumOfTests());
    return EXIT_FAILURE;
  }
  if (unitTest->getNumOfFails() != 0) {
    std::fprintf(stderr, "FAIL: %u assertion(s) failed\n",
                 unitTest->getNumOfFails());
    return EXIT_FAILURE;
  }

  std::vector<std::uint64_t> intervals;
  if (!readIntervals(csvPath, "perform_reports_plausible_intervals",
                     intervals) || intervals.size() != 2) {
    std::fprintf(stderr,
                 "FAIL: expected 2 PERFORM() intervals in '%s'\n",
                 csvPath.c_str());
    return EXIT_FAILURE;
  }

  const std::uint64_t fast = intervals[0];
  const std::uint64_t slept = intervals[1];
  if (fast >= 10000000000ULL) {
    std::fprintf(stderr,
                 "FAIL: first PERFORM() interval is not a real duration "
                 "(%llu ns)\n", (unsigned long long)fast);
    return EXIT_FAILURE;
  }
  if (slept < 20000000ULL) {
    std::fprintf(stderr,
                 "FAIL: second PERFORM() did not measure the 20 ms sleep "
                 "(%llu ns)\n", (unsigned long long)slept);
    return EXIT_FAILURE;
  }
  if (slept <= fast) {
    std::fprintf(stderr,
                 "FAIL: intervals do not track elapsed time "
                 "(%llu ns vs %llu ns)\n",
                 (unsigned long long)fast, (unsigned long long)slept);
    return EXIT_FAILURE;
  }

  std::printf("skypat consumer test: PASSED "
              "(2 tests, PERFORM() intervals %llu ns / %llu ns)\n",
              (unsigned long long)fast, (unsigned long long)slept);
  return EXIT_SUCCESS;
}
