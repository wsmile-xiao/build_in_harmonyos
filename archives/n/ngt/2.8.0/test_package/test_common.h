// test_common.h — shared helpers for ngt/2.8.0 test_package consumer tests.
// Each scenario compiles into its own executable; this header only provides
// deterministic data generation and a lightweight assertion counter so every
// test binary reports a real, counted set of checks (no print-only "tests").
#pragma once

#include <NGT/Index.h>

#include <cmath>
#include <cstdio>
#include <random>
#include <string>
#include <vector>

// ---- per-process assertion accounting -------------------------------
static int g_checks = 0;
static int g_failures = 0;
static const char *g_ctx = "";

#define SETCTX(s)     \
  do {                \
    g_ctx = (s);      \
  } while (0)

#define CHECK(cond, msg)                                      \
  do {                                                        \
    ++g_checks;                                               \
    if (!(cond)) {                                            \
      std::fprintf(stderr, "FAIL [%s]: %s\n", g_ctx, (msg));  \
      ++g_failures;                                           \
    }                                                         \
  } while (0)

// Prints the summary and returns process exit code (0 = all checks passed).
inline int finishReport(const char *name) {
  if (g_failures == 0) {
    std::printf("PASS %-20s checks=%d failures=0\n", name, g_checks);
    return 0;
  }
  std::printf("FAIL %-20s checks=%d failures=%d\n", name, g_checks, g_failures);
  return 1;
}

// ---- deterministic synthetic data ------------------------------------
inline std::vector<std::vector<float>> genFloatData(int n, int dim, unsigned seed) {
  std::vector<std::vector<float>> data(n, std::vector<float>(dim));
  std::mt19937 rng(seed);
  std::uniform_real_distribution<float> dist(1.0f, 10.0f);
  for (auto &v : data)
    for (auto &x : v) x = dist(rng);
  return data;
}

inline std::vector<std::vector<uint8_t>> genUint8Data(int n, int dim, unsigned seed) {
  std::vector<std::vector<uint8_t>> data(n, std::vector<uint8_t>(dim));
  std::mt19937 rng(seed);
  std::uniform_int_distribution<int> dist(0, 255);
  for (auto &v : data)
    for (auto &x : v) x = static_cast<uint8_t>(dist(rng));
  return data;
}

// ---- self-match query: top-1 of data[q] must be object q+1 (1-based NGT
// ids) with distance ~ 0.  Returns true when the query result is sane so the
// caller can stop early; assertions themselves are counted via CHECK().
inline bool runSelfQuery(NGT::Index &index, const std::vector<float> &query, int expectId, int qIdx) {
  NGT::SearchQuery sq(query);
  NGT::ObjectDistances objs;
  sq.setResults(&objs);
  sq.setSize(5);
  sq.setEpsilon(0.1);
  index.search(sq);
  char msg_id[160], msg_d[160];
  std::snprintf(msg_id, sizeof(msg_id), "q%d: top-1 is the query itself (id=%d)", qIdx, expectId);
  std::snprintf(msg_d, sizeof(msg_d), "q%d: top-1 distance ~ 0", qIdx);
  if (objs.empty()) {
    std::snprintf(msg_id, sizeof(msg_id), "q%d: result set is empty", qIdx);
    CHECK(false, msg_id);
    return false;
  }
  CHECK(static_cast<int>(objs[0].id) == expectId, msg_id);
  CHECK(std::fabs(objs[0].distance) < 1e-3, msg_d);
  return objs[0].id == static_cast<NGT::ObjectID>(expectId);
}

// uint8 overload
inline bool runSelfQueryU8(NGT::Index &index, const std::vector<uint8_t> &query, int expectId, int qIdx) {
  NGT::SearchQuery sq(query);
  NGT::ObjectDistances objs;
  sq.setResults(&objs);
  sq.setSize(5);
  sq.setEpsilon(0.1);
  index.search(sq);
  char msg_id[160], msg_d[160];
  std::snprintf(msg_id, sizeof(msg_id), "q%d: top-1 is the query itself (id=%d)", qIdx, expectId);
  std::snprintf(msg_d, sizeof(msg_d), "q%d: top-1 distance ~ 0", qIdx);
  if (objs.empty()) {
    std::snprintf(msg_id, sizeof(msg_id), "q%d: result set is empty", qIdx);
    CHECK(false, msg_id);
    return false;
  }
  CHECK(static_cast<int>(objs[0].id) == expectId, msg_id);
  CHECK(std::fabs(objs[0].distance) < 1e-3, msg_d);
  return objs[0].id == static_cast<NGT::ObjectID>(expectId);
}
