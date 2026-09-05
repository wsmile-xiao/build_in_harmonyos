/**
 * test_rocksdb.cpp — Functional test for rocksdb 8.7.3 on HarmonyOS.
 *
 * Tests core RocksDB APIs:
 *   1. Open/Close database
 *   2. Put/Get basic operations
 *   3. Delete operations
 *   4. Iterator (forward scan, ordered)
 *   5. WriteBatch (atomic batch write)
 *   6. Persistence (reopen and verify data)
 *   7. CompactRange (manual compaction)
 *   8. Snapshot (consistent read view)
 */
#include <cassert>
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

#include "rocksdb/db.h"
#include "rocksdb/options.h"
#include "rocksdb/slice.h"
#include "rocksdb/write_batch.h"

static std::string get_test_db_path() {
    const char* tmpdir = getenv("TMPDIR");
    if (tmpdir && tmpdir[0]) return std::string(tmpdir) + "/rocksdb_test_db";
    const char* home = getenv("HOME");
    if (home && home[0]) return std::string(home) + "/tmp/rocksdb_test_db";
    return "/tmp/rocksdb_test_db";
}

static int test_count = 0;
static int pass_count = 0;

#define TEST_ASSERT(cond, msg)                                            \
    do {                                                                  \
        ++test_count;                                                     \
        if (!(cond)) {                                                    \
            std::cerr << "  FAIL: " << msg << " (line " << __LINE__      \
                      << ")" << std::endl;                                \
        } else {                                                          \
            ++pass_count;                                                 \
            std::cout << "  PASS: " << msg << std::endl;                  \
        }                                                                 \
    } while (0)

int main() {
    rocksdb::DB* db = nullptr;
    rocksdb::Options options;
    options.create_if_missing = true;

    // Clean up any previous test database
    std::string test_db = get_test_db_path();
    std::string rm_cmd = std::string("rm -rf ") + test_db;
    system(rm_cmd.c_str());

    // --- Test 1: Open database ---
    {
        rocksdb::Status s = rocksdb::DB::Open(options, test_db, &db);
        TEST_ASSERT(s.ok(), "Open database");
        if (!s.ok()) {
            std::cerr << "Cannot proceed without database: " << s.ToString() << std::endl;
            return 1;
        }
    }

    // --- Test 2: Put/Get ---
    {
        rocksdb::Status s = db->Put(rocksdb::WriteOptions(), "key1", "value1");
        TEST_ASSERT(s.ok(), "Put key1=value1");

        std::string value;
        s = db->Get(rocksdb::ReadOptions(), "key1", &value);
        TEST_ASSERT(s.ok() && value == "value1", "Get key1 returns value1");

        // Overwrite
        s = db->Put(rocksdb::WriteOptions(), "key1", "value1_updated");
        TEST_ASSERT(s.ok(), "Put key1=value1_updated (overwrite)");
        s = db->Get(rocksdb::ReadOptions(), "key1", &value);
        TEST_ASSERT(s.ok() && value == "value1_updated", "Get key1 returns updated value");

        // Multiple keys
        for (int i = 2; i <= 5; ++i) {
            std::string k = "key" + std::to_string(i);
            std::string v = "value" + std::to_string(i);
            s = db->Put(rocksdb::WriteOptions(), k, v);
            TEST_ASSERT(s.ok(), "Put " + k + "=" + v);
        }
    }

    // --- Test 3: Delete ---
    {
        rocksdb::Status s = db->Delete(rocksdb::WriteOptions(), "key5");
        TEST_ASSERT(s.ok(), "Delete key5");

        std::string value;
        s = db->Get(rocksdb::ReadOptions(), "key5", &value);
        TEST_ASSERT(s.IsNotFound(), "Get deleted key5 returns NotFound");
    }

    // --- Test 4: Iterator ---
    {
        rocksdb::ReadOptions read_opts;
        rocksdb::Iterator* it = db->NewIterator(read_opts);
        int count = 0;
        std::string prev_key;
        for (it->SeekToFirst(); it->Valid(); it->Next()) {
            std::string key = it->key().ToString();
            // Verify lexicographic order
            if (!prev_key.empty()) {
                TEST_ASSERT(key > prev_key, "Iterator key '" + key + "' > '" + prev_key + "'");
            }
            prev_key = key;
            ++count;
        }
        TEST_ASSERT(it->status().ok(), "Iterator status ok after full scan");
        TEST_ASSERT(count == 4, "Iterator found 4 keys (key1-key4)");
        delete it;
    }

    // --- Test 5: WriteBatch ---
    {
        rocksdb::WriteBatch batch;
        batch.Put("batch_key1", "batch_val1");
        batch.Put("batch_key2", "batch_val2");
        batch.Delete("key4");
        rocksdb::Status s = db->Write(rocksdb::WriteOptions(), &batch);
        TEST_ASSERT(s.ok(), "WriteBatch commit");

        std::string value;
        s = db->Get(rocksdb::ReadOptions(), "batch_key1", &value);
        TEST_ASSERT(s.ok() && value == "batch_val1", "WriteBatch: Get batch_key1");

        s = db->Get(rocksdb::ReadOptions(), "key4", &value);
        TEST_ASSERT(s.IsNotFound(), "WriteBatch: key4 deleted by batch");
    }

    // --- Test 6: CompactRange ---
    {
        rocksdb::Slice begin = "key1";
        rocksdb::Slice end = "key4";
        rocksdb::Status s = db->CompactRange(rocksdb::CompactRangeOptions(), &begin, &end);
        TEST_ASSERT(s.ok(), "CompactRange key1..key4");
    }

    // --- Test 7: Snapshot ---
    {
        const rocksdb::Snapshot* snap = db->GetSnapshot();
        // Write a new value after snapshot
        db->Put(rocksdb::WriteOptions(), "key1", "value1_after_snap");

        rocksdb::ReadOptions read_opts;
        read_opts.snapshot = snap;
        std::string value;
        rocksdb::Status s = db->Get(read_opts, "key1", &value);
        TEST_ASSERT(s.ok() && value == "value1_updated",
                     "Snapshot reads pre-snapshot value (value1_updated)");

        // Read without snapshot should see new value
        s = db->Get(rocksdb::ReadOptions(), "key1", &value);
        TEST_ASSERT(s.ok() && value == "value1_after_snap",
                     "Current read sees post-snapshot value");

        db->ReleaseSnapshot(snap);
    }

    // --- Test 8: Close and reopen (persistence) ---
    {
        delete db;
        db = nullptr;

        rocksdb::Status s = rocksdb::DB::Open(options, test_db, &db);
        TEST_ASSERT(s.ok(), "Reopen database after close");

        if (db) {
            std::string value;
            s = db->Get(rocksdb::ReadOptions(), "key2", &value);
            TEST_ASSERT(s.ok() && value == "value2",
                         "Persistence: key2=value2 survives reopen");

            s = db->Get(rocksdb::ReadOptions(), "batch_key2", &value);
            TEST_ASSERT(s.ok() && value == "batch_val2",
                         "Persistence: batch_key2 survives reopen");
        }
    }

    // Cleanup
    delete db;
    system(rm_cmd.c_str());

    // Summary
    std::cout << "\n========================================" << std::endl;
    std::cout << "rocksdb 8.7.3 test: " << pass_count << "/" << test_count
              << " passed" << std::endl;
    std::cout << "========================================" << std::endl;

    return (pass_count == test_count) ? 0 : 1;
}
