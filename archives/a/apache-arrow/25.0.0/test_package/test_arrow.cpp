/*
 * test_arrow.cpp — Conan L1 consumer test for apache-arrow 25.0.0
 *
 * 真实验证 Arrow C++ 核心（不是链接冒烟）：
 *   1. Array      — 通过 Int32Builder 构造，校验长度/元素/类型
 *   2. Builder    — Append / Finish 运行时 API
 *   3. Schema     — field 构造与校验
 *   4. Table      — Table::Make + Validate，遍历列与行
 *   5. Compute    — arrow::compute::Initialize() 后 CallFunction("add")
 *
 * R34: 每一步都调用被测包的运行时 API，失败即非零退出。
 *
 * 注意第 5 步：Arrow 25 把重量级 compute 内核（算术/布尔/聚合…）改为
 * **惰性注册** —— 它们只在消费者显式调用 arrow::compute::Initialize() 时
 * 才注册进函数表（cpp/src/arrow/compute/initialize.cc:31-60；上游自己的测试
 * 环境也在 SetUp 里调用它，见 cpp/src/arrow/compute/test_env.cc:33）。
 * 不调用时 GetFunctionRegistry() 里只有 13 个核心函数，add 不存在。
 */
#include <arrow/api.h>
#include <arrow/compute/api.h>

#include <cstdio>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

namespace {

int fail(const char *what) {
    std::fprintf(stderr, "[test_arrow] FAIL: %s\n", what);
    return 1;
}

}  // namespace

int main() {
    // ── 1. + 2. Builder / Array ────────────────────────────────────────────
    arrow::Int32Builder builder;
    auto st = builder.Append(42);
    if (!st.ok()) return fail("Int32Builder::Append");
    st = builder.AppendValues({1, 2, 3});
    if (!st.ok()) return fail("Int32Builder::AppendValues");
    auto arr_res = builder.Finish();
    if (!arr_res.ok()) return fail("Int32Builder::Finish");

    std::shared_ptr<arrow::Array> arr = *arr_res;
    if (arr->length() != 4) return fail("array length != 4");
    if (arr->type_id() != arrow::Type::INT32) return fail("array type != int32");
    auto *int_arr = static_cast<arrow::Int32Array *>(arr.get());
    if (int_arr->Value(0) != 42) return fail("array[0] != 42");
    if (int_arr->Value(3) != 3) return fail("array[3] != 3");
    std::printf("  ok   : Array/Builder — length=%lld type=%s [%d,%d,%d,%d]\n",
                static_cast<long long>(arr->length()),
                arr->type()->ToString().c_str(),
                int_arr->Value(0), int_arr->Value(1), int_arr->Value(2),
                int_arr->Value(3));

    // ── 3. Schema ─────────────────────────────────────────────────────────
    auto schema = arrow::schema({arrow::field("value", arrow::int32(), /*nullable=*/false)});
    if (schema == nullptr) return fail("schema() returned null");
    if (schema->num_fields() != 1) return fail("schema field count != 1");
    if (schema->field(0)->name() != "value") return fail("schema field name");
    std::printf("  ok   : Schema — %s\n", schema->ToString().c_str());

    // ── 4. Table ──────────────────────────────────────────────────────────
    auto table = arrow::Table::Make(schema, {arr});
    if (table == nullptr) return fail("Table::Make returned null");
    if (!table->Validate().ok()) return fail("Table::Validate");
    if (table->num_rows() != 4 || table->num_columns() != 1)
        return fail("table shape != 4x1");
    std::printf("  ok   : Table — rows=%lld cols=%lld\n",
                static_cast<long long>(table->num_rows()),
                static_cast<long long>(table->num_columns()));

    // ── 5. Compute ────────────────────────────────────────────────────────
    // Arrow 25 registers the heavy compute kernels lazily (see the header
    // comment); without this call only the 13 core functions exist and
    // CallFunction("add") fails with "No function registered with name: add".
    auto compute_init = arrow::compute::Initialize();
    if (!compute_init.ok()) {
        std::string msg = "arrow::compute::Initialize(): " + compute_init.ToString();
        return fail(msg.c_str());
    }
    std::printf("  ok   : Compute — Initialize() registered %d functions\n",
                static_cast<int>(arrow::compute::GetFunctionRegistry()->num_functions()));

    auto doubled = arrow::compute::CallFunction("add", {arr, arr});
    if (!doubled.ok()) {
        std::string msg = "compute CallFunction(add): " + doubled.status().ToString();
        return fail(msg.c_str());
    }
    auto dbl_arr = doubled->make_array();
    auto *dbl_int = static_cast<arrow::Int32Array *>(dbl_arr.get());
    if (dbl_int->Value(0) != 84) return fail("compute add: 42+42 != 84");
    if (dbl_int->Value(1) != 2) return fail("compute add: 1+1 != 2");
    std::printf("  ok   : Compute — add([42,1,2,3],[42,1,2,3])[0]=%d\n",
                dbl_int->Value(0));

    std::printf("[test_arrow] PASS: apache-arrow 25.0.0 Array/Builder/Schema/Table/Compute OK\n");
    return 0;
}
