// test_objecttype — NGT object-type coverage on top of the L2 / Hamming
// distances: float + uint8 (Integer-1) object spaces.  Each object type is
// written through the templated NGT::Index::append(), indexed (ANNG) and
// verified by self-query after reopen.
// 3 scenarios × (property readback 2 + 3 self-queries × 2) = 24 checks.
#include "test_common.h"

#include <cstdio>


static void runFloatL2() {
  const char *name = "float-L2";
  auto data = genFloatData(120, 16, 201);
  SETCTX(name);
  try {
    NGT::Property prop;
    prop.dimension = 16;
    prop.objectType = NGT::ObjectSpace::ObjectType::Float;
    prop.distanceType = NGT::ObjectSpace::DistanceType::DistanceTypeL2;
    NGT::Index::create("idx_otype_float", prop);
    {
      NGT::Index index("idx_otype_float");
      for (auto &v : data) index.append(v);
      index.createIndex(16);
      index.save();
    }
    NGT::Index r("idx_otype_float");
    NGT::Property got;
    r.getProperty(got);
    CHECK(static_cast<int>(got.objectType) == static_cast<int>(NGT::ObjectSpace::ObjectType::Float),
          "float index readback objectType=Float");
    CHECK(static_cast<int>(got.dimension) == 16, "float index readback dimension");
    for (int q = 0; q < 3; ++q) runSelfQuery(r, data[q], q + 1, q);
  } catch (NGT::Exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: NGT exception: %s\n", name, e.what());
  } catch (std::exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: std exception: %s\n", name, e.what());
  }
}

static void runUint8L2() {
  const char *name = "uint8-L2";
  auto data = genUint8Data(120, 16, 202);
  SETCTX(name);
  try {
    NGT::Property prop;
    prop.dimension = 16;
    prop.objectType = NGT::ObjectSpace::ObjectType::Uint8;
    prop.distanceType = NGT::ObjectSpace::DistanceType::DistanceTypeL2;
    NGT::Index::create("idx_otype_u8_l2", prop);
    {
      NGT::Index index("idx_otype_u8_l2");
      for (auto &v : data) index.append(v);
      index.createIndex(16);
      index.save();
    }
    NGT::Index r("idx_otype_u8_l2");
    NGT::Property got;
    r.getProperty(got);
    CHECK(static_cast<int>(got.objectType) == static_cast<int>(NGT::ObjectSpace::ObjectType::Uint8),
          "uint8 index readback objectType=Uint8");
    CHECK(static_cast<int>(got.dimension) == 16, "uint8 index readback dimension");
    for (int q = 0; q < 3; ++q) runSelfQueryU8(r, data[q], q + 1, q);
  } catch (NGT::Exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: NGT exception: %s\n", name, e.what());
  } catch (std::exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: std exception: %s\n", name, e.what());
  }
}

static void runUint8Hamming() {
  const char *name = "uint8-Hamming";
  auto data = genUint8Data(120, 16, 203);
  SETCTX(name);
  try {
    NGT::Property prop;
    prop.dimension = 16;
    prop.objectType = NGT::ObjectSpace::ObjectType::Uint8;
    prop.distanceType = NGT::ObjectSpace::DistanceType::DistanceTypeHamming;
    NGT::Index::create("idx_otype_u8_ham", prop);
    {
      NGT::Index index("idx_otype_u8_ham");
      for (auto &v : data) index.append(v);
      index.createIndex(16);
      index.save();
    }
    NGT::Index r("idx_otype_u8_ham");
    NGT::Property got;
    r.getProperty(got);
    CHECK(static_cast<int>(got.objectType) == static_cast<int>(NGT::ObjectSpace::ObjectType::Uint8),
          "hamming index readback objectType=Uint8");
    CHECK(static_cast<int>(got.distanceType) == static_cast<int>(NGT::ObjectSpace::DistanceType::DistanceTypeHamming),
          "hamming index readback distanceType=Hamming");
    for (int q = 0; q < 3; ++q) runSelfQueryU8(r, data[q], q + 1, q);
  } catch (NGT::Exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: NGT exception: %s\n", name, e.what());
  } catch (std::exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: std exception: %s\n", name, e.what());
  }
}

int main() {
  runFloatL2();
  runUint8L2();
  runUint8Hamming();
  return finishReport("test_objecttype");
}
