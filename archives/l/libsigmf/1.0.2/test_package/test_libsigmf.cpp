// Consumer test for libsigmf 1.0.2 (HarmonyOS PC conan test_package).
//
// Builds a SigMF record with the core + antenna namespaces, serializes it
// to JSON, verifies the values with explicit runtime checks (plain ifs, no
// assert(), so the checks stay active under Release/NDEBUG), and verifies a
// from_json roundtrip. Prints one line per check plus a final summary.
//
// Field-type note (verified against upstream v1.0.2 flatbuffers headers):
// string fields (author/description/...) are plain std::string (direct ==),
// numeric/bool fields (sample_rate/frequency/sample_count/...) are
// flatbuffers::Optional<T> (checked via has_value() + operator*). The
// previous revision wrongly called .value_or() on std::string and failed
// to compile (true-device evidence 2026-09-17).
#include <sigmf/sigmf.h>

#include <nlohmann/json.hpp>

#include <iostream>
#include <string>

using namespace sigmf;

namespace {

int g_passed = 0;

bool check(int id, const char *name, bool cond) {
  std::cout << "CHECK " << id << " " << name << ": " << (cond ? "ok" : "FAIL") << std::endl;
  if (cond) {
    ++g_passed;
    return true;
  }
  return false;
}

}  // namespace

int main() {
  bool ok = true;

  SigMF<Global<core::DescrT, antenna::DescrT>, Capture<core::DescrT>,
        Annotation<core::DescrT, antenna::DescrT> >
      record;
  record.global.access<core::GlobalT>().author = "hmbs-test";
  record.global.access<core::GlobalT>().description = "consumer probe";
  record.global.access<core::GlobalT>().sample_rate = 1000000.0;
  record.global.access<antenna::GlobalT>().mobile = true;
  record.global.access<antenna::GlobalT>().gain = 12.5;

  auto &cap = record.captures.create_new();
  cap.get<core::DescrT>().frequency = 915e6;
  cap.get<core::DescrT>().sample_start = 42;

  auto anno = Annotation<core::DescrT, antenna::DescrT>();
  anno.access<core::AnnotationT>().sample_count = 1024;
  anno.access<core::AnnotationT>().description = "probe annotation";
  anno.access<core::AnnotationT>().generator = "hmbs";
  record.annotations.emplace_back(anno);

  // 1: plain std::string field, direct comparison.
  ok &= check(1, "global.author",
              record.global.access<core::GlobalT>().author == "hmbs-test");
  // 2: flatbuffers::Optional<double> field, has_value + deref.
  {
    const auto &freq = record.captures[0].get<core::DescrT>().frequency;
    ok &= check(2, "capture.frequency", freq.has_value() && *freq == 915e6);
  }

  // 3-4: serialized JSON carries the core + antenna namespaced keys.
  const std::string dumped = json(record).dump();
  ok &= check(3, "json.core:author", dumped.find("\"core:author\":\"hmbs-test\"") != std::string::npos);
  ok &= check(4, "json.antenna:mobile", dumped.find("\"antenna:mobile\":true") != std::string::npos);

  // 5-6: from_json roundtrip restores every field that was set.
  SigMF<Global<core::DescrT, antenna::DescrT>, Capture<core::DescrT>,
        Annotation<core::DescrT, antenna::DescrT> >
      restored = json::parse(dumped);
  {
    const auto &sr = restored.global.access<core::GlobalT>().sample_rate;
    ok &= check(5, "roundtrip.sample_rate", sr.has_value() && *sr == 1000000.0);
  }
  {
    bool anno_ok = restored.annotations.size() == 1;
    if (anno_ok) {
      const auto &sc = restored.annotations[0].access<core::AnnotationT>().sample_count;
      anno_ok = sc.has_value() && *sc == 1024;
    }
    ok &= check(6, "roundtrip.annotation", anno_ok);
  }

  std::cout << "CHECKS " << g_passed << "/6 passed" << std::endl;
  if (!ok || g_passed != 6) {
    std::cout << "test_libsigmf FAILED" << std::endl;
    return 1;
  }
  std::cout << "test_libsigmf passed" << std::endl;
  return 0;
}
