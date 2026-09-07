// test_package main for kyoto-cabinet 1.2.80 on HarmonyOS PC AArch64.
//
// Verifies the installed package end-to-end against the real file DB:
//   create, write, read, overwrite, remove, iterate, close & reopen,
//   persistence, invalid path, and corrupted input handling.
//
// The DB path comes from argv[1] (the test build directory), so all DB
// files live strictly inside the current test build tree.
//
// IMPORTANT: these tests intentionally do NOT disable file locking,
// mmap, or synchronization. Kyoto Cabinet's lock manager (flock on the
// lock file), mmap-based reader and atomic write semantics are
// exercised as-is so any HarmonyOS filesystem incompatibility surfaces
// here rather than being masked.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <kchashdb.h>
#include <kccommon.h>

using namespace kyotocabinet;

static int g_fail = 0;

static void check(bool ok, const char* what) {
  if (ok) {
    printf("[PASS] %s\n", what);
  } else {
    printf("[FAIL] %s\n", what);
    ++g_fail;
  }
}

// Visitor that counts records during iteration
class CountingVisitor : public kyotocabinet::DB::Visitor {
  size_t n_;
 public:
  CountingVisitor() : n_(0) {}
  const char* visit_full(const char* kbuf, size_t ksiz,
                         const char* vbuf, size_t vsiz, size_t* sp) override {
    (void)kbuf; (void)ksiz; (void)vbuf; (void)vsiz; (void)sp;
    ++n_;
    return NOP;
  }
  size_t count() const { return n_; }
};

static bool write_junk_prefix(const std::string& path, size_t nbytes) {
  FILE* f = fopen(path.c_str(), "rb+");
  if (!f) return false;
  char junk[64];
  memset(junk, 0x7f, sizeof junk);
  const size_t wrote = fwrite(junk, 1, nbytes, f);
  fclose(f);
  return wrote == nbytes;
}

static bool truncate_file_half(const std::string& src_path,
                               const std::string& dst_path) {
  FILE* src = fopen(src_path.c_str(), "rb");
  if (!src) return false;
  std::string buf;
  char tmp[4096];
  size_t n;
  while ((n = fread(tmp, 1, sizeof tmp, src)) > 0) buf.append(tmp, n);
  fclose(src);
  buf.resize(buf.size() / 2);
  FILE* dst = fopen(dst_path.c_str(), "wb");
  if (!dst) return false;
  const size_t wrote = fwrite(buf.data(), 1, buf.size(), dst);
  fclose(dst);
  return wrote == buf.size();
}

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <build-dir>\n", argv[0]);
    return 2;
  }
  const std::string dir = argv[1];
  const std::string dbpath = dir + "/casket.kch";

  // ---- 1. create + write ----
  {
    kyotocabinet::HashDB db;
    check(db.open(dbpath, HashDB::OWRITER | HashDB::OCREATE),
          "create & open writer (file lock + mmap engaged)");
    check(db.set("foo", "bar"), "write foo=bar");
    check(db.set("persist", "yes"), "write persist=yes");
    check(db.count() == 2, "count == 2 after writes");
    check(db.close(), "close writer");
  }

  // ---- 2. read / overwrite / remove / iterate / sync ----
  {
    kyotocabinet::HashDB db;
    check(db.open(dbpath, HashDB::OWRITER), "reopen writer");
    std::string val;
    check(db.get("foo", &val) && val == "bar", "read foo == bar");
    check(db.set("foo", "baz"), "overwrite foo=baz");
    check(db.get("foo", &val) && val == "baz", "foo == baz after overwrite");
    check(db.remove("persist") && db.count() == 1, "remove persist, count == 1");
    check(db.set("alpha", "1"), "write alpha=1");
    check(db.set("beta", "2"), "write beta=2");
    CountingVisitor v;
    check(db.iterate(&v, true) && v.count() == 3, "iterate all records (3)");
    check(db.synchronize(true, nullptr), "synchronize (fsync to disk)");
    check(db.close(), "close writer after sync");
  }

  // ---- 3. close, reopen, persistence ----
  {
    kyotocabinet::File::Status st;
    check(kyotocabinet::File::status(dbpath, &st) && st.size > 0,
          "db file exists on disk, non-empty");
    kyotocabinet::HashDB db;
    check(db.open(dbpath, HashDB::OREADER), "reopen reader after full close");
    std::string val;
    check(db.get("foo", &val) && val == "baz", "persisted foo == baz");
    check(db.get("alpha", &val) && val == "1", "persisted alpha == 1");
    check(db.get("beta", &val) && val == "2", "persisted beta == 2");
    check(db.close(), "close reader");
  }

  // ---- 4. invalid path ----
  {
    kyotocabinet::HashDB db;
    const std::string bad = dir + "/no/such/dir/casket.kch";
    check(!db.open(bad, HashDB::OWRITER | HashDB::OCREATE),
          "invalid path rejected (missing parent dir)");
    check(db.error().code() != BasicDB::Error::SUCCESS,
          "error flag set for invalid path");
  }

  // ---- 5. corrupted input ----
  {
    check(write_junk_prefix(dbpath, 32), "corrupt db header written");
    kyotocabinet::HashDB db;
    const bool opened = db.open(dbpath, HashDB::OREADER);
    check(!opened, "corrupted db (junk header) rejected by open");
    if (opened) db.close();
  }
  {
    // The corrupted db from the junk-header test must be removed first:
    // OCREATE does not rebuild a file whose header magic is broken.
    ::remove(dbpath.c_str());
    kyotocabinet::HashDB db;
    check(db.open(dbpath, HashDB::OWRITER | HashDB::OCREATE),
          "recreate db for truncation test");
    for (int i = 0; i < 100; ++i) {
      char key[32], val[32];
      snprintf(key, sizeof key, "key%03d", i);
      snprintf(val, sizeof val, "val%03d", i);
      db.set(key, val);
    }
    db.close();
    const std::string trunc = dir + "/truncated.kch";
    check(truncate_file_half(dbpath, trunc), "write truncated db copy");
    kyotocabinet::HashDB db2;
    const bool opened = db2.open(trunc, HashDB::OREADER);
    check(!opened || db2.count() <= 100, "truncated db handled safely");
    if (opened) db2.close();
  }

  // ---- 6. remove db files (cleanup is also part of the test) ----
  {
    ::remove((dir + "/casket.kch").c_str());
    ::remove((dir + "/truncated.kch").c_str());
    kyotocabinet::File::Status st;
    check(!kyotocabinet::File::status(dir + "/casket.kch", &st),
          "db file removed after test");
  }

  if (g_fail == 0) {
    printf("ALL TESTS PASSED\n");
    return 0;
  }
  printf("%d TEST(S) FAILED\n", g_fail);
  return 1;
}
