#include <cstdint>
#include <iostream>
#include <memory>
#include <vector>

#include <arrow/api.h>
#include <arrow/acero/api.h>

// Test Arrow Acero (streaming compute engine) API
// This test verifies:
// 1. Arrow core API works (array builder, table creation)
// 2. Acero ExecPlan can be created (proves libarrow_acero is linked)
// 3. Acero TableSourceNode can be created via MakeExecNode
// 4. The plan contains the created node

int main(int argc, char** argv) {
    arrow::MemoryPool* pool = arrow::default_memory_pool();

    // Create a simple int64 array using Arrow core API
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

    // Create a schema and table
    auto schema = arrow::schema({arrow::field("values", arrow::int64())});
    auto table = arrow::Table::Make(schema, {array});

    // Test acero ExecPlan API - create an execution plan
    // This proves libarrow_acero is correctly linked
    auto plan_result = arrow::acero::ExecPlan::Make();
    if (!plan_result.ok()) {
        std::cerr << "Failed to create ExecPlan: " << plan_result.status().message() << std::endl;
        return EXIT_FAILURE;
    }

    std::shared_ptr<arrow::acero::ExecPlan> plan = std::move(plan_result).ValueOrDie();

    // Create a TableSourceNode using MakeExecNode with factory name "table_source"
    // This proves the acero node factory system is functional
    arrow::acero::TableSourceNodeOptions source_options(table);
    auto source_result = arrow::acero::MakeExecNode("table_source", plan.get(), {}, source_options);
    if (!source_result.ok()) {
        std::cerr << "Failed to create source node: " << source_result.status().message() << std::endl;
        return EXIT_FAILURE;
    }

    // Verify the node was added to the plan
    const auto& nodes = plan->nodes();
    if (nodes.empty()) {
        std::cerr << "No nodes in plan after adding source node" << std::endl;
        return EXIT_FAILURE;
    }

    std::cout << "Arrow Acero test passed: ExecPlan created with " << nodes.size()
              << " node(s), TableSourceNode built with " << array->length()
              << " elements in source table" << std::endl;

    return EXIT_SUCCESS;
}
