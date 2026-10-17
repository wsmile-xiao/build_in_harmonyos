#include "pxr/base/vt/value.h"
#include "pxr/base/vt/array.h"
#include "pxr/base/vt/dictionary.h"

#include <iostream>

int main() {
    // Test VtValue with integer
    pxr::VtValue intVal(42);
    if (!intVal.IsHolding<int>()) {
        std::cerr << "FAIL: VtValue not holding int" << std::endl;
        return 1;
    }
    if (intVal.Get<int>() != 42) {
        std::cerr << "FAIL: VtValue int value mismatch" << std::endl;
        return 1;
    }

    // Test VtValue with string
    pxr::VtValue strVal(std::string("hello"));
    if (!strVal.IsHolding<std::string>()) {
        std::cerr << "FAIL: VtValue not holding string" << std::endl;
        return 1;
    }
    if (strVal.Get<std::string>() != "hello") {
        std::cerr << "FAIL: VtValue string value mismatch" << std::endl;
        return 1;
    }

    // Test VtArray
    pxr::VtArray<int> arr(3);
    arr[0] = 1;
    arr[1] = 2;
    arr[2] = 3;
    pxr::VtValue arrVal(arr);
    if (!arrVal.IsHolding<pxr::VtArray<int>>()) {
        std::cerr << "FAIL: VtValue not holding VtArray" << std::endl;
        return 1;
    }

    // Test VtDictionary
    pxr::VtDictionary dict;
    dict["key"] = pxr::VtValue(100);
    if (dict.find("key") == dict.end()) {
        std::cerr << "FAIL: VtDictionary missing key" << std::endl;
        return 1;
    }

    std::cout << "pxr-vt smoke test: OK" << std::endl;
    return 0;
}
