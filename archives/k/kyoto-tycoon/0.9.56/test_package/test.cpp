// test_package for kyoto-tycoon 0.9.56 on HarmonyOS PC AArch64.
//
// Exercises the installed libkyototycoon end-to-end through the real
// TimedDB C++ API (kt::TimedDB, the storage engine behind ktserver):
// create, write, read, append, remove, iterate, close & reopen,
// persistence, fsync, and invalid-path handling.
//
// The DB path comes from argv[1] (the test build directory), so all DB
// files live strictly inside the current test build tree.
//
// IMPORTANT: these tests intentionally do NOT disable file locking or
// synchronization. TimedDB delegates locking/mmap to Kyoto Cabinet, so
// any HarmonyOS filesystem incompatibility surfaces here rather than
// being masked.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <kttimeddb.h>
#include <kccommon.h>

namespace kt = kyototycoon;
namespace kc = kyotocabinet;

static int g_fail = 0;
static int g_count = 0;

static void check(bool ok, const char* what) {
  ++g_count;
  if (ok) {
    printf("[PASS] %s\n", what);
  } else {
    printf("[FAIL] %s\n", what);
    ++g_fail;
  }
}

// Visitor that counts records during iteration
class CountingVisitor : public kt::TimedDB::Visitor {
  size_t n_;
 public:
  CountingVisitor() : n_(0) {}
  const char* visit_full(const char* kbuf, size_t ksiz,
                         const char* vbuf, size_t vsiz, size_t* sp,
                         int64_t* xtp) override {
    (void)kbuf; (void)ksiz; (void)vbuf; (void)vsiz; (void)sp; (void)xtp;
    ++n_;
    return NOP;
  }
  size_t count() const { return n_; }
};

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <build-dir>\n", argv[0]);
    return 2;
  }
  const std::string dir = argv[1];
  const std::string dbpath = dir + "/casket.kct";

  // ---- 1. create + write ----
  {
    kt::TimedDB db;
    check(db.open(dbpath, kc::BasicDB::OWRITER | kc::BasicDB::OCREATE),
          "create & open writer (kc file lock engaged)");
    check(db.set("alpha", "1"), "write alpha=1");
    check(db.set("beta", "2"), "write beta=2");
    check(db.count() == 2, "count == 2 after writes");
    check(db.close(), "close writer");
  }

  // ---- 2. read / append / remove / iterate / sync ----
  {
    kt::TimedDB db;
    check(db.open(dbpath, kc::BasicDB::OWRITER), "reopen writer");
    std::string val;
    check(db.get("alpha", &val) && val == "1", "read alpha == 1");
    check(db.append("beta", "+tail"), "append beta += +tail");
    check(db.get("beta", &val) && val == "2+tail", "beta == 2+tail after append");
    CountingVisitor v;
    check(db.iterate(&v, true) && v.count() == 2, "iterate all records (2)");
    check(db.remove("alpha") && db.count() == 1, "remove alpha, count == 1");
    check(!db.get("alpha", &val), "alpha gone after remove");
    check(db.synchronize(true), "synchronize (fsync to disk)");
    check(db.close(), "close writer after sync");
  }

  // ---- 3. close, reopen, persistence ----
  {
    kyotocabinet::File::Status st;
    check(kyotocabinet::File::status(dbpath, &st) && st.size > 0,
          "db file exists on disk, non-empty");
    kt::TimedDB db;
    check(db.open(dbpath, kc::BasicDB::OREADER), "reopen reader after full close");
    std::string val;
    check(db.get("beta", &val) && val == "2+tail", "persisted beta == 2+tail");
    check(db.close(), "close reader");
  }

  // ---- 4. invalid path ----
  {
    kt::TimedDB db;
    const std::string bad = dir + "/no/such/dir/casket.kct";
    check(!db.open(bad, kc::BasicDB::OWRITER | kc::BasicDB::OCREATE),
          "invalid path rejected (missing parent dir)");
  }

  // ---- 5. remove db files (cleanup is also part of the test) ----
  {
    ::remove(dbpath.c_str());
    kyotocabinet::File::Status st;
    check(!kyotocabinet::File::status(dbpath, &st),
          "db file removed after test");
  }

  printf("executed %d checks, %d failed\n", g_count, g_fail);
  if (g_fail == 0) {
    printf("ALL TESTS PASSED\n");
    return 0;
  }
  printf("TEST(S) FAILED\n");
  return 1;
}
