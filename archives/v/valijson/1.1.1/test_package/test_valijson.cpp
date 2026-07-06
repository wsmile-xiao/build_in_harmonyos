// test_valijson.cpp — L1 smoke test for valijson header-only library
// Verifies that valijson headers are usable and schema validation works.
//
// Note: StdStringAdapter wraps a std::string as a JSON string value.
// It is NOT a JSON parser. This test creates schemas programmatically
// and validates string values against them.
#include <valijson/schema.hpp>
#include <valijson/validator.hpp>
#include <valijson/adapters/std_string_adapter.hpp>
#include <valijson/constraints/concrete_constraints.hpp>
#include <iostream>
#include <string>

int main() {
    // Test 1: Schema requiring "string" type — should accept a string value
    {
        valijson::Schema schema;
        valijson::constraints::TypeConstraint typeConstraint;
        typeConstraint.addNamedType(
            valijson::constraints::TypeConstraint::kString);
        schema.addConstraint(typeConstraint);

        valijson::Validator validator;
        valijson::ValidationResults results;

        std::string value = "hello world";
        valijson::adapters::StdStringAdapter doc(value);
        if (!validator.validate(schema, doc, &results)) {
            std::cerr << "FAIL: string value rejected by string-type schema"
                      << std::endl;
            return 1;
        }
    }

    // Test 2: Schema requiring "object" type — should reject a string value
    {
        valijson::Schema schema;
        valijson::constraints::TypeConstraint typeConstraint;
        typeConstraint.addNamedType(
            valijson::constraints::TypeConstraint::kObject);
        schema.addConstraint(typeConstraint);

        valijson::Validator validator;

        std::string value = "hello world";
        valijson::adapters::StdStringAdapter doc(value);
        if (validator.validate(schema, doc, nullptr)) {
            std::cerr << "FAIL: string value accepted by object-type schema"
                      << std::endl;
            return 1;
        }
    }

    // Test 3: Schema requiring "number" type — should reject a string value
    {
        valijson::Schema schema;
        valijson::constraints::TypeConstraint typeConstraint;
        typeConstraint.addNamedType(
            valijson::constraints::TypeConstraint::kNumber);
        schema.addConstraint(typeConstraint);

        valijson::Validator validator;

        std::string value = "hello world";
        valijson::adapters::StdStringAdapter doc(value);
        if (validator.validate(schema, doc, nullptr)) {
            std::cerr << "FAIL: string value accepted by number-type schema"
                      << std::endl;
            return 1;
        }
    }

    std::cout << "PASS: valijson schema validation works correctly" << std::endl;
    return 0;
}
