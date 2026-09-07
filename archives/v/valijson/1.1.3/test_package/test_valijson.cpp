// test_valijson.cpp — L1 smoke test for valijson (header-only library)
// Exercises the public API for real: schema construction with type and
// numeric constraints, and validation of document values through
// StdStringAdapter. Also verifies the string→double parsing path
// (internal::parseDouble) that on OHOS toolchains takes the istringstream
// fallback branch (VALIJSON_HAS_STD_FROM_CHARS=0).
#include <valijson/adapters/std_string_adapter.hpp>
#include <valijson/constraints/concrete_constraints.hpp>
#include <valijson/internal/double_parser.hpp>
#include <valijson/schema.hpp>
#include <valijson/validation_results.hpp>
#include <valijson/validator.hpp>

#include <iostream>
#include <string>

int main() {
    // --- Test 1: string-type schema accepts a string value ---
    {
        valijson::Schema schema;
        valijson::constraints::TypeConstraint typeConstraint;
        typeConstraint.addNamedType(
            valijson::constraints::TypeConstraint::kString);
        schema.addConstraint(typeConstraint);

        valijson::Validator validator;
        valijson::ValidationResults results;

        const std::string value = "hello world";
        valijson::adapters::StdStringAdapter doc(value);
        if (!validator.validate(schema, doc, &results)) {
            std::cerr << "FAIL: string value rejected by string-type schema"
                      << std::endl;
            return 1;
        }
    }

    // --- Test 2: numeric constraints (JSON Schema semantics on string values) ---
    {
        // 2a: type=number 约束必须拒绝字符串值（类型不匹配）
        valijson::Schema schema;
        valijson::constraints::TypeConstraint typeConstraint;
        typeConstraint.addNamedType(
            valijson::constraints::TypeConstraint::kNumber);
        schema.addConstraint(typeConstraint);

        valijson::Validator validator;

        double v = 5.0;
        valijson::adapters::StdStringAdapter doc(std::to_string(v));
        if (validator.validate(schema, doc, nullptr)) {
            std::cerr << "FAIL: number-type schema accepted a string value"
                      << std::endl;
            return 1;
        }

        // 2b: minimum 数值约束对字符串值应 vacuous 通过（JSON Schema 语义：
        //     数值约束不适用于非 number 实例）
        valijson::Schema minSchema;
        valijson::constraints::MinimumConstraint minConstraint;
        minConstraint.setMinimum(10.0);
        minSchema.addConstraint(minConstraint);

        if (!validator.validate(minSchema, doc, nullptr)) {
            std::cerr << "FAIL: minimum constraint applied to a string value"
                      << std::endl;
            return 1;
        }
    }

    // --- Test 3: double parsing fallback path (OHOS-relevant) ---
    {
        double parsed = 0.0;
        if (!valijson::internal::parseDouble("3.14159", parsed) ||
            parsed != 3.14159) {
            std::cerr << "FAIL: parseDouble(\"3.14159\")" << std::endl;
            return 1;
        }
        double bad = 0.0;
        if (valijson::internal::parseDouble("not-a-number", bad)) {
            std::cerr << "FAIL: parseDouble accepted invalid input"
                      << std::endl;
            return 1;
        }
    }

    std::cout << "PASS: valijson schema validation works correctly"
              << std::endl;
    return 0;
}