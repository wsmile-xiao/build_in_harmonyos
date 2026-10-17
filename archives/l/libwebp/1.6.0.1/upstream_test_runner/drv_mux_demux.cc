// 上游 tests/fuzzer/mux_demux_api_fuzzer.cc 真机驱动。
// 上游源码零改动:#include 纳入本 TU,直接调用被测函数 MuxDemuxApiTest()。
// 组合:use_mux_api {0,1}(Mux API / Demux API 两路)。
#include "driver_common.h"

#include "mux_demux_api_fuzzer.cc"

int main(int argc, char** argv) {
  std::vector<std::string> seeds;
  if (LoadSeeds(argc, argv, &seeds) != 0) return 2;

  int runs = 0;
  for (const std::string& s : seeds) {
    const std::string_view sv(s.data(), s.size());
    MuxDemuxApiTest(sv, /*use_mux_api=*/false);
    MuxDemuxApiTest(sv, /*use_mux_api=*/true);
    runs += 2;
  }

  SeedSanity(seeds);
  printf("PASS mux_demux_api_fuzzer runs=%d\n", runs);
  return 0;
}
