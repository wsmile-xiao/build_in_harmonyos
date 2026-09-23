// libparquet consumer smoke test for HarmonyOS PC (aarch64)
//
// Verifies the Apache Parquet columnar storage format C++ API end-to-end:
//  1. Arrow table round-trip: build a table (Int64 + Float64 + Utf8), write
//     it to a Parquet file with SNAPPY compression, read it back with
//     parquet::arrow::FileReader and verify schema + values match
//  2. Low-level columnar API: write/read a plain Int32 column via
//     parquet::ParquetFileWriter/ParquetFileReader (ZSTD compressed)
//  3. Parquet file metadata/footer inspection (created_by, row count,
//     physical types)

#include <arrow/api.h>
#include <arrow/io/file.h>
#include <parquet/api/io.h>
#include <parquet/api/reader.h>
#include <parquet/api/writer.h>
#include <parquet/arrow/reader.h>
#include <parquet/arrow/writer.h>
#include <parquet/arrow/schema.h>

#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>

#define EXIT_ON_FAILURE(expr)                                              \
    do {                                                                   \
        arrow::Status status_ = (expr);                                    \
        if (!status_.ok()) {                                               \
            std::cerr << "FAILED: " #expr " -> " << status_.message()      \
                      << std::endl;                                        \
            return EXIT_FAILURE;                                           \
        }                                                                  \
    } while (0)

template <typename T>
static T DieOnErrorOrValue(arrow::Result<T> result, const char* expr) {
    if (!result.ok()) {
        std::cerr << "FAILED: " << expr << " -> " << result.status().message()
                  << std::endl;
        std::exit(EXIT_FAILURE);
    }
    return std::move(result).ValueOrDie();
}

#define VALUE_OR_DIE(expr) DieOnErrorOrValue((expr), #expr)

static std::string TempFilePath(const char* name) {
    const char* dir = std::getenv("TMPDIR");
    if (!dir || !dir[0]) dir = "/tmp";
    std::string path(dir);
    path += "/";
    path += name;
    return path;
}

// --- 1. High-level API round-trip: Arrow Table -> Parquet file -> Arrow Table ---
static int TestArrowRoundTrip() {
    arrow::Int64Builder id_builder;
    arrow::DoubleBuilder value_builder;
    arrow::StringBuilder name_builder;
    EXIT_ON_FAILURE(id_builder.AppendValues({1, 2, 3, 4, 5}));
    EXIT_ON_FAILURE(value_builder.AppendValues({1.5, 2.5, 3.5, 4.5, 5.5}));
    EXIT_ON_FAILURE(name_builder.Append("apple"));
    EXIT_ON_FAILURE(name_builder.Append("banana"));
    EXIT_ON_FAILURE(name_builder.Append("cherry"));
    EXIT_ON_FAILURE(name_builder.Append("date"));
    EXIT_ON_FAILURE(name_builder.Append("elderberry"));

    std::shared_ptr<arrow::Array> id_array;
    std::shared_ptr<arrow::Array> value_array;
    std::shared_ptr<arrow::Array> name_array;
    EXIT_ON_FAILURE(id_builder.Finish(&id_array));
    EXIT_ON_FAILURE(value_builder.Finish(&value_array));
    EXIT_ON_FAILURE(name_builder.Finish(&name_array));

    auto schema = arrow::schema({
        arrow::field("id", arrow::int64()),
        arrow::field("value", arrow::float64()),
        arrow::field("name", arrow::utf8()),
    });
    auto table = arrow::Table::Make(schema, {id_array, value_array, name_array});

    const std::string path = TempFilePath("test_package_arrow_roundtrip.parquet");

    // --- Write with SNAPPY compression ---
    {
        auto outfile = VALUE_OR_DIE(arrow::io::FileOutputStream::Open(path));
        auto props = parquet::WriterProperties::Builder()
                         .compression(parquet::Compression::SNAPPY)
                         ->build();
        auto pq_writer = VALUE_OR_DIE(parquet::arrow::FileWriter::Open(
            *schema, arrow::default_memory_pool(), outfile, props));
        EXIT_ON_FAILURE(pq_writer->WriteTable(*table, /*chunk_size=*/2));
        EXIT_ON_FAILURE(pq_writer->Close());
        EXIT_ON_FAILURE(outfile->Close());
    }

    // --- Read back ---
    std::shared_ptr<arrow::Table> read_table;
    {
        auto infile = VALUE_OR_DIE(arrow::io::ReadableFile::Open(path));
        auto arrow_reader = VALUE_OR_DIE(
            parquet::arrow::OpenFile(infile, arrow::default_memory_pool()));
        EXIT_ON_FAILURE(arrow_reader->ReadTable(&read_table));
    }

    if (read_table->num_rows() != 5) {
        std::cerr << "row count mismatch: " << read_table->num_rows() << " != 5"
                  << std::endl;
        return EXIT_FAILURE;
    }
    if (read_table->num_columns() != 3) {
        std::cerr << "column count mismatch: " << read_table->num_columns() << " != 3"
                  << std::endl;
        return EXIT_FAILURE;
    }
    if (!read_table->schema()->Equals(*schema)) {
        std::cerr << "schema mismatch after round-trip" << std::endl;
        return EXIT_FAILURE;
    }

    auto ids = std::static_pointer_cast<arrow::Int64Array>(read_table->column(0)->chunk(0));
    auto values = std::static_pointer_cast<arrow::DoubleArray>(read_table->column(1)->chunk(0));
    auto names = std::static_pointer_cast<arrow::StringArray>(read_table->column(2)->chunk(0));
    for (int i = 0; i < 5; i++) {
        if (ids->Value(i) != i + 1 || values->Value(i) != i + 1.5) {
            std::cerr << "value mismatch at row " << i << std::endl;
            return EXIT_FAILURE;
        }
    }
    if (names->GetString(0) != "apple" || names->GetString(4) != "elderberry") {
        std::cerr << "string value mismatch after round-trip" << std::endl;
        return EXIT_FAILURE;
    }

    // Verify SNAPPY compression was applied to every column chunk
    {
        auto reader = parquet::ParquetFileReader::OpenFile(path, false);
        auto metadata = reader->metadata();
        if (metadata->num_columns() != 3) {
            std::cerr << "metadata column count mismatch" << std::endl;
            return EXIT_FAILURE;
        }
        auto rg_meta = metadata->RowGroup(0);
        for (int i = 0; i < metadata->num_columns(); i++) {
            if (rg_meta->ColumnChunk(i)->compression() != parquet::Compression::SNAPPY) {
                std::cerr << "column " << i << " not SNAPPY compressed" << std::endl;
                return EXIT_FAILURE;
            }
        }
    }

    std::remove(path.c_str());
    std::cout << "[1/3] Arrow table round-trip (SNAPPY): OK - "
              << read_table->num_rows() << " rows x " << read_table->num_columns()
              << " cols verified" << std::endl;
    return EXIT_SUCCESS;
}

// --- 2. Low-level columnar API: ParquetFileWriter with Int32 column (ZSTD) ---
// Writes through the low-level parquet::ParquetFileWriter /
// RowGroupWriter / Int32Writer::WriteBatch path (proves the thrift-based
// metadata serialization + ZSTD codec + column chunk writing all work),
// then verifies the file via footer metadata and reads it back through the
// arrow-level reader.
static int TestLowLevelColumnar() {
    const std::string path = TempFilePath("test_package_lowlevel.parquet");

    // Write with the low-level columnar API
    {
        auto outfile = VALUE_OR_DIE(arrow::io::FileOutputStream::Open(path));
        auto schema = std::static_pointer_cast<parquet::schema::GroupNode>(
            parquet::schema::GroupNode::Make(
                "schema", parquet::Repetition::REQUIRED,
                {parquet::schema::PrimitiveNode::Make(
                    "int32_col", parquet::Repetition::REQUIRED, parquet::Type::INT32,
                    parquet::ConvertedType::NONE)}));
        auto props = parquet::WriterProperties::Builder()
                         .compression(parquet::Compression::ZSTD)
                         ->build();
        auto writer = parquet::ParquetFileWriter::Open(outfile, schema, props);
        parquet::RowGroupWriter* rg_writer = writer->AppendRowGroup();
        auto* col_writer =
            static_cast<parquet::Int32Writer*>(rg_writer->NextColumn());
        int32_t values[6] = {100, 200, 300, 400, 500, 600};
        // REQUIRED column: max_def_level == 0 -> pass nullptr for levels
        col_writer->WriteBatch(6, nullptr, nullptr, values);
        rg_writer->Close();
        writer->Close();
        EXIT_ON_FAILURE(outfile->Close());
    }

    // Verify the written file: thrift footer + metadata + ZSTD compression
    {
        auto reader = parquet::ParquetFileReader::OpenFile(path, false);
        auto metadata = reader->metadata();
        if (metadata->num_rows() != 6 || metadata->num_columns() != 1) {
            std::cerr << "low-level metadata mismatch: rows="
                      << metadata->num_rows() << " cols=" << metadata->num_columns()
                      << std::endl;
            return EXIT_FAILURE;
        }
        if (metadata->num_row_groups() != 1) {
            std::cerr << "low-level row group count mismatch" << std::endl;
            return EXIT_FAILURE;
        }
        // thrift footer parsed: schema physical type must round-trip
        if (metadata->schema()->Column(0)->physical_type() != parquet::Type::INT32) {
            std::cerr << "low-level physical type mismatch" << std::endl;
            return EXIT_FAILURE;
        }
        // ZSTD compression applied to the column chunk
        auto chunk = metadata->RowGroup(0)->ColumnChunk(0);
        if (chunk->compression() != parquet::Compression::ZSTD) {
            std::cerr << "low-level column chunk not ZSTD compressed" << std::endl;
            return EXIT_FAILURE;
        }
        std::string created_by = metadata->created_by();
        if (created_by.find("parquet-cpp") == std::string::npos) {
            std::cerr << "low-level created_by mismatch: " << created_by << std::endl;
            return EXIT_FAILURE;
        }
    }

    // Read values back through the arrow-level reader
    {
        auto infile = VALUE_OR_DIE(arrow::io::ReadableFile::Open(path));
        auto arrow_reader = VALUE_OR_DIE(
            parquet::arrow::OpenFile(infile, arrow::default_memory_pool()));
        std::shared_ptr<arrow::Table> table;
        EXIT_ON_FAILURE(arrow_reader->ReadTable(&table));
        if (table->num_rows() != 6 || table->num_columns() != 1) {
            std::cerr << "low-level round-trip shape mismatch: "
                      << table->num_rows() << "x" << table->num_columns() << std::endl;
            return EXIT_FAILURE;
        }
        auto col = std::static_pointer_cast<arrow::Int32Array>(table->column(0)->chunk(0));
        for (int i = 0; i < 6; i++) {
            if (col->Value(i) != (i + 1) * 100) {
                std::cerr << "low-level value mismatch at " << i << ": "
                          << col->Value(i) << std::endl;
                return EXIT_FAILURE;
            }
        }
    }

    std::remove(path.c_str());
    std::cout << "[2/3] Low-level columnar write (ZSTD, Int32) + round-trip read: OK - 6 values verified"
              << std::endl;
    return EXIT_SUCCESS;
}

// --- 3. Parquet file metadata / footer inspection ---
static int TestMetadata() {
    const std::string path = TempFilePath("test_package_meta.parquet");

    arrow::Int64Builder builder;
    EXIT_ON_FAILURE(builder.AppendValues({42}));
    std::shared_ptr<arrow::Array> array;
    EXIT_ON_FAILURE(builder.Finish(&array));
    auto schema = arrow::schema({arrow::field("magic", arrow::int64())});
    auto table = arrow::Table::Make(schema, {array});

    {
        auto outfile = VALUE_OR_DIE(arrow::io::FileOutputStream::Open(path));
        auto pq_writer = VALUE_OR_DIE(parquet::arrow::FileWriter::Open(
            *schema, arrow::default_memory_pool(), outfile,
            parquet::WriterProperties::Builder().build()));
        EXIT_ON_FAILURE(pq_writer->WriteTable(*table, 1024));
        EXIT_ON_FAILURE(pq_writer->Close());
        EXIT_ON_FAILURE(outfile->Close());
    }

    {
        auto reader = parquet::ParquetFileReader::OpenFile(path, false);
        auto metadata = reader->metadata();
        std::string created_by = metadata->created_by();
        if (created_by.find("parquet-cpp") == std::string::npos) {
            std::cerr << "created_by mismatch: " << created_by << std::endl;
            return EXIT_FAILURE;
        }
        if (metadata->num_rows() != 1) {
            std::cerr << "meta num_rows mismatch" << std::endl;
            return EXIT_FAILURE;
        }
        if (metadata->schema()->Column(0)->physical_type() != parquet::Type::INT64) {
            std::cerr << "physical type mismatch" << std::endl;
            return EXIT_FAILURE;
        }
        // File must be readable end-to-end: thrift footer parsed => num_row_groups >= 1
        if (metadata->num_row_groups() < 1) {
            std::cerr << "num_row_groups mismatch" << std::endl;
            return EXIT_FAILURE;
        }
    }

    std::remove(path.c_str());
    std::cout << "[3/3] Metadata/footer inspection: OK (created_by contains parquet-cpp)"
              << std::endl;
    return EXIT_SUCCESS;
}

int main() {
    if (TestArrowRoundTrip() != EXIT_SUCCESS) return EXIT_FAILURE;
    if (TestLowLevelColumnar() != EXIT_SUCCESS) return EXIT_FAILURE;
    if (TestMetadata() != EXIT_SUCCESS) return EXIT_FAILURE;

    std::cout << "libparquet test_package passed: Parquet columnar format write/read OK"
              << std::endl;
    return EXIT_SUCCESS;
}
