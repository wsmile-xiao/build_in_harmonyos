#include <amqpcpp.h>
#include <iostream>
#include <string>

// Consumer test: exercise the public AMQP-CPP API (AMQP::Array and
// AMQP::Address parsing), mirroring the upstream tests/table/table.cpp
// test that ships with the library.
int main()
{
    // AMQP::Array: upstream tests/table/table.cpp equivalent
    AMQP::Array x;
    x[0] = "abc";
    x[1] = "xyz";

    std::cout << x << std::endl;
    std::cout << x[0] << std::endl;
    std::cout << x[1] << std::endl;

    if (x.count() != 2) {
        std::cerr << "FAIL: array count mismatch" << std::endl;
        return 1;
    }
    if (std::string(x[0]) != "abc" || std::string(x[1]) != "xyz") {
        std::cerr << "FAIL: array element mismatch" << std::endl;
        return 1;
    }

    // AMQP::Address: parse an amqp:// URL
    AMQP::Address address("amqp://user:password@localhost:5672/vhost");
    if (address.hostname() != "localhost") {
        std::cerr << "FAIL: hostname mismatch: " << address.hostname() << std::endl;
        return 1;
    }
    if (address.port() != 5672) {
        std::cerr << "FAIL: port mismatch" << std::endl;
        return 1;
    }

    std::cout << "amqp-cpp consumer test OK" << std::endl;
    return 0;
}
