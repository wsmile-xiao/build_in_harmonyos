// test_package consumer test for concurrencpp 0.1.7
// Verifies a consumer can link against the installed package and use its
// public API (runtime + thread executor + result) for real work.
#include <concurrencpp/concurrencpp.h>

#include <iostream>
#include <stdexcept>
#include <string>

int main() {
    try {
        concurrencpp::runtime runtime;
        auto thread_executor = runtime.thread_executor();

        // Execute a real unit of work on the executor and await its result.
        auto result = thread_executor->submit([]() { return 40 + 2; });
        const auto value = result.get();

        if (value != 42) {
            throw std::runtime_error("unexpected result: " + std::to_string(value));
        }

        std::cout << "concurrencpp 0.1.7 consumer test: OK (42)" << std::endl;
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "concurrencpp consumer test FAILED: " << ex.what() << std::endl;
        return 1;
    }
}
