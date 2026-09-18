#include <cstdint>
#include <iostream>
#include <memory>
#include <vector>

#include <arrow/api.h>
#include <arrow/acero/api.h>
#include <arrow/compute/api.h>
#include <arrow/dataset/dataset.h>
#include <arrow/dataset/scanner.h>

// Test Arrow Dataset API (dataset discovery/partitioning/scanning)
// This test verifies:
// 1. Arrow core API works (array builder, table creation)
// 2. InMemoryDataset can be constructed from a Table (proves libarrow_dataset linked)
// 3. ScannerBuilder creates a Scanner, ScanOptions applied (batch size / projection)
// 4. Scanner::ToTable() scans the dataset end-to-end through the acero engine
// 5. Scanner::CountRows() returns the expected row count

int main(int argc, char** argv) {
    // Arrow 23.0 static linkage: compute kernels (make_struct et al.) are
    // registered into the global FunctionRegistry by
    // arrow::compute::Initialize() — the documented consumer-side step
    // (arrow/compute/api.h includes initialize.h). Without it the scanner
    // projection fails with "No function registered with name: make_struct".
    arrow::Status init_status = arrow::compute::Initialize();
    if (!init_status.ok()) {
        std::cerr << "Failed to initialize compute kernels: "
                  << init_status.message() << std::endl;
        return EXIT_FAILURE;
    }

    arrow::MemoryPool* pool = arrow::default_memory_pool();

    // 1. Create a source table using Arrow core API
    arrow::Int64Builder builder(pool);
    auto status = builder.AppendValues({1, 2, 3, 4, 5});
    if (!status.ok()) {
        std::cerr << "Failed to append values: " << status.message() << std::endl;
        return EXIT_FAILURE;
    }

    std::shared_ptr<arrow::Array> array;
    status = builder.Finish(&array);
    if (!status.ok()) {
        std::cerr << "Failed to finish array: " << status.message() << std::endl;
        return EXIT_FAILURE;
    }

    auto schema = arrow::schema({arrow::field("values", arrow::int64())});
    auto table = arrow::Table::Make(schema, {array});

    // 2. Construct an InMemoryDataset from the table.
    // This exercises the Dataset virtual interface of libarrow_dataset.
    std::shared_ptr<arrow::dataset::Dataset> dataset =
        std::make_shared<arrow::dataset::InMemoryDataset>(table);

    // 3. Build a Scanner via ScannerBuilder (dataset scan API entry point)
    auto builder_result = dataset->NewScan();
    if (!builder_result.ok()) {
        std::cerr << "Failed to create ScannerBuilder: "
                  << builder_result.status().message() << std::endl;
        return EXIT_FAILURE;
    }
    std::shared_ptr<arrow::dataset::ScannerBuilder> scan_builder =
        std::move(builder_result).ValueOrDie();

    // Project only the "values" column
    arrow::Status proj_status = scan_builder->Project({"values"});
    if (!proj_status.ok()) {
        std::cerr << "Failed to set projection: "
                  << proj_status.message() << std::endl;
        return EXIT_FAILURE;
    }

    // Configure scan options: smaller batch size so scanning produces 2 batches
    arrow::Status batch_status = scan_builder->BatchSize(3);
    if (!batch_status.ok()) {
        std::cerr << "Failed to set batch size: "
                  << batch_status.message() << std::endl;
        return EXIT_FAILURE;
    }

    auto scanner_result = scan_builder->Finish();
    if (!scanner_result.ok()) {
        std::cerr << "Failed to finish Scanner: "
                  << scanner_result.status().message() << std::endl;
        return EXIT_FAILURE;
    }
    std::shared_ptr<arrow::dataset::Scanner> scanner =
        std::move(scanner_result).ValueOrDie();

    // 4. Scan the dataset into a Table (end-to-end scan through acero engine)
    auto scanned_result = scanner->ToTable();
    if (!scanned_result.ok()) {
        std::cerr << "Failed to scan dataset to table: "
                  << scanned_result.status().message() << std::endl;
        return EXIT_FAILURE;
    }
    std::shared_ptr<arrow::Table> scanned = std::move(scanned_result).ValueOrDie();

    if (scanned->num_rows() != 5) {
        std::cerr << "Unexpected scanned row count: " << scanned->num_rows()
                  << " (expected 5)" << std::endl;
        return EXIT_FAILURE;
    }
    if (scanned->num_columns() != 1) {
        std::cerr << "Unexpected scanned column count: " << scanned->num_columns()
                  << " (expected 1 after projection)" << std::endl;
        return EXIT_FAILURE;
    }

    // 5. CountRows on the dataset scanner
    auto count_result = scanner->CountRows();
    if (!count_result.ok()) {
        std::cerr << "Failed to count rows: "
                  << count_result.status().message() << std::endl;
        return EXIT_FAILURE;
    }
    int64_t row_count = count_result.ValueOrDie();
    if (row_count != 5) {
        std::cerr << "Unexpected row count: " << row_count << " (expected 5)"
                  << std::endl;
        return EXIT_FAILURE;
    }

    // Verify scanned values round-trip: column "values" of the scanned table.
    // BatchSize(3) makes the scan produce multiple record batches (3+2), so
    // sum across all chunks of the chunked array.
    auto col = scanned->column(0);
    int64_t sum = 0;
    for (int ch = 0; ch < col->num_chunks(); ++ch) {
        auto int64_col = std::static_pointer_cast<arrow::Int64Array>(col->chunk(ch));
        for (int64_t i = 0; i < int64_col->length(); ++i) {
            sum += int64_col->Value(i);
        }
    }
    if (sum != 15) {
        std::cerr << "Unexpected sum of scanned values: " << sum
                  << " (expected 15)" << std::endl;
        return EXIT_FAILURE;
    }

    std::cout << "Arrow Dataset test passed: InMemoryDataset scanned via Scanner -> "
              << scanned->num_rows() << " rows (sum=" << sum
              << ", CountRows=" << row_count << ")" << std::endl;

    return EXIT_SUCCESS;
}
