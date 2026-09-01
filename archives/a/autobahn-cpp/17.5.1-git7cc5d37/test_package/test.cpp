#include <cassert>
#include <chrono>
#include <iostream>
#include <memory>
#include <string>

#include <autobahn/autobahn.hpp>
#include <autobahn/wamp_auth_utils.hpp>
#include <autobahn/wamp_websocketpp_websocket_transport.hpp>

int main()
{
    assert(base_64_encode("hello") == "aGVsbG8=");
    assert(!derive_key("password", "salt", 1, 16).empty());

    autobahn::wamp_message message(3);
    message.set_field(0, 42);
    message.set_field(1, std::string("realm1"));
    message.set_field(2, true);
    assert(message.field<int>(0) == 42);
    assert(message.field<std::string>(1) == "realm1");
    assert(message.field<bool>(2));

    autobahn::wamp_call_options options;
    options.set_timeout(std::chrono::milliseconds(250));
    assert(options.timeout() == std::chrono::milliseconds(250));
    msgpack::sbuffer buffer;
    msgpack::pack(buffer, options);
    autobahn::wamp_call_options restored;
    msgpack::unpack(buffer.data(), buffer.size()).get().convert(restored);
    assert(restored.timeout() == std::chrono::milliseconds(250));

    boost::asio::io_context io;
    auto session = std::make_shared<autobahn::wamp_session>(io);
    assert(session);

    using config = websocketpp::config::asio_client;
    websocketpp::client<config> client;
    autobahn::wamp_websocketpp_websocket_transport<config> transport(
        client, "ws://127.0.0.1:1");
    assert(!transport.is_connected());

    std::cout << "autobahn-cpp consumer test passed" << std::endl;
    return 0;
}
