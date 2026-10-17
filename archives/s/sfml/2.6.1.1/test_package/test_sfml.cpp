#include <SFML/Network/IpAddress.hpp>
#include <SFML/System/String.hpp>
#include <SFML/System/Time.hpp>

#include <cstdlib>
#include <iostream>

int main() {
    const sf::String message = "OpenHarmony";
    if (message.getSize() != 11) {
        std::cerr << "unexpected sf::String size\n";
        return EXIT_FAILURE;
    }

    const sf::Time elapsed = sf::milliseconds(42);
    if (elapsed.asMilliseconds() != 42) {
        std::cerr << "unexpected sf::Time conversion\n";
        return EXIT_FAILURE;
    }

    if (sf::seconds(1).asMicroseconds() != 1000000) {
        std::cerr << "unexpected sf::Time microsecond conversion\n";
        return EXIT_FAILURE;
    }

    const sf::IpAddress loopback("127.0.0.1");
    if (loopback.toString() != "127.0.0.1") {
        std::cerr << "unexpected sf::IpAddress conversion\n";
        return EXIT_FAILURE;
    }

    std::cout << "sfml system/network smoke test passed\n";
    return EXIT_SUCCESS;
}
