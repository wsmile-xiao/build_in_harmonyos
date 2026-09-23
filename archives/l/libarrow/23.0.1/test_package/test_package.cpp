#include <cstddef>
#include <cstdint>
#include <iostream>
#include <vector>

#include <arrow/api.h>

using arrow::DoubleBuilder;
using arrow::Int64Builder;
using arrow::ListBuilder;
struct data_row {
    int64_t id;
    double cost;
    std::vector<double> cost_components;
};

arrow::Status VectorToColumnarTable(const std::vector<struct data_row>& rows,
                                    std::shared_ptr<arrow::Table>* table) {
    arrow::MemoryPool* pool = arrow::default_memory_pool();

    Int64Builder id_builder(pool);
    DoubleBuilder cost_builder(pool);
    ListBuilder components_builder(pool, std::make_shared<DoubleBuilder>(pool));
    DoubleBuilder& cost_components_builder =
        *(static_cast<DoubleBuilder*>(components_builder.value_builder()));

    for (const data_row& row : rows) {
        ARROW_RETURN_NOT_OK(id_builder.Append(row.id));
        ARROW_RETURN_NOT_OK(cost_builder.Append(row.cost));
        ARROW_RETURN_NOT_OK(components_builder.Append());
        ARROW_RETURN_NOT_OK(cost_components_builder.AppendValues(row.cost_components.data(),
                                                                 row.cost_components.size()));
    }

    std::shared_ptr<arrow::Array> id_array;
    ARROW_RETURN_NOT_OK(id_builder.Finish(&id_array));
    std::shared_ptr<arrow::Array> cost_array;
    ARROW_RETURN_NOT_OK(cost_builder.Finish(&cost_array));
    std::shared_ptr<arrow::Array> cost_components_array;
    ARROW_RETURN_NOT_OK(components_builder.Finish(&cost_components_array));

    std::vector<std::shared_ptr<arrow::Field>> schema_vector = {
        arrow::field("id", arrow::int64()), arrow::field("cost", arrow::float64()),
        arrow::field("cost_components", arrow::list(arrow::float64()))};

    auto schema = std::make_shared<arrow::Schema>(schema_vector);
    *table = arrow::Table::Make(schema, {id_array, cost_array, cost_components_array});

    return arrow::Status::OK();
}

arrow::Status ColumnarTableToVector(const std::shared_ptr<arrow::Table>& table,
                                    std::vector<struct data_row>* rows) {
    std::vector<std::shared_ptr<arrow::Field>> schema_vector = {
        arrow::field("id", arrow::int64()), arrow::field("cost", arrow::float64()),
        arrow::field("cost_components", arrow::list(arrow::float64()))};
    auto expected_schema = std::make_shared<arrow::Schema>(schema_vector);

    if (!expected_schema->Equals(*table->schema())) {
        return arrow::Status::Invalid("Schemas are not matching!");
    }

    auto ids =
        std::static_pointer_cast<arrow::Int64Array>(table->column(0)->chunk(0));
    auto costs =
        std::static_pointer_cast<arrow::DoubleArray>(table->column(1)->chunk(0));
    auto cost_components =
        std::static_pointer_cast<arrow::ListArray>(table->column(2)->chunk(0));
    auto cost_components_values =
        std::static_pointer_cast<arrow::DoubleArray>(cost_components->values());
    const double* ccv_ptr = cost_components_values->data()->GetValues<double>(1);

    for (int64_t i = 0; i < table->num_rows(); i++) {
        int64_t id = ids->Value(i);
        double cost = costs->Value(i);
        const double* first = ccv_ptr + cost_components->value_offset(i);
        const double* last = ccv_ptr + cost_components->value_offset(i + 1);
        std::vector<double> components_vec(first, last);
        rows->push_back({id, cost, components_vec});
    }

    return arrow::Status::OK();
}

#define EXIT_ON_FAILURE(expr)                      \
    do {                                           \
        arrow::Status status_ = (expr);            \
        if (!status_.ok()) {                       \
            std::cerr << status_.message() << std::endl; \
            return EXIT_FAILURE;                   \
        }                                          \
    } while (0);

int main(int argc, char** argv) {
    std::vector<data_row> rows = {
        {1, 1.0, {1.0}}, {2, 2.0, {1.0, 2.0}}, {3, 3.0, {1.0, 2.0, 3.0}}};

    std::shared_ptr<arrow::Table> table;
    EXIT_ON_FAILURE(VectorToColumnarTable(rows, &table));

    std::vector<data_row> roundtripped_rows;
    EXIT_ON_FAILURE(ColumnarTableToVector(table, &roundtripped_rows));

    // Explicit field-by-field comparison (assert would be compiled out under
    // NDEBUG in Release builds, leaving the roundtrip unverified).
    if (rows.size() != roundtripped_rows.size()) {
        std::cerr << "roundtrip row count mismatch: expected " << rows.size()
                  << ", got " << roundtripped_rows.size() << std::endl;
        return EXIT_FAILURE;
    }
    for (size_t i = 0; i < rows.size(); i++) {
        const data_row& exp = rows[i];
        const data_row& got = roundtripped_rows[i];
        if (exp.id != got.id) {
            std::cerr << "row " << i << " id mismatch: expected " << exp.id
                      << ", got " << got.id << std::endl;
            return EXIT_FAILURE;
        }
        if (exp.cost != got.cost) {
            std::cerr << "row " << i << " cost mismatch: expected " << exp.cost
                      << ", got " << got.cost << std::endl;
            return EXIT_FAILURE;
        }
        if (exp.cost_components != got.cost_components) {
            std::cerr << "row " << i << " cost_components mismatch: expected "
                      << exp.cost_components.size() << " values, got "
                      << got.cost_components.size() << std::endl;
            return EXIT_FAILURE;
        }
    }

    std::cout << "Arrow test passed: built columnar table with " << table->num_rows()
              << " rows, " << table->num_columns() << " columns (roundtrip verified: "
              << roundtripped_rows.size() << " rows field-checked)" << std::endl;

    return EXIT_SUCCESS;
}
