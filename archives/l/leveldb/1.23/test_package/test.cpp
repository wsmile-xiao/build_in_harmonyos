#include <leveldb/db.h>
#include <leveldb/write_batch.h>

#include <iostream>
#include <memory>
#include <string>

namespace {

bool Require(bool condition, const char* message) {
  if (!condition) {
    std::cerr << message << std::endl;
    return false;
  }
  return true;
}

}  // namespace

int main() {
  const std::string database_path = "leveldb-consumer-test-db";
  leveldb::Options options;
  options.create_if_missing = true;

  leveldb::Status status = leveldb::DestroyDB(database_path, options);
  if (!Require(status.ok(), "initial cleanup failed")) return 1;

  leveldb::DB* raw_database = nullptr;
  status = leveldb::DB::Open(options, database_path, &raw_database);
  if (!Require(status.ok(), "database open failed")) return 1;
  if (!Require(raw_database != nullptr, "database pointer is null")) return 1;
  std::unique_ptr<leveldb::DB> database(raw_database);

  status = database->Put(leveldb::WriteOptions(), "alpha", "one");
  if (!Require(status.ok(), "Put(alpha) failed")) return 1;

  std::string value;
  status = database->Get(leveldb::ReadOptions(), "alpha", &value);
  if (!Require(status.ok(), "Get(alpha) failed")) return 1;
  if (!Require(value == "one", "Get(alpha) returned the wrong value")) return 1;

  leveldb::WriteBatch batch;
  batch.Delete("alpha");
  batch.Put("beta", "two");
  status = database->Write(leveldb::WriteOptions(), &batch);
  if (!Require(status.ok(), "WriteBatch failed")) return 1;

  value.clear();
  status = database->Get(leveldb::ReadOptions(), "beta", &value);
  if (!Require(status.ok(), "Get(beta) failed")) return 1;
  if (!Require(value == "two", "Get(beta) returned the wrong value")) return 1;

  status = database->Get(leveldb::ReadOptions(), "alpha", &value);
  if (!Require(status.IsNotFound(), "deleted alpha key is still present")) return 1;

  database.reset();
  status = leveldb::DestroyDB(database_path, options);
  if (!Require(status.ok(), "final cleanup failed")) return 1;
  return 0;
}
