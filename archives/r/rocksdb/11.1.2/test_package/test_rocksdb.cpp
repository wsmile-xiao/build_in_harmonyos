// RocksDB 11.1.2 L1 consumer test.
//
// Truthfully exercises the packaged library through the public C++ API on the
// HarmonyOS PC (aarch64) target:
//   1. DB::Open on a real on-disk database directory (std::unique_ptr<DB>)
//   2. Put  (several key/value pairs)
//   3. Get  (verify values read back byte-exact)
//   4. Get  (missing key must report NotFound)
//   5. Delete + re-Get (key must be gone)
//   6. Iterator over the full key range
//   7. Flush, then release the handle (unique_ptr destruction closes the DB)
//
// RocksDB 11.x removed the `DB**` overload of Open(); the only read-write
// entry point now takes `std::unique_ptr<DB>*`, and closing is implicit on
// destruction.  This test therefore uses that signature.
//
// Every assertion prints on failure and returns non-zero, so a passing run is
// real evidence that the library links and executes correctly.

#include <cstdio>
#include <cstdlib>
#include <memory>
#include <string>

#include <rocksdb/db.h>
#include <rocksdb/iterator.h>
#include <rocksdb/options.h>
#include <rocksdb/slice.h>
#include <rocksdb/status.h>
#include <rocksdb/version.h>
#include <rocksdb/write_batch.h>

namespace {

int g_failures = 0;

void check(bool cond, const char *what) {
  if (cond) {
    std::printf("  ok   : %s\n", what);
  } else {
    std::printf("  FAIL : %s\n", what);
    ++g_failures;
  }
}

}  // namespace

int main() {
  // Use a writable scratch directory.  On the OHOS device /tmp is a read-only
  // tmpfs, so prefer $TMPDIR (set by the runner) and fall back to the current
  // working directory, which is always writable during a conan test run.
  const char *tmpdir = std::getenv("TMPDIR");
  const std::string path =
      std::string(tmpdir && *tmpdir ? tmpdir : ".") + "/rocksdb_consumer_test_db";

  rocksdb::Options options;
  options.create_if_missing = true;
  options.error_if_exists = false;

  std::unique_ptr<rocksdb::DB> db;
  rocksdb::Status status = rocksdb::DB::Open(options, path, &db);
  if (!status.ok()) {
    std::fprintf(stderr, "[test_rocksdb] DB::Open failed: %s\n",
                 status.ToString().c_str());
    return 1;
  }
  check(db != nullptr, "DB::Open returned a handle");
  std::printf("RocksDB version: %s\n",
              rocksdb::GetRocksVersionAsString(true).c_str());

  // 2. Put
  status = db->Put(rocksdb::WriteOptions(), "key1", "value1");
  check(status.ok(), "Put key1");
  status = db->Put(rocksdb::WriteOptions(), "key2", "value2");
  check(status.ok(), "Put key2");
  status = db->Put(rocksdb::WriteOptions(), "key3", "value3");
  check(status.ok(), "Put key3");

  // 3. Get
  std::string value;
  status = db->Get(rocksdb::ReadOptions(), "key1", &value);
  check(status.ok() && value == "value1", "Get key1 == value1");
  status = db->Get(rocksdb::ReadOptions(), "key3", &value);
  check(status.ok() && value == "value3", "Get key3 == value3");

  // 4. Missing key
  status = db->Get(rocksdb::ReadOptions(), "no_such_key", &value);
  check(status.IsNotFound(), "Get missing key reports NotFound");

  // 5. Delete
  status = db->Delete(rocksdb::WriteOptions(), "key2");
  check(status.ok(), "Delete key2");
  status = db->Get(rocksdb::ReadOptions(), "key2", &value);
  check(status.IsNotFound(), "Get key2 after Delete reports NotFound");

  // 6. Iterate the remaining keys
  int seen = 0;
  rocksdb::Iterator *it = db->NewIterator(rocksdb::ReadOptions());
  for (it->SeekToFirst(); it->Valid(); it->Next()) {
    ++seen;
    std::printf("  iter : %s => %s\n", it->key().ToString().c_str(),
                it->value().ToString().c_str());
  }
  check(it->status().ok(), "Iterator completed without error");
  check(seen == 2, "Iterator saw exactly 2 live keys");
  delete it;

  // 7. Flush, then release the database.  With the 11.x API the handle is
  //    closed by the unique_ptr destructor, so there is no Close() call.
  status = db->Flush(rocksdb::FlushOptions());
  check(status.ok(), "Flush");
  db.reset();
  check(db == nullptr, "database released (destructor closed it)");

  if (g_failures != 0) {
    std::fprintf(stderr, "[test_rocksdb] FAILED: %d assertion(s)\n", g_failures);
    return 1;
  }
  std::printf("[test_rocksdb] PASS: rocksdb 11.1.2 Open/Put/Get/Delete/Iterate/Flush OK\n");
  return 0;
}
