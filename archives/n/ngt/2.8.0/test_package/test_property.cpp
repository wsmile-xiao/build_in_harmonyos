// test_property — NGT property get/set round-trip consistency.
// After saving and reopening an index, getProperty() must reproduce every
// field set at creation (dimension / objectType / distanceType / graphType).
// Feeding the very same property back through setProperty() must be a no-op
// for those fields (getProperty() still returns identical values), which
// exercises the property write path used by NGT.
// 11 checks total.
#include "test_common.h"

#include <cstdio>

static int buildFloatIndex(const char *dir) {
  auto data = genFloatData(60, 16, 701);
  NGT::Property prop;
  prop.dimension = 16;
  prop.objectType = NGT::ObjectSpace::ObjectType::Float;
  prop.distanceType = NGT::ObjectSpace::DistanceType::DistanceTypeL2;
  prop.graphType = NGT::NeighborhoodGraph::GraphType::GraphTypeANNG;
  NGT::Index::create(dir, prop);
  NGT::Index index(dir);
  for (auto &v : data) index.append(v);
  index.createIndex(16);
  index.save();
  return static_cast<int>(data.size());
}

int main() {
  const char *name = "test_property";
  SETCTX(name);
  try {
    buildFloatIndex("idx_prop_float");
    NGT::Index r("idx_prop_float");
    NGT::Property p;
    r.getProperty(p);
    CHECK(static_cast<int>(p.dimension) == 16, "float: readback dimension=16");
    CHECK(static_cast<int>(p.objectType) == static_cast<int>(NGT::ObjectSpace::ObjectType::Float),
          "float: readback objectType=Float");
    CHECK(static_cast<int>(p.distanceType) == static_cast<int>(NGT::ObjectSpace::DistanceType::DistanceTypeL2),
          "float: readback distanceType=L2");
    CHECK(static_cast<int>(p.graphType) == static_cast<int>(NGT::NeighborhoodGraph::GraphType::GraphTypeANNG),
          "float: readback graphType=ANNG");

    // setProperty round-trip: writing the read property back must leave all
    // four fields unchanged on the next getProperty().
    r.setProperty(p);
    NGT::Property p2;
    r.getProperty(p2);
    CHECK(static_cast<int>(p2.dimension) == 16, "set/get roundtrip: dimension");
    CHECK(static_cast<int>(p2.objectType) == static_cast<int>(NGT::ObjectSpace::ObjectType::Float),
          "set/get roundtrip: objectType");
    CHECK(static_cast<int>(p2.distanceType) == static_cast<int>(NGT::ObjectSpace::DistanceType::DistanceTypeL2),
          "set/get roundtrip: distanceType");
    CHECK(static_cast<int>(p2.graphType) == static_cast<int>(NGT::NeighborhoodGraph::GraphType::GraphTypeANNG),
          "set/get roundtrip: graphType");

    // a second, different object space: uint8 + Hamming
    {
      auto data = genUint8Data(60, 16, 702);
      NGT::Property uprop;
      uprop.dimension = 16;
      uprop.objectType = NGT::ObjectSpace::ObjectType::Uint8;
      uprop.distanceType = NGT::ObjectSpace::DistanceType::DistanceTypeHamming;
      NGT::Index::create("idx_prop_u8", uprop);
      NGT::Index u("idx_prop_u8");
      for (auto &v : data) u.append(v);
      u.createIndex(16);
      u.save();
      NGT::Index ur("idx_prop_u8");
      NGT::Property ug;
      ur.getProperty(ug);
      CHECK(static_cast<int>(ug.objectType) == static_cast<int>(NGT::ObjectSpace::ObjectType::Uint8),
            "uint8/hamming: readback objectType=Uint8");
      CHECK(static_cast<int>(ug.distanceType) == static_cast<int>(NGT::ObjectSpace::DistanceType::DistanceTypeHamming),
            "uint8/hamming: readback distanceType=Hamming");
      CHECK(static_cast<int>(ug.dimension) == 16, "uint8/hamming: readback dimension=16");
    }
  } catch (NGT::Exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: NGT exception: %s\n", name, e.what());
  } catch (std::exception &e) {
    ++g_checks; ++g_failures;
    std::fprintf(stderr, "FAIL [%s]: std exception: %s\n", name, e.what());
  }
  return finishReport(name);
}
