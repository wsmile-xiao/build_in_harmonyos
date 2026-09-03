#include <cstdlib>
#include <iostream>
#include <iterator>
#include <string>

#include <pqxx/connection>
#include <pqxx/except>
#include <pqxx/separated_list>
#include <pqxx/strconv>
#include <pqxx/version>

// Real libpqxx API test (R34): exercises version macros, pure client-side
// string conversion, a template utility, and a serverless error path.
// None of these need a live PostgreSQL server.
int main() {
    int failures = 0;

    // 1. Version macros from <pqxx/version>.
    if (PQXX_VERSION_MAJOR != 8 || PQXX_VERSION_MINOR != 0) {
        std::cout << "FAIL: unexpected version " << PQXX_VERSION << "\n";
        ++failures;
    }
    if (std::string(PQXX_VERSION).find("8.0") == std::string::npos) {
        std::cout << "FAIL: PQXX_VERSION=" << PQXX_VERSION << "\n";
        ++failures;
    }

    // 2. pqxx::to_string / pqxx::from_string (pure client-side conversions).
    if (pqxx::to_string(42) != "42") {
        std::cout << "FAIL: to_string(int)\n";
        ++failures;
    }
    if (pqxx::to_string(3.25) != "3.25") {
        std::cout << "FAIL: to_string(double)\n";
        ++failures;
    }
    int i = 0;
    pqxx::from_string("1234", i);
    if (i != 1234) {
        std::cout << "FAIL: from_string(int)\n";
        ++failures;
    }
    bool b = false;
    pqxx::from_string("true", b);
    if (!b) {
        std::cout << "FAIL: from_string(bool)\n";
        ++failures;
    }

    // 3. pqxx::separated_list template utility.
    int const values[] = {1, 2, 3};
    std::ostringstream out;
    out << pqxx::separated_list(", ", std::begin(values), std::end(values));
    if (out.str() != "1, 2, 3") {
        std::cout << "FAIL: separated_list -> " << out.str() << "\n";
        ++failures;
    }

    // 4. Serverless error path: connecting to a closed port must throw
    //    pqxx::broken_connection (drives libpq itself through the
    //    pqxx::connection wrapper).
    bool caught = false;
    try {
        pqxx::connection c(
            "host=127.0.0.1 port=1 dbname=conan_test connect_timeout=1");
        (void)c;
    } catch (pqxx::broken_connection const &e) {
        caught = true;
        if (std::string(e.what()).empty()) {
            std::cout << "FAIL: broken_connection has empty message\n";
            ++failures;
        }
    }
    if (!caught) {
        std::cout << "FAIL: expected broken_connection\n";
        ++failures;
    }

    if (failures != 0) {
        std::cout << failures << " failure(s)\n";
        return EXIT_FAILURE;
    }
    std::cout << "libpqxx test_package OK (" << PQXX_VERSION << ")\n";
    return EXIT_SUCCESS;
}
