#include <cstdint>
#include <exception>
#include <iostream>
#include <string>

#include <zmqpp/zmqpp.hpp>

int main()
{
    try
    {
        std::uint8_t major = 0;
        std::uint8_t minor = 0;
        std::uint8_t revision = 0;
        zmqpp::version(major, minor, revision);
        // The 4.2.0 upstream tag retains the library API version 4.1.1.
        if (major != 4 || minor != 1 || revision != 1)
        {
            std::cerr << "unexpected zmqpp version: "
                      << static_cast<int>(major) << "."
                      << static_cast<int>(minor) << "."
                      << static_cast<int>(revision) << '\n';
            return 1;
        }

        zmqpp::context context;
        zmqpp::socket puller(context, zmqpp::socket_type::pull);
        puller.bind("inproc://zmqpp-conan-test");

        zmqpp::socket pusher(context, zmqpp::socket_type::push);
        pusher.connect("inproc://zmqpp-conan-test");

        const std::string sent = "zmqpp consumer test";
        if (!pusher.send(sent))
        {
            std::cerr << "send failed\n";
            return 1;
        }

        std::string received;
        if (!puller.receive(received) || received != sent)
        {
            std::cerr << "round trip failed\n";
            return 1;
        }
    }
    catch (const std::exception& error)
    {
        std::cerr << "zmqpp exception: " << error.what() << '\n';
        return 1;
    }

    std::cout << "zmqpp version and inproc round trip passed\n";
    return 0;
}
