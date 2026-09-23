// test_errors — NGT error / boundary paths must surface as NGT::Exception
// (never a silent crash or success):
//   1. opening an index that does not exist;
//   2. opening a path that exists but is not an NGT index;
//   3. creating an index with dimension == 0;
//   4. appending a vector whose size does not match the declared dimension;
//   5. constructing a SearchQuery with an unsupported element type.
// 5 checks.
#include "test_common.h"

#include <cstdio>
#include <fstream>

static bool throwsNgtException(void (*fn)()) {
  try {
    fn();
    return false;  // did not throw
  } catch (NGT::Exception &) {
    return true;
  } catch (std::exception &e) {
    std::fprintf(stderr, "  (unexpected std exception: %s)\n", e.what());
    return false;
  }
}

static void openMissing() { NGT::Index idx("idx_does_not_exist_xyz"); }

static void openNonIndex() {
  // create an empty regular file where an index directory is expected
  { std::ofstream f("not_an_index"); f << "x"; }
  NGT::Index idx("not_an_index");
}

static void createDimZero() {
  NGT::Property prop;
  prop.dimension = 0;  // invalid: create must reject it
  NGT::Index::create("idx_err_dim0", prop);
}

static void appendWrongDim() {
  NGT::Property prop;
  prop.dimension = 8;
  NGT::Index::create("idx_err_append", prop);
  NGT::Index idx("idx_err_append");
  std::vector<float> shortv(4, 1.0f);  // dimension mismatch
  idx.append(shortv);
}

static void badQueryType() {
  std::vector<int> q(4, 1);  // int is not a supported NGT query type
  NGT::SearchQuery sq(q);
}

int main() {
  const char *name = "test_errors";
  SETCTX(name);
  CHECK(throwsNgtException(openMissing), "open non-existent index throws NGT::Exception");
  CHECK(throwsNgtException(openNonIndex), "open non-index path throws NGT::Exception");
  CHECK(throwsNgtException(createDimZero), "create with dimension=0 throws NGT::Exception");
  CHECK(throwsNgtException(appendWrongDim), "append wrong-dimension vector throws NGT::Exception");
  CHECK(throwsNgtException(badQueryType), "unsupported SearchQuery element type throws NGT::Exception");
  return finishReport(name);
}
