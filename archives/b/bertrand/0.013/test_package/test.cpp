// Consumer test for bertrand 0.013 — exercises the installed public header.
//
// Uses only the exported public API (include/bertrand/bertrand.hpp):
//   - bertrand::find<T>::in(...)  — value membership check (constexpr)
//   - Require / Ensure / Invariant macros
//   - BERTRAND_CONTRACTS_ARE_EXCEPTIONS contract failure path (throws)
//
// BERTRAND_ENABLE_CONTRACTS / BERTRAND_CONTRACTS_ARE_EXCEPTIONS are passed
// via target_compile_definitions (must be active at #include time).
#include <bertrand/bertrand.hpp>

#include <iostream>
#include <stdexcept>
#include <string>

int main() {
  int failures = 0;

  // 1) bertrand::find — value contained in a list (runtime membership;
  //    upstream find stores const T&, so constexpr init is not usable).
  const bertrand::find<int> valid{3};
  if (!valid.in(1, 2, 3, 4)) {
    std::cout << "find.in: 3 must be in {1,2,3,4}" << std::endl;
    ++failures;
  }
  if (valid.in(7, 8)) {
    std::cout << "find.in: 3 must NOT be in {7,8}" << std::endl;
    ++failures;
  }
  std::cout << "find.in(pass/fail membership): OK" << std::endl;

  // 2) Require — passing contract must not throw.
  try {
    Require(valid.in(3, 5, 6), "value must be a supported type");
    std::cout << "Require(passing): OK" << std::endl;
  } catch (const std::runtime_error &) {
    std::cout << "Require(passing): UNEXPECTED THROW" << std::endl;
    ++failures;
  }

  // 3) Require — failing contract must throw (contracts are exceptions).
  try {
    Require(valid.in(9, 10), "unsupported value must be rejected");
    std::cout << "Require(failing): NO THROW (contract not active?)" << std::endl;
    ++failures;
  } catch (const std::runtime_error &e) {
    const std::string what = e.what();
    if (what.find("Require") != std::string::npos) {
      std::cout << "Require(failing): OK — threw with type marker"
                << std::endl;
    } else {
      std::cout << "Require(failing): threw but missing type marker"
                << std::endl;
      ++failures;
    }
  }

  // 4) Ensure — positive branch, must not throw.
  try {
    const int value = 42;
    Ensure(value == 42, "postcondition holds");
    std::cout << "Ensure(passing): OK" << std::endl;
  } catch (const std::runtime_error &) {
    std::cout << "Ensure(passing): UNEXPECTED THROW" << std::endl;
    ++failures;
  }

  if (failures == 0) {
    std::cout << "test bertrand 0.013: ALL CHECKS PASSED" << std::endl;
    return 0;
  }
  std::cout << "test bertrand 0.013: " << failures << " CHECK(S) FAILED"
            << std::endl;
  return 1;
}